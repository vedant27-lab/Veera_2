# agents/system_agent.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
import paho.mqtt.client as mqtt
import json
from llama_cpp import Llama
from execution_engine import parse_plan, execute_plan
llm_instances = {}

def load_model(model_name):
    """Loads a model into memory if it's not already loaded."""
    if model_name not in llm_instances:
        model_path = config.MODEL_PATHS.get(model_name)
        if not model_path:
            raise ValueError(f"Model path for '{model_name}' not found in config.")
        
        print(f"System Agent loading model: {model_name}...")
        llm_instances[model_name] = Llama(
            model_path=model_path,
            n_gpu_layers=0, 
            n_ctx=4096,
            verbose=False
        )
        print(f"Model '{model_name}' loaded.")
    return llm_instances[model_name]

def get_detailed_plan(command):
    """Gets a detailed, step-by-step plan from the specialist LLM."""
    model_name = config.AGENT_MODELS.get("SYSTEM_AGENT", "QWEN_1.8B") 
    llm = load_model(model_name)
    
    system_prompt = (
        "You are a System Agent. Your task is to create a precise, step-by-step plan to accomplish the user's goal using only keyboard and application actions.\n\n"
        "RULES:\n"
        "- Only use the following action keywords: OPEN_APP, TYPE_TEXT, PRESS_KEY, HOTKEY.\n"
        "- Be direct and machine-readable. Do not add conversational text.\n\n"
        "EXAMPLE:\n"
        "User Command: open notepad and write hello world\n"
        "Plan:\n"
        "1. OPEN_APP: 'notepad.exe'\n"
        "2. TYPE_TEXT: 'hello world'\n"
        "--- END OF EXAMPLE ---\n\n"
    )
    full_prompt = system_prompt + f"User Command: {command}\nPlan:"
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant that creates step-by-step plans."},
        {"role": "user", "content": full_prompt}
    ]
    response = llm.create_chat_completion(messages)
    return response['choices'][0]['message']['content']

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        print("System Agent connected to MQTT Broker.")
        client.subscribe(config.AGENT_TOPICS["SYSTEM_AGENT"])
        print(f"Subscribed to topic: {config.AGENT_TOPICS['SYSTEM_AGENT']}")
    else:
        print(f"Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    """Callback for when a message is received from the Orchestrator."""
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")
        print(f"\nReceived high-level command: '{command}'")
        
        plan_text = get_detailed_plan(command)
        print("\n--- Generated Plan ---")
        print(plan_text)
        
        actions = parse_plan(plan_text)
        
        print("\n--- Executing Plan ---")
        execute_plan(actions)
        print("\n--- Task Complete ---")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("System Agent is shutting down.")
        client.disconnect()
    except Exception as e:
        print(f"Could not connect to MQTT Broker: {e}") 