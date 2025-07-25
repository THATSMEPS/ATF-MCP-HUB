import subprocess
import time
from typing import Dict, Any
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import requests

# Tool: Create FastAPI-ready Python Slim Docker Container
fastapi_mcp = FastMCP(name="FastAPI Container MCP Server")

@fastapi_mcp.tool
async def create_docker_container(port: int = 8080) -> Dict[str, Any]:
    """
    Create a Docker container running python:<version>-slim, ready for FastAPI, exposing the given port.
    Returns container id and details.
    """
    container_name = f"fastapi-{int(time.time())}"
    image = f"python:3.13-slim"
    try:
        # Generate a unique 4-digit host port using current time (mmss), always 4 digits and valid
        host_port = 8080
        run_proc = subprocess.run([
            'docker', 'run', '-it', '-d', '--name', container_name,
            '-p', f'{host_port}:{port}', image, 'sleep', 'infinity'
        ], capture_output=True, text=True)
        if run_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Failed to start container: {run_proc.stderr}\nSTDOUT: {run_proc.stdout}"
            }
        container_id = run_proc.stdout.strip()
        # Create /app directory inside the container
        mkdir_proc = subprocess.run([
            'docker', 'exec', container_id, 'mkdir', '-p', 'app'
        ], capture_output=True, text=True)
        if mkdir_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Failed to create /app directory: {mkdir_proc.stderr}\nSTDOUT: {mkdir_proc.stdout}",
                'container_id': container_id,
                'container_name': container_name,
                'image': image,
                'port': port,
                'host_port': host_port
            }
        # Change working directory to /app (test with a harmless command)
        cd_proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c', 'cd app && pwd'
        ], capture_output=True, text=True)
        if cd_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Failed to cd into /app: {cd_proc.stderr}\nSTDOUT: {cd_proc.stdout}",
                'container_id': container_id,
                'container_name': container_name,
                'image': image,
                'port': port,
                'host_port': host_port
            }
        return {
            'status': 'success',
            'container_id': container_id,
            'container_name': container_name,
            'image': image,
            'port': port,
            'host_port': host_port,
            'message': f"Container '{container_name}' running with image '{image}' exposing container port {port} to host port {host_port}, /app directory created, and cd into /app successful.",
            'cd_output': cd_proc.stdout.strip()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Exception: {str(e)}"
        }

@fastapi_mcp.tool
async def github_repo_clone(ctx: Context, container_id: str, github_url: str) -> Dict[str, Any]:
    """
    Clone a GitHub repository into the /app directory of the specified Docker container.
    Args:
        ctx: FastMCP context for logging and progress
        container_id: The Docker container ID
        github_url: The GitHub repository URL (e.g., https://github.com/user/repo.git)
    Returns:
        Dictionary containing clone status, repo name, and output
    """
    await ctx.info(f"Starting to clone repository: {github_url} into container {container_id}:/app")
    if not github_url.startswith(('https://github.com/', 'git@github.com:')):
        raise ToolError("Invalid GitHub URL. Must start with 'https://github.com/' or 'git@github.com:'")
    try:
        # Extract repository name from URL
        if github_url.endswith('.git'):
            repo_name = github_url.split('/')[-1][:-4]
        else:
            repo_name = github_url.split('/')[-1]
        await ctx.info(f"Repository will be cloned as: {repo_name}")
        await ctx.report_progress(progress=0, total=100)
        # Ensure git is installed in the container
        git_check = subprocess.run([
            'docker', 'exec', container_id, 'which', 'git'
        ], capture_output=True, text=True)
        if git_check.returncode != 0:
            await ctx.info("Git not found in container, installing...")
            update_proc = subprocess.run([
                'docker', 'exec', container_id, 'apt-get', 'update'
            ], capture_output=True, text=True)
            if update_proc.returncode != 0:
                await ctx.error(f"Failed to update apt-get: {update_proc.stderr}\nSTDOUT: {update_proc.stdout}")
                raise ToolError(f"Failed to update apt-get: {update_proc.stderr}\nSTDOUT: {update_proc.stdout}")
            install_proc = subprocess.run([
                'docker', 'exec', container_id, 'apt-get', 'install', '-y', 'git'
            ], capture_output=True, text=True)
            if install_proc.returncode != 0:
                await ctx.error(f"Failed to install git: {install_proc.stderr}\nSTDOUT: {install_proc.stdout}")
                raise ToolError(f"Failed to install git: {install_proc.stderr}\nSTDOUT: {install_proc.stdout}")
        # Clone the repo into /app
        await ctx.info(f"Cloning repo into /app/{repo_name} in container {container_id}")
        clone_proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c', f'cd app && git clone {github_url}'
        ], capture_output=True, text=True)
        await ctx.report_progress(progress=80, total=100)
        if clone_proc.returncode != 0:
            error_msg = f"Git clone failed: {clone_proc.stderr}\nSTDOUT: {clone_proc.stdout}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        await ctx.report_progress(progress=100, total=100)
        await ctx.info(f"Successfully cloned repository to /app/{repo_name} in container {container_id}")
        return {
            'status': 'success',
            'message': 'Repository cloned successfully',
            'container_id': container_id,
            'repo_name': repo_name,
            'container_path': f'/app/{repo_name}',
            'stdout': clone_proc.stdout.strip()
        }
    except subprocess.TimeoutExpired:
        error_msg = "Git clone operation timed out (5 minutes)"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during clone: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

