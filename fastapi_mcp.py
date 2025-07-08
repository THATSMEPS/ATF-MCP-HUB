import subprocess
import time
from typing import Dict, Any
from fastmcp import FastMCP, Context

# Tool: Create FastAPI-ready Python Slim Docker Container
mcp = FastMCP(name="FastAPI Container MCP Server")

@mcp.tool
async def create_docker_container(port: int = 8080) -> Dict[str, Any]:
    """
    Create a Docker container running python:<version>-slim, ready for FastAPI, exposing the given port.
    Installs fastapi and uvicorn in the container. Returns container id and details.
    """
    container_name = f"fastapi-{int(time.time())}"
    image = f"python:3.13-slim"
    try:
        # Run the container (detached, with port mapping, and keep it running)
        run_proc = subprocess.run([
            'docker', 'run', '-d', '--name', container_name,
            '-p', f'{port}:8000', image, 'sleep', 'infinity'
        ], capture_output=True, text=True)
        if run_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Failed to start container: {run_proc.stderr}\nSTDOUT: {run_proc.stdout}"
            }
        container_id = run_proc.stdout.strip()
        # Install fastapi and uvicorn in the running container
        pip_proc = subprocess.run([
            'docker', 'exec', container_name, 'pip', 'install', 'fastapi', 'uvicorn[standard]'
        ], capture_output=True, text=True)
        if pip_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Failed to install FastAPI/Uvicorn: {pip_proc.stderr}\nSTDOUT: {pip_proc.stdout}",
                'container_id': container_id,
                'container_name': container_name,
                'image': image,
                'port': port
            }
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
                'port': port
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
                'port': port
            }
        return {
            'status': 'success',
            'container_id': container_id,
            'container_name': container_name,
            'image': image,
            'port': port,
            'message': f"Container '{container_name}' running with image '{image}' on port {port}, FastAPI-ready, /app directory created, and cd into /app successful.",
            'cd_output': cd_proc.stdout.strip()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Exception: {str(e)}"
        }
