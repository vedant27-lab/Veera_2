# execution_engine.py
import pyautogui
import time
import os
import webbrowser
import sqlite3
import config # Assuming config.py is in the root directory

def find_app_path_in_logs(app_name):
    """Queries the database to find the last known path for an application."""
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()
    # Search for logs where this app was opened and the details look like a path
    cursor.execute(
        "SELECT action_details FROM activity_log WHERE action_type = 'OPEN_APP' AND action_details LIKE ? ORDER BY timestamp DESC LIMIT 1",
        (f'%{app_name}%',)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def parse_plan(plan_text):
    """
    Parses the natural language plan from the LLM into a list of actions.
    """
    actions = []
    lines = plan_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
            
        try:
            # Splits "1. ACTION: 'details'" into its components
            command_part = line.split('.', 1)[1].strip()
            action_type, details = command_part.split(':', 1)
            
            # Cleans up and standardizes the parts
            action_type = action_type.strip().upper()
            details = details.strip().strip("'\"")
            
            actions.append({"action": action_type, "details": details})
        except (IndexError, ValueError):
            print(f"Warning: Could not parse line: {line}")
            
    return actions

def execute_plan(actions):
    """
    Executes a list of parsed actions using pyautogui and other libraries.
    """
    if not actions:
        print("No actions to execute.")
        return

    for i, action_item in enumerate(actions):
        action_type = action_item.get("action")
        details = action_item.get("details")
        
        print(f"Step {i+1}: Executing {action_type} with details '{details}'")
        time.sleep(2) # A delay to see each action happen
        
        if action_type == "OPEN_APP":
            try:
                # First, try to find the full path in memory (logs)
                path = find_app_path_in_logs(details)
                if path and os.path.exists(path):
                    print(f"Found path in memory: {path}")
                    os.startfile(path)
                else:
                    # If not found or path is invalid, try the system's start command
                    print(f"App not in memory or path invalid, trying system command for '{details}'")
                    os.system(f"start {details}")
            except Exception as e:
                print(f"Error opening application '{details}': {e}")
        
        elif action_type == "TYPE_TEXT":
            pyautogui.write(details, interval=0.05)
            
        elif action_type == "PRESS_KEY":
            pyautogui.press(details.lower())
            
        elif action_type == "HOTKEY":
            try:
                # Assumes details are comma-separated, e.g., "ctrl,l"
                keys = [key.strip() for key in details.split(',')]
                pyautogui.hotkey(*keys)
            except Exception as e:
                print(f"Error executing HOTKEY '{details}': {e}")

        elif action_type == "NAVIGATE_URL":
            webbrowser.open(details)

        else:
            print(f"Warning: Unknown action type '{action_type}'")