@fastapi_mcp.tool
def install_requirements(container_id: str, repo_name: str) -> dict:
    """
    Install requirements.txt in the given repo directory inside the container. repo_name should be the name of the repo cloned to /app/repo_name.
    """
    try:
        # Run pip install -r requirements.txt in the repo directory
        install_proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c', f'cd app/{repo_name} && pip install -r requirements.txt'
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        stdout = install_proc.stdout if install_proc.stdout is not None else ''
        stderr = install_proc.stderr if install_proc.stderr is not None else ''
        if install_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f'Failed to install requirements: {stderr}\nSTDOUT: {stdout}',
                'container_id': container_id,
                'repo_name': repo_name
            }
        return {
            'status': 'success',
            'message': 'Requirements installed.',
            'stdout': stdout.strip(),
            'container_id': container_id,
            'repo_name': repo_name
        }
    except subprocess.TimeoutExpired:
        return {
            'status': 'error',
            'message': 'pip install operation timed out (15 minutes)'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@fastapi_mcp.tool
def start_backend(container_id: str, repo_name: str, run_command: str) -> dict:
    """
    Start the FastAPI backend inside the specified container and repo directory using the provided run command.
    Args:
        container_id: The Docker container ID
        repo_name: The name of the repository (directory under /app)
        run_command: The command to run (e.g., 'uvicorn main:app --reload')
    Returns:
        dict: Status, message, and info about the running backend
    """
    try:
        # Always ensure --host 0.0.0.0 in the run_command for accessibility
        if '--host' not in run_command:
            run_command += ' --host 0.0.0.0'
        # Run the command in the background inside the container at /app/repo_name
        bash_cmd = f"cd app/{repo_name} && nohup {run_command} > fastapi.log 2>&1 &"
        proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c', bash_cmd
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f'Failed to start backend: {proc.stderr}\nSTDOUT: {proc.stdout}',
                'container_id': container_id,
                'repo_name': repo_name
            }
        return {
            'status': 'success',
            'message': f'Backend started successfully using command: {run_command}',
            'container_id': container_id,
            'repo_name': repo_name
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@fastapi_mcp.tool
def requests(
    host_port: int,
    http_method: str,
    api_endpoint: str,
    json_input: dict = {}
) -> dict:
    """
    Make an HTTP request to the FastAPI backend running in the Docker container.

    Args:
        host_port: The host port mapped to the container's FastAPI port.
        http_method: HTTP method as a string (GET, POST, PATCH, PUT, DELETE).
        api_endpoint: The API endpoint (e.g., '/predict').
        json_input: Optional JSON data for POST, PUT, PATCH, DELETE.

    Returns:
        dict: Status, response, and error (if any).
    """
    # Ensure endpoint starts with /
    if not api_endpoint.startswith("/"):
        api_endpoint = "/" + api_endpoint
    url = f"http://localhost:{host_port}{api_endpoint}"
    method = http_method.upper()
    import requests as pyrequests
    try:
        if method == "GET":
            resp = pyrequests.get(url)
        elif method == "POST":
            resp = pyrequests.post(url, json=json_input if json_input else None)
        elif method == "PUT":
            resp = pyrequests.put(url, json=json_input if json_input else None)
        elif method == "PATCH":
            resp = pyrequests.patch(url, json=json_input if json_input else None)
        elif method == "DELETE":
            resp = pyrequests.delete(url, json=json_input if json_input else None)
        else:
            return {
                "status": "error",
                "message": f"Unsupported HTTP method: {http_method}"
            }
        try:
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                response_data = resp.json()
            else:
                response_data = resp.text
        except Exception:
            response_data = resp.text
        return {
            "status": "success",
            "status_code": resp.status_code,
            "response": response_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}"
        }
    

if __name__ == "__main__":
    print("🚀 Starting Fastapi Container MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server endpoints available at:")
    print("🌐 Server available at: http://127.0.0.1:8003/fastapi/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    fastapi_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8003,
        path="/fastapi/mcp",
        log_level="info"
    )