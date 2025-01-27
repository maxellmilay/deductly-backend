import os
import subprocess
import sys
import shutil


def run_command(command, description):
    """Run a shell command and display its progress."""
    print(f"\n[INFO] {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True)
        print(f"[SUCCESS] {description} completed.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} failed with error: {e}")
        sys.exit(1)


def find_pip_command():
    """Determine the correct pip command to use."""
    for pip_cmd in ["pip", "pip3"]:
        if shutil.which(pip_cmd):  # Check if the command exists in PATH
            return pip_cmd
    print(
        "[ERROR] pip is not installed or not in PATH. Please install pip and try again."
    )
    sys.exit(1)


def main():
    # Step 1: Find the appropriate pip command
    pip_cmd = find_pip_command()

    # Step 2: Install dependencies from requirements.txt
    if os.path.exists("requirements.txt"):
        run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies")
    else:
        print("[WARNING] requirements.txt not found. Skipping dependency installation.")

    # Step 2: Install pre-commit hooks
    run_command("pre-commit install", "Installing pre-commit hooks")


if __name__ == "__main__":
    main()
