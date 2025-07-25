# ATF MCP Hub

**ATF = Automated Tool Framework**

A modular Python toolkit for running and interacting with various code-processing servers (MCPs) in containers. Supports code execution, dependency analysis, image processing, database queries, and more, using user-provided GitHub repositories.

## Features

- Run code from user GitHub repos in isolated containers
- Dependency analysis (Python, Node.js, etc.)
- Image processing tools
- Database query tools (MySQL, MongoDB)
- FastAPI/Starlette HTTP endpoints for each MCP
- Modular architecture: add new MCPs easily

## Directory Structure

- `main_mcp.py` — Main server entry point
- `docker_mcp.py`, `git_clone_mcp.py`, etc. — Individual MCP server modules
- `pyproject.toml` — Project dependencies
- `sample_problems/` — Example input files
- `image_contest_runs/` — Output directory for image processing runs
- `README.md` — This file

## Installation

1. **Clone the repo:**
   ```powershell
git clone <your-repo-url>
cd atf-mcp-hub
```

2. **Install Python (>=3.13) and pip.**

3. **Create a virtual environment (recommended):**
   ```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

4. **Install dependencies using `pip` and `pyproject.toml`:**
   ```powershell
pip install toml
pip install -r requirements.txt
```
   Or, if using PEP 621/modern standards:
   ```powershell
pip install .
```

   *Note: If you need to parse TOML files directly, install `toml` or `tomli`.*

## Running the Code

- **Start the main MCP server:**
  ```powershell
python main_mcp.py
```
  This will launch all MCP endpoints. See the printed URLs for available tools.

- **Run with FastAPI/Starlette:**
  Edit `main_mcp.py` to call `run_fast_api()` instead of the default runner.

## Testing

- **Manual Testing:**  
  Access endpoints via browser or API client (e.g., Postman) at the URLs printed on startup.

- **Automated Testing:**  
  Add test scripts or use Python’s `unittest` or `pytest` to test individual MCP modules.

## Inspector Usage

- **Debugging:**  
  Use Python’s built-in `inspect` module or VS Code’s debugger to step through MCP logic.

- **Example:**
  ```python
import inspect
print(inspect.getmembers(docker_mcp))
```

## Adding New MCPs

1. Create a new `<name>_mcp.py` module.
2. Implement the required MCP interface.
3. Import and mount it in `main_mcp.py`.

## Dependencies

See `pyproject.toml` for a full list. Key packages:
- `fastmcp`
- `mysql-connector-python`
- `pymongo`
- `opencv-python`, `numpy`, `matplotlib`, `pillow`, `scikit-image`
- `playwright`
- `requests`

## Notes

- All MCPs run in containers for isolation.
- This repo is not a contest platform; it’s a general-purpose MCP hub.

---

**Repo Name Suggestion:** `atf-mcp-hub`

*ATF = Automated Tool Framework*
