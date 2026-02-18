# config.py

# -- MQTT Broker Configuration --
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# -- LLM Configuration --
MODEL_PATHS = {
    "QWEN_1.8B": "LLM/qwen1_5-1_8b-chat-q4_k_m.gguf",
    "LLAMA3_8B": "LLM/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
}

AGENT_MODELS = {
    "PROMPT_ENGINEER": "QWEN_1.8B",
    "ORCHESTRATOR": "LLAMA3_8B",
    "PROJECT_MANAGER_AGENT": "LLAMA3_8B",
    "DEV_AGENT": "LLAMA3_8B",
    "SYSTEM_AGENT": "QWEN_1.8B",
    "WEB_AGENT": "LLAMA3_8B",
    "CODE_AGENT": "LLAMA3_8B",
    "DATA_AGENT": "LLAMA3_8B"
}

# -- Agent Topics --
AGENT_TOPICS = {
    "ORCHESTRATOR_COMMANDS": "veera/commands",
    "PROJECT_MANAGER_AGENT": "veera/project_manager/tasks",
    "DEV_AGENT": "veera/dev_agent/tasks",
    "SYSTEM_AGENT": "veera/system_agent/tasks",
    "WEB_AGENT": "veera/web_agent/tasks",
    "CODE_AGENT": "veera/code_agent/tasks",
    "DATA_AGENT": "veera/data_agent/tasks"
}

# -- Agent "Personality" Prompts --
AGENT_PROMPTS = {
    "PROJECT_MANAGER_AGENT": (
        "You are a Senior Project Manager AI. Your job is to take a high-level user goal and break it down into a sequence of precise, actionable steps for your team of specialist agents (SYSTEM_AGENT, DEV_AGENT). "
        "Your response MUST be a JSON array of objects. Each object must have a 'target_agent' and a 'command'.\n\n"
        "EXAMPLE:\n"
        "User Command: Create a full-stack web app project for a to-do list.\n"
        "Response:\n"
        "[\n"
        "  {\"target_agent\": \"SYSTEM_AGENT\", \"command\": \"create a new folder named 'todo_app'\"},\n"
        "  {\"target_agent\": \"SYSTEM_AGENT\", \"command\": \"inside 'todo_app', create a python virtual environment named 'venv'\"},\n"
        "  {\"target_agent\": \"DEV_AGENT\", \"command\": \"generate the code for a simple Flask to-do list application inside the 'todo_app' folder\"},\n"
        "  {\"target_agent\": \"SYSTEM_AGENT\", \"command\": \"inside 'todo_app', install the required libraries: flask\"},\n"
        "  {\"target_agent\": \"SYSTEM_AGENT\", \"command\": \"zip the entire 'todo_app' folder into 'todo_app.zip'\"}\n"
        "]"
    ),
    "DEV_AGENT": (
        "You are an expert full-stack Developer Agent focused on security. Your task is to build a web application. "
        "You MUST use Flask for the backend. For authentication, you MUST use server-side sessions and hash passwords using 'werkzeug.security'. "
        "Provide a multi-file plan in a single JSON block. Each key in the JSON should be the filename (e.g., 'app.py', 'templates/login.html'), "
        "and the value should be the full code content for that file. "
        "Respond with ONLY the JSON object and nothing else."
    ),
    "SYSTEM_AGENT": (
        "You are a System Agent. Your only job is to execute direct OS commands passed to you. You do not generate plans."
    ),
    "DATA_AGENT": (
        "You are an expert data analyst who writes robust Python scripts using pandas. Your #1 priority is to write modern, error-free code that will not fail."
    ),
}