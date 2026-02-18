# agents/prompt_engineer_agent.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from llama_cpp import Llama
import paho.mqtt.client as mqtt
import json

llm_instances = {}
def load_model(model_name):
    if model_name not in llm_instances:
        model_path = config.MODEL_PATHS.get(model_name)
        if not model_path: raise ValueError(f"Model path for '{model_name}' not found.")
        print(f"Prompt Engineer loading model: {model_name}...")
        llm_instances[model_name] = Llama(model_path=model_path, n_gpu_layers=0, n_ctx=4096, verbose=False)
        print(f"Model '{model_name}' loaded.")
    return llm_instances[model_name]

def correct_user_command(command):
    """Mindset 1: Pre-processes and corrects the user's raw command."""
    print("\n--- Prompt Engineer: Correcting user input ---")
    model_name = config.AGENT_MODELS["PROMPT_ENGINEER"]
    llm = load_model(model_name)
    
    # --- NEW, STRICTER PROMPT ---
    system_prompt = (
        "You are a command-line pre-processor. Your only job is to correct any spelling, grammar, or case sensitivity errors in the user's command. "
        "Do NOT add any conversational text, greetings, or explanations. "
        "Respond with ONLY the corrected, ready-to-execute command."
        "\n\nEXAMPLE:\nUser: hey veera can u opn notpad and writ a story\nResponse: open notepad and write a story"
    )
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": command}]
    response = llm.create_chat_completion(messages)
    corrected_command = response['choices'][0]['message']['content'].strip()
    
    # Clean up any potential quotation marks the model might add
    corrected_command = corrected_command.strip("'\"")

    print(f"Corrected Command: {corrected_command}")
    return corrected_command

def run_prompt_engineer():
    """The main user interface loop for Veera."""
    main_client = mqtt.Client(client_id="veera_main_ui")
    main_client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
    main_client.loop_start()

    print("\n--- Veera is ready. Enter your command. ---")
    try:
        while True:
            user_command = input("\n> ")
            if user_command.lower() == 'quit': break
            
            corrected_command = correct_user_command(user_command)
            
            topic = config.AGENT_TOPICS["ORCHESTRATOR_COMMANDS"]
            payload = json.dumps({"command": corrected_command})
            main_client.publish(topic, payload)
            print(f"Published corrected command to '{topic}'")

    except KeyboardInterrupt:
        print("\nShutdown signal received.")
    finally:
        main_client.loop_stop()
        main_client.disconnect()