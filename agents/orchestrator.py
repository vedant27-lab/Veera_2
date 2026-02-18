import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
import paho.mqtt.client as mqtt
import json
from llama_cpp import Llama

llm_instances = {}
def load_model(model_name):
    if model_name not in llm_instances:
        model_path = config.MODEL_PATHS.get(model_name)
        if not model_path: raise ValueError(f"Model path for '{model_name}' not found.")
        print(f"Orchestrator loading model: {model_name}...")
        llm_instances[model_name] = Llama(model_path=model_path, n_gpu_layers=0, n_ctx=4096, verbose=False)
        print(f"Model '{model_name}' loaded.")
    return llm_instances[model_name]

def get_llm_routing_decision(command):
    model_name = config.AGENT_MODELS["ORCHESTRATOR"] # Will now use Llama3
    llm = load_model(model_name)
    available_agents = ", ".join(k for k in config.AGENT_TOPICS if k != "ORCHESTRATOR_COMMANDS")
    
    # --- NEW, SMARTER ROUTING PROMPT ---
    system_prompt = (
        f"You are an expert task router for an AI assistant. Your only job is to analyze the user's command and respond with the single, most appropriate agent name from this list: {available_agents}.\n\n"
        "CRITICAL GUIDELINES:\n"
        "- If the command involves a complex, multi-step project with file creation, environment setup, and code generation (like 'create a website' or 'build a full project'), you MUST use PROJECT_MANAGER_AGENT.\n"
        "- If the command is about analyzing, cleaning, or visualizing data from a file (like a .csv), you MUST use DATA_AGENT.\n"
        "- If the command asks to create a Word Document (.docx), you MUST use WORD_AGENT.\n"
        "- If the command is a simple web search for news or information, use WEB_AGENT.\n"
        "- For simple, direct OS tasks like 'open notepad and type a sentence', use SYSTEM_AGENT.\n\n"
        "EXAMPLES:\n"
        "User Command: open notepad and write a story about a robot\nResponse: SYSTEM_AGENT\n\n"
        "User Command: create a full login-signup website project\nResponse: PROJECT_MANAGER_AGENT\n\n"
        "User Command: find the latest news on Chandrayaan-3\nResponse: WEB_AGENT\n\n"
        "User Command: load laptopData.csv and create a bar chart of the average price\nResponse: DATA_AGENT\n"
    )

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Command: {command}"}]
    response = llm.create_chat_completion(messages, max_tokens=32, temperature=0.0)
    agent_name = response['choices'][0]['message']['content'].strip()
    return agent_name if agent_name in config.AGENT_TOPICS else "SYSTEM_AGENT"

def on_orchestrator_message(client, userdata, msg):
    """Handles incoming commands from the Prompt Engineer."""
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")
        print(f"\nOrchestrator received command: '{command[:100]}...'") 

        agent_name = get_llm_routing_decision(command)
        print(f"Routing to: {agent_name}")
        
        topic = config.AGENT_TOPICS.get(agent_name)
        if topic:
            new_payload = json.dumps({"command": command, "agent_type": agent_name})
            client.publish(topic, new_payload)
            print(f"Task delegated to topic '{topic}'.")
    except Exception as e:
        print(f"Error in Orchestrator: {e}")

def run_orchestrator():
    """The main loop for the Orchestrator agent."""
    client = mqtt.Client(client_id="veera_orchestrator")
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Orchestrator connected and listening for commands.")
            client.subscribe(config.AGENT_TOPICS["ORCHESTRATOR_COMMANDS"])
    client.on_connect = on_connect
    client.on_message = on_orchestrator_message
    
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nOrchestrator shutting down.")
    except Exception as e:
        print(f"Orchestrator connection error: {e}")