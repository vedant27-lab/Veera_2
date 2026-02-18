import config
import paho.mqtt.client as mqtt
import json
from llama_cpp import Llama
import subprocess
import pyautogui
import time
import os
import pandas as pd
import re
import sys
import shutil

# --- LLM and Helper Functions ---
llm_instances = {}

def load_model(model_name):
    """Loads a model into memory if it's not already loaded."""
    if model_name not in llm_instances:
        model_path = config.MODEL_PATHS.get(model_name)
        if not model_path:
            raise ValueError(f"Model path for '{model_name}' not found in config.")
        
        print(f"Loading model: {model_name}...")
        llm_instances[model_name] = Llama(model_path=model_path, n_gpu_layers=0, n_ctx=4096, verbose=False)
        print(f"Model '{model_name}' loaded.")
    return llm_instances[model_name]

def get_csv_headers(file_path):
    """Reads the headers of a CSV file, automatically handling common encoding issues."""
    try:
        df = pd.read_csv(file_path, nrows=0, encoding='utf-8')
        return df.columns.tolist()
    except UnicodeDecodeError:
        print(f"UTF-8 decoding failed for {file_path}. Trying 'latin1' encoding.")
        try:
            df = pd.read_csv(file_path, nrows=0, encoding='latin1')
            return df.columns.tolist()
        except Exception as e:
            print(f"Could not read CSV headers with any encoding: {e}")
            return None
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading CSV headers: {e}")
        return None

