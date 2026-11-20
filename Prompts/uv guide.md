What is uv?
 
uv is a modern Python dependency manager and environment tool that:
	• Creates and manages virtual environments (uv venv)
	• Resolves and installs Python dependencies (uv pip install / uv sync)
	• Locks exact versions in uv.lock for reproducibility
	• Is designed to be faster and more deterministic than traditional pip
 
uv = virtual environment manager + fast dependency resolver + package installer


Core features of uv
 
Virtual environments
uv venv          # creates default .venv
uv venv myenv    # custom env name
uv venv --python 3.11  # specific Python version
 
uv init 

Dependency installation
uv pip install requests

uv add requests


Dependency synchronization
uv sync
 
	• Reads pyproject.toml and uv.lock
	• Resolves all dependencies and sub-dependencies
	• Installs missing packages
	• Updates/downgrades to exact versions in the lock file
	• Removes extra packages that don’t belong
 
Locking dependencies
	• uv.lock stores exact versions of all packages
	• Ensures reproducible builds across machines
	• Automatically updated when dependencies change

 source .venv/bin/activate   
