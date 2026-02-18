# main_veera.py
import multiprocessing
import time
from agents.prompt_engineer_agent import run_prompt_engineer
from agents.orchestrator import run_orchestrator
from agents.specialist_agent import run_specialist_agent
import config

def main():
    print("--- Starting Veera Multi-Agent System ---")
    processes = []
    
    try:
        # Start Orchestrator Process
        orchestrator_proc = multiprocessing.Process(target=run_orchestrator, name="Orchestrator")
        orchestrator_proc.start()
        processes.append(orchestrator_proc)
        print(f"Orchestrator started with PID: {orchestrator_proc.pid}")

        # Start a process for each Specialist Agent
        specialist_agents_to_run = [k for k in config.AGENT_TOPICS if k != "ORCHESTRATOR_COMMANDS"]
        for agent_type in specialist_agents_to_run:
            specialist_proc = multiprocessing.Process(target=run_specialist_agent, name=agent_type, args=(agent_type,))
            specialist_proc.start()
            processes.append(specialist_proc)
            print(f"{agent_type} started with PID: {specialist_proc.pid}")
        
        time.sleep(5) 
        
        # Run the Prompt Engineer in the main process to handle user input
        run_prompt_engineer()
        
    except KeyboardInterrupt:
        print("\nShutdown signal received.")
    finally:
        for process in processes:
            if process.is_alive():
                print(f"Terminating {process.name}...")
                process.terminate()
                process.join()
        
        print("\n--- Veera Multi-Agent System Shut Down ---")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()