def extract_code(text):
    """Reliably extracts code from a markdown block using regex."""
    match = re.search(r"```(?:[a-zA-Z]+\n)?(.*)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

# --- Orchestrator Logic ---
def get_llm_routing_decision(command):
    """Uses the LLM to decide which agent should handle the command."""
    model_name = config.AGENT_MODELS["ORCHESTRATOR"]
    llm = load_model(model_name)
    available_agents = ", ".join(config.AGENT_TOPICS.keys())
    
    system_prompt = (
        f"You are a task router. Your only job is to determine which specialist agent should handle the user's command. "
        f"Respond with only the agent's name from this list: {available_agents}.\n\n"
        "GUIDELINES:\n"
        "- If the command is a complex, multi-step project like 'create a website' or 'build a full project', you MUST use PROJECT_MANAGER_AGENT.\n"
        "- If the command involves loading, cleaning, analyzing, or modifying a data file (like .csv or .xlsx), you MUST use DATA_AGENT.\n"
        "- If the command is a general request to write a code snippet, function, or script unrelated to a specific data file, use CODE_AGENT.\n"
        "- For web browsers, use WEB_AGENT.\n"
        "- For all other OS-level tasks (opening apps, file management), use SYSTEM_AGENT.\n\n"
        "EXAMPLE 1:\nUser Command: load 'my_data.csv' and find the average of the 'sales' column\nResponse: DATA_AGENT\n\n"
        "EXAMPLE 2:\nUser Command: write a python function to sort a list\nResponse: CODE_AGENT\n"
    )
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Command: {command}"}]
    response = llm.create_chat_completion(messages, max_tokens=32, temperature=0.0)
    agent_name = response['choices'][0]['message']['content'].strip()
    return agent_name if agent_name in config.AGENT_TOPICS else "SYSTEM_AGENT"

def run_orchestrator():
    """The main loop for the Orchestrator agent."""
    client = mqtt.Client(client_id="veera_orchestrator_main")
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Orchestrator connected and listening for commands.")
            client.subscribe("veera/commands")
    
    def on_message(client, userdata, msg):
        command = json.loads(msg.payload.decode())['command']
        print(f"\nOrchestrator received command: '{command}'")
        agent_name = get_llm_routing_decision(command)
        print(f"Routing to: {agent_name}")
        topic = config.AGENT_TOPICS.get(agent_name)
        if topic:
            payload = json.dumps({"command": command, "agent_type": agent_name})
            client.publish(topic, payload)
    
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
    client.loop_forever()


# --- Specialist Agent Logic ---
def get_detailed_plan(command, agent_type, file_context=""):
    """Gets a detailed plan or script from the appropriate LLM."""
    model_name = config.AGENT_MODELS.get(agent_type)
    llm = load_model(model_name)
    system_prompt = config.AGENT_PROMPTS.get(agent_type)
    user_content = f"{file_context} Command: {command}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    response = llm.create_chat_completion(messages, max_tokens=4096)
    return response['choices'][0]['message']['content']

def parse_and_execute(plan_text, agent_type, original_command, mqtt_client):
    """The new, more powerful execution engine."""
    
    if agent_type == "PROJECT_MANAGER_AGENT":
        print("\n--- Executing High-Level Project Plan ---")
        try:
            json_match = re.search(r"\[.*\]", plan_text, re.DOTALL)
            if not json_match:
                raise json.JSONDecodeError("No JSON array found in the plan.", plan_text, 0)
            
            meta_plan = json.loads(json_match.group(0))
            for i, step in enumerate(meta_plan):
                target_agent = step.get("target_agent")
                command = step.get("command")
                print(f"\nStep {i+1}/{len(meta_plan)}: Delegating to {target_agent} -> '{command}'")
                topic = config.AGENT_TOPICS.get(target_agent)
                if topic:
                    payload = json.dumps({"command": command, "agent_type": target_agent})
                    mqtt_client.publish(topic, payload)
                    time.sleep(30) # Give the sub-agent time to work
                else:
                    print(f"Error: Could not find topic for target agent '{target_agent}'")
        except json.JSONDecodeError as e:
            print(f"Error: The PROJECT_MANAGER_AGENT did not return a valid JSON plan. Details: {e}")
        return

    if agent_type == "DEV_AGENT":
        print("\n--- Executing Multi-File Development Plan ---")
        try:
            match = re.search(r"folder named '([^']*)'", original_command)
            project_name = match.group(1) if match else "generated_webapp"
            
            file_plan = json.loads(plan_text)
            project_path = os.path.join(os.getcwd(), project_name)
            if os.path.exists(project_path): shutil.rmtree(project_path)
            os.makedirs(project_path)

            for filename, content in file_plan.items():
                full_path = os.path.join(project_path, filename)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                print(f"Creating file: {full_path}")
                with open(full_path, "w", encoding='utf-8') as f: f.write(content)
            print(f"\nSuccessfully created web application in folder: '{project_name}'")
        except Exception as e:
            print(f"Error during DEV_AGENT execution: {e}")
        return
        
    if agent_type == "SYSTEM_AGENT":
        command = original_command.lower()
        try:
            print(f"System Agent executing: {command}")
            if "create a new folder" in command:
                folder_name = command.split("named")[-1].strip().strip("'\"")
                os.makedirs(folder_name, exist_ok=True)
                print(f"Folder '{folder_name}' created.")
            elif "create a python virtual environment" in command:
                parts = command.split("'")
                folder, venv_name = parts[1], parts[3]
                subprocess.run([sys.executable, "-m", "venv", os.path.join(folder, venv_name)], check=True)
                print(f"Virtual environment '{venv_name}' created in '{folder}'.")
            elif "install the required libraries" in command:
                parts = command.split("'")
                folder = parts[1]
                libs = command.split(":")[-1].strip().split(',')
                pip_path = os.path.join(folder, "venv", "Scripts", "pip") if sys.platform == "win32" else os.path.join(folder, "venv", "bin", "pip")
                for lib in libs:
                    subprocess.run([pip_path, "install", lib.strip()], check=True)
                    print(f"Library '{lib.strip()}' installed.")
            elif "zip the entire" in command:
                folder_to_zip = command.split("'")[1]
                shutil.make_archive(folder_to_zip, 'zip', folder_to_zip)
                print(f"Folder '{folder_to_zip}' has been zipped.")
        except Exception as e:
            print(f"System Agent failed to execute command '{command}': {e}")
        return

    # Fallback for simple script agents (DATA, CODE, WORD)
    script = extract_code(plan_text)
    for attempt in range(1, 3):
        try:
            print(f"Executing generated script (Attempt {attempt})...")
            with open("temp_agent_script.py", "w", encoding='utf-8') as f: f.write(script)
            result = subprocess.run([sys.executable, "temp_agent_script.py"], capture_output=True, text=True, check=True, encoding='utf-8')
            if result.stdout: print("Output:", result.stdout)
            print(f"Script executed successfully on attempt {attempt}.")
            break
        except subprocess.CalledProcessError as e:
            error_message = e.stderr
            print("\n--- Script Failed. Initiating Self-Correction ---")
            print("Error Details:", error_message)
            if "ModuleNotFoundError" in error_message:
                missing_module = error_message.split("'")[1]
                print(f"Attempting to install missing module: {missing_module}")
                subprocess.run([sys.executable, "-m", "pip", "install", missing_module], check=True)
                print("Installation complete. Retrying script...")
                continue
            file_context = ""
            try:
                file_path = [word.strip("'\"") for word in original_command.split() if '.csv' in word][0]
                if file_path:
                    headers = get_csv_headers(file_path)
                    if headers: file_context = f"Context: The file '{file_path}' has columns: {headers}."
            except IndexError: pass
            correction_prompt = (
                f"The following script failed. Analyze the original command, file context, faulty script, and error to provide a corrected script.\n\n"
                f"Original Command: {original_command}\n{file_context}\n\n"
                f"Faulty Script:\n```python\n{script}\n```\n\n"
                f"Error Message:\n{error_message}\n\n"
                f"Provide the corrected, full Python script."
            )
            corrected_script_text = get_detailed_plan(correction_prompt, agent_type, file_context)
            print("\n--- Generated Corrected Script ---\n", corrected_script_text)
            script = extract_code(corrected_script_text)
            if attempt == 2:
                print("\n--- Self-Correction Failed on the second attempt ---")
        finally:
            if os.path.exists("temp_agent_script.py"): os.remove("temp_agent_script.py")

def on_specialist_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        command, agent_type = payload.get("command"), payload.get("agent_type")
        print(f"\nSpecialist received task for {agent_type}: '{command}'")
        plan_text = get_detailed_plan(command, agent_type)
        print("\n--- Generated Plan/Meta-Plan ---\n", plan_text)
        parse_and_execute(plan_text, agent_type, command, client)
        print("\n--- Task Complete ---")
    except Exception as e:
        print(f"An error occurred in on_message: {e}")

def run_specialist_agent(agent_type):
    client = mqtt.Client(client_id=f"veera_{agent_type}")
    client.on_message = on_specialist_message
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"{agent_type} connected.")
            client.subscribe(config.AGENT_TOPICS.get(agent_type))
    client.on_connect = on_connect
    client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
    client.loop_forever()