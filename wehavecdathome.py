import sys
from typing import Callable

from CliFunction import cli_function, cli
import time
from pathlib import Path
import json
import os
import subprocess


# CONSTANTS:
SERVICES_DIR = "wehavecdathome"
CONFIG_FILE = f"{SERVICES_DIR}/wehavecdathome.conf.json"

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

def print_masthead():
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


# UTILITY/HELPER FUNCTIONS:
def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"{CONFIG_FILE} not found. Run setup first.")
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config):
    dir_name = os.path.dirname(CONFIG_FILE)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)

    print(f"saving config: {CONFIG_FILE}")
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
    print_masthead()

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
    print("You can now [p]ull/[t]est/[h]ost this configuration.")


@cli_function
def pull() -> bool:
    """Pull updates for the repository specified in the config."""

    print_masthead()
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
        print(f"Running command: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print("Repository successfully cloned!")
            return True  # Cloning is considered an update
        except subprocess.CalledProcessError as e:
            print(f"{RED}Error occurred while cloning the repository:{RESET}")
            print(f"{RED}{e.stderr}{RESET}")
            return False  # Clone failed, no updates applied

    else:
        # Pull updates if the repository exists
        cmd = ["git", "-C", str(repo_dir), "pull", "origin", config["branch"]]
        print(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(result.stdout)

            # Determine if updates were pulled
            if "Already up to date." in result.stdout:
                print("No updates found.")
                return False  # No updates
            else:
                print("Repository successfully updated!")
                return True  # Updates were applied

        except subprocess.CalledProcessError as e:
            print(f"{RED}Error occurred while executing git pull command:{RESET}")
            print(f"{RED}{e.stderr}{RESET}")
            print(f"{RED}No Updates were able to be applied{RESET}")
            return False  # Pull failed


@cli_function
def test():
    """Run the command specified in the config, in the pulled repository, without any automatic reloading"""
    print_masthead()

    config = load_config()
    # pass in a no-op false argument, so that the test function never wakes up to poll.
    run(config, lambda: False, lambda: False)

@cli_function
def host():
    """Use the conf.json file, to watch a repository, pull new versions automatically, and continuously re-deploy using the configured command."""
    print_masthead()

    config = load_config()

    next_poll = int(time.time()) + config.get("poll_period")

    def shouldPoll():
        nonlocal next_poll
        if next_poll < int(time.time()):
            next_poll = int(time.time()) + config.get("poll_period")
            return True
        return False

    def check_for_updates():
        return pull()


    while True:
        # run will loop continually, if updates are found, it will pull them and then stop running.  This loop will then immediately re-run the command again.
        run(config, shouldPoll, check_for_updates)


@cli_function
def view_config():
    """Display the current configuration."""
    print_masthead()

    config = load_config()
    print("Current Configuration:")
    print(f"{MAGENTA}{json.dumps(config, indent=4)}{RESET}")

def run(config: dict, pollCheck: Callable[[], bool], poll: Callable[[], bool]):
    startup_cmd = config.get("startup_cmd")

    # Change directory to SERVICES_DIR before running the command
    os.chdir(SERVICES_DIR)
    print(f"Changed directory to {SERVICES_DIR}")

    # Run the command and stream output to the console
    print(f"Running command: {startup_cmd}")

    # Using subprocess.Popen to stream output
    process = subprocess.Popen(startup_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Continuously read the stdout and stderr and print it to the console
    try:
        while True:
            # Read one line of output from stdout
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()

            if stdout_line:
                sys.stdout.write(stdout_line)  # Print stdout line to the shell
            if stderr_line:
                sys.stderr.write(stderr_line)  # Print stderr line to the shell

            # If both stdout and stderr are empty, and the process is finished, break the loop
            if stdout_line == '' and stderr_line == '' and process.poll() is not None:
                break
            time.sleep(.1)
            if pollCheck():
                print("Checking GIT for Updates")
                if poll():
                    print("Updates found, Tearing down system")
                    break
                else:
                    print("No Updates Found")

    except KeyboardInterrupt:
        print("\nProcess interrupted. Terminating...")
        process.terminate()

    process.stdout.close()
    process.stderr.close()
    process.wait()  # Ensure the process has fully completed

    print("Command execution finished.")

if __name__ == "__main__":
    cli()