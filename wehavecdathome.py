import sys

from CliFunction import cli_function, cli
import threading
import time
from pathlib import Path
import json
import os
import subprocess


# CONSTANTS:
SERVICES_DIR = "wehavecdathome"
CONFIG_FILE = f"{SERVICES_DIR}/cdathome.conf.json"

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"


# UTILITY/HELPER FUNCTIONS:
def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"{CONFIG_FILE} not found. Run setup first.")
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def clone_repo(repo_url, branch, services_dir):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(services_dir, repo_name)
    if os.path.exists(repo_path):
        print(f"Repository already cloned at {repo_path}.")
        return
    subprocess.run(["git", "clone", "-b", branch, repo_url, repo_path], check=True)
    print(f"Cloned repository to {repo_path}.")


def run_command(command):
    process = subprocess.Popen(command, shell=True)
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()


def poll_git_updates(repo_dir, branch):
    result = subprocess.run(
        ["git", "-C", repo_dir, "fetch", "origin", branch], capture_output=True, text=True
    )
    if "new branch" in result.stdout or "fast-forward" in result.stdout:
        return True
    return False


@cli_function
def setup():
    """Interactive setup to gather and save configuration."""
    try:
        config = load_config()
        print("config already exits.  Setup will over-write existing config:")
        print(f"{MAGENTA}{json.dumps(config, indent=4)}{RESET}")
        if(input("Continue? (y/n)").lower() == "y"):
            pass
        else:
            return

    except Exception:
        pass

    repo_url = input("Enter the GIT repository URL: ").strip()
    branch = input("Enter the branch to monitor (default: main): ").strip() or "main"
    token = input("Enter a Personal Access Token for your user on the specified GIT repo (default: Public repo only): ")
    poll_period = int(input("Enter poll period in seconds (default: 60): ").strip() or 60)
    startup_cmd = input(
        "Enter the startup command (leave blank for `docker compose up`): "
    ).strip()

    if startup_cmd == "":
        startup_cmd = "docker compose up"

    # Save configuration
    config = {
        "repo_url": repo_url,
        "branch": branch,
        "token": token,
        "poll_period": poll_period,
        "startup_cmd": startup_cmd,
    }
    save_config(config)
    print(f"Configuration saved to {CONFIG_FILE}")
    print(f"{MAGENTA}{json.dumps(config, indent=4)}{RESET}")
    print("You can now download/test/host this configuration.")


@cli_function
def pull():
    """Pull updates for the repository."""
    config = load_config()
    repo_name = config["repo_url"].split("/")[-1].replace(".git", "")
    repo_dir = Path(f"{SERVICES_DIR}/{repo_name}")

    print("Loaded Config:")
    print(f"{MAGENTA}{json.dumps(config, indent=4)}{RESET}")
    print(f"Using Repo Name: {repo_name}")
    print(f"Using Repo Directory: {repo_dir}")
    print(f"Current Working Directory: {os.getcwd()}")

    if not repo_dir.exists():
        # Clone the repository if it doesn't exist
        if config.get("token"):
            clone_url = f"https://{config['token']}@{config['repo_url'].replace('https://', '')}"
        else:
            clone_url = config["repo_url"]  # Assume public repo if no token is provided

        cmd = ["git", "clone", "-b", config["branch"], clone_url, str(repo_dir)]
    else:
        # Pull updates if the repository exists
        cmd = ["git", "-C", str(repo_dir), "pull", "origin", config["branch"]]

    print(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        # Print the stderr from the failed command
        print(f"{RED}Error occurred while executing git command:{RESET}")
        print(f"{RED}{e.stderr}{RESET}")
        print(f"{RED}Please Resolve Issue Above.{RESET}")
        sys.exit(1)

    print("Repository successfully pulled!")


@cli_function
def test():
    """Run the startup command in verbose mode."""
    config = load_config()
    startup_cmd = config.get("startup_cmd", "docker-compose up")
    run_command(startup_cmd)

@cli_function
def host():
    """Start watching the repository and restart on updates."""
    config = load_config()
    repo_dir = Path(SERVICES_DIR) / Path(config["repo_url"].split("/")[-1].replace(".git", ""))
    if not repo_dir.exists():
        print(f"Repository not found in {repo_dir}. Run setup first.")
        return

    def monitor_and_restart():
        while True:
            if poll_git_updates(repo_dir, config["branch"]):
                print("Changes detected. Restarting service...")
                process.terminate()
                time.sleep(2)
                process = subprocess.Popen(config.get("startup_cmd", "docker-compose up"), shell=True)
            time.sleep(config["poll_period"])

    process = subprocess.Popen(config.get("startup_cmd", "docker-compose up"), shell=True)
    monitor_thread = threading.Thread(target=monitor_and_restart, daemon=True)
    monitor_thread.start()
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()

@cli_function
def view_config():
    """Display the current configuration."""
    config = load_config()
    print("Current Configuration:")
    print(f"{MAGENTA}{json.dumps(config, indent=4)}{RESET}")

if __name__ == "__main__":
    masthead = """
    #     #           #     #                          #####  ######        #             #     #                      
    #  #  # ######    #     #   ##   #    # ######    #     # #     #      # #   #####    #     #  ####  #    # ###### 
    #  #  # #         #     #  #  #  #    # #         #       #     #     #   #    #      #     # #    # ##  ## #      
    #  #  # #####     ####### #    # #    # #####     #       #     #    #     #   #      ####### #    # # ## # #####  
    #  #  # #         #     # ###### #    # #         #       #     #    #######   #      #     # #    # #    # #      
    #  #  # #         #     # #    #  #  #  #         #     # #     #    #     #   #      #     # #    # #    # #      
     ## ##  ######    #     # #    #   ##   ######     #####  ######     #     #   #      #     #  ####  #    # ######                                                                                          
    """
    print(masthead)
    cli()