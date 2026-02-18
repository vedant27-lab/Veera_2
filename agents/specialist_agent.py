# agents/specialist_agent.py
import config
import paho.mqtt.client as mqtt
import json
from llama_cpp import Llama
import subprocess
import time
import os
import re
import sys
import shutil
import pandas as pd

llm_instances = {}
def load_model(model_name):
    if model_name not in llm_instances:
        model_path = config.MODEL_PATHS.get(model_name)
        if not model_path: raise ValueError(f"Model path for '{model_name}' not found.")
        print(f"Specialist loading model: {model_name}...")
        llm_instances[model_name] = Llama(model_path=model_path, n_gpu_layers=0, n_ctx=4096, verbose=False)
        print(f"Model '{model_name}' loaded.")
    return llm_instances[model_name]

def extract_code(text, language='python'):
    match = re.search(rf"```{language}?\s*\n(.*?)\n```", text, re.DOTALL)
    if match: return match.group(1).strip()
    match = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
    if match: return match.group(1).strip()
    return text.strip()

def get_detailed_plan(command, agent_type, file_context=""):
    model_name = config.AGENT_MODELS.get(agent_type)
    llm = load_model(model_name)
    system_prompt = config.AGENT_PROMPTS.get(agent_type)
    user_content = f"{file_context} Command: {command}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    response = llm.create_chat_completion(messages, max_tokens=4096) # Increased for complex plans
    return response['choices'][0]['message']['content']

def parse_and_execute(plan_text, agent_type, original_command, mqtt_client):
    if agent_type == "PROJECT_MANAGER_AGENT":
        print("\n--- Executing High-Level Project Plan ---")
        try:
            meta_plan = json.loads(plan_text)
            for i, step in enumerate(meta_plan):
                target_agent = step.get("target_agent")
                command = step.get("command")
                print(f"\nStep {i+1}/{len(meta_plan)}: Delegating to {target_agent} -> '{command}'")
                topic = config.AGENT_TOPICS.get(target_agent)
                if topic:
                    payload = json.dumps({"command": command, "agent_type": target_agent})
                    mqtt_client.publish(topic, payload)
                    time.sleep(30) # Give the sub-agent more time for complex tasks
                else:
                    print(f"Error: Could not find topic for target agent '{target_agent}'")
        except json.JSONDecodeError:
            print("Error: The PROJECT_MANAGER_AGENT did not return a valid JSON plan.")
        return

    if agent_type == "DEV_AGENT":
        print("\n--- Executing Multi-File Development Plan ---")
        try:
            match = re.search(r"folder named '([^']*)'", original_command)
            project_name = match.group(1) if match else "generated_webapp"
            
            file_plan = json.loads(plan_text)
            if not os.path.exists(project_name): os.makedirs(project_name)

            for filename, content in file_plan.items():
                full_path = os.path.join(project_name, filename)
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
    try:
        with open("temp_agent_script.py", "w", encoding='utf-8') as f: f.write(script)
        result = subprocess.run([sys.executable, "temp_agent_script.py"], check=True, capture_output=True, text=True)
        if result.stdout: print("Output:", result.stdout)
    except Exception as e:
        print(f"Script execution failed: {e}")
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