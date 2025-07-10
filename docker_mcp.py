import subprocess
import os
import time
import json
from typing import Dict, Any
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

# Default port configuration
DEFAULT_NODEJS_PORT = 3000
DEFAULT_PYTHON_PORT = 8000

docker_mcp = FastMCP(name="Docker MCP Server")

@docker_mcp.tool
async def create_and_run_docker(github_url: str, project_type: str, ctx: Context) -> Dict[str, Any]:
    """
    Create a Docker image, build and run it from a GitHub URL.

    Args:
        github_url: The GitHub repository URL
        project_type: Type of project ('python' or 'nodejs')

    Returns:
        Dictionary containing build, run status and details
    """
    try:
        # Create and build Docker image
        build_result = await create_docker_image_internal(github_url, project_type, ctx)

        if build_result['status'] != 'success':
            raise ToolError("Docker image creation failed")

        image_name = build_result['image_name']
        await ctx.info(f"Starting container from image: {image_name}")

        # Verify image exists before running
        verify_process = subprocess.run(
            ['docker', 'image', 'inspect', image_name],
            capture_output=True,
            text=True
        )

        if verify_process.returncode != 0:
            raise ToolError(f"Image verification failed: {verify_process.stderr}")

        # Set port based on project type
        default_port = str(DEFAULT_NODEJS_PORT if project_type.lower() == 'nodejs' else DEFAULT_PYTHON_PORT)
        
        # Run container with port configuration
        run_process = subprocess.run(
            [
                'docker', 'run',
                '-d',  # Run in detached mode
                '-e', f"DEFAULT_PORT={default_port}",  # Set default port
                '-p', f"{default_port}:{default_port}",  # Port mapping
                '--name', f"{image_name.replace(':', '-')}-container",
                image_name
            ],
            check=True,
            capture_output=True,
            text=True
        )

        if run_process.returncode != 0:
            raise ToolError(f"Docker run failed: {run_process.stderr}")

        container_id = run_process.stdout.strip()

        # Get container details
        inspect_process = subprocess.run(
            ['docker', 'inspect', container_id],
            check=True,
            capture_output=True,
            text=True
        )

        container_info = json.loads(inspect_process.stdout)[0]
        container_ip = container_info['NetworkSettings']['IPAddress']

        await ctx.info(f"Container running at http://localhost:{default_port}")

        return {
            'status': 'success',
            'image_name': image_name,
            'container_id': container_id,
            'container_ip': container_ip,
            'port': default_port,
            'url': f"http://localhost:{default_port}"
        }

    except Exception as e:
        error_msg = f"Error in create and run process: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def create_docker_image_internal(github_url: str, project_type: str, ctx: Context) -> Dict[str, Any]:
    """Internal function to create Docker image"""
    try:
        if project_type.lower() not in ['python', 'nodejs']:
            raise ToolError("Project type must be either 'python' or 'nodejs'")

        # Create temporary directory for Dockerfile
        temp_dir = os.path.join(os.getcwd(), 'docker_builds')
        os.makedirs(temp_dir, exist_ok=True)

        repo_name = github_url.split('/')[-1].replace('.git', '')
        build_dir = os.path.join(temp_dir, repo_name)
        os.makedirs(build_dir, exist_ok=True)

        # Generate Dockerfile
        dockerfile_content = await generate_dockerfile(project_type.lower(), github_url, ctx)
        dockerfile_path = os.path.join(build_dir, 'Dockerfile')

        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)

        await ctx.report_progress(progress=30, total=100)

        # Build Docker image
        image_name = f"{repo_name.lower()}:{project_type.lower()}"
        await ctx.info(f"Building Docker image: {image_name}")

        build_process = subprocess.run(
            ['docker', 'build', '-t', image_name, build_dir, '--progress=plain'],
            check=True,
            capture_output=True,
            text=True
        )

        # Log build output
        await ctx.info("Docker Build Output:\n" + build_process.stdout)
        if build_process.stderr:
            await ctx.info("Docker Build Logs:\n" + build_process.stderr)

        if build_process.returncode != 0:
            raise ToolError(f"Docker build failed: {build_process.stderr}")

        await ctx.report_progress(progress=100, total=100)

        return {
            'status': 'success',
            'image_name': image_name,
            'dockerfile_path': dockerfile_path
        }

    except Exception as e:
        error_msg = f"Error creating Docker image: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def generate_dockerfile(project_type: str, github_url: str, ctx: Context) -> str:
    """Generate Dockerfile content with port detection inside the container"""
    if project_type == 'python':
        return f"""FROM python:3.14.0b3-alpine3.21

# Install git and required tools
RUN apk add --no-cache git grep

# Set working directory
WORKDIR /app

# Clone the repository
RUN git clone {github_url} .

# Install dependencies if they exist
RUN if [ -f "requirements.txt" ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN if [ -f "pyproject.toml" ]; then pip install --no-cache-dir .; fi

# Set default port
ENV DEFAULT_PORT={DEFAULT_PYTHON_PORT}

# Set up entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \\
    echo 'PORT=\${DEFAULT_PYTHON_PORT}' >> /entrypoint.sh && \\
    echo 'echo "Using port: \${DEFAULT_PYTHON_PORT}"' >> /entrypoint.sh && \\
    echo 'if [ -f "app.py" ]; then' >> /entrypoint.sh && \\
    echo '  python app.py --port \${DEFAULT_PYTHON_PORT}' >> /entrypoint.sh && \\
    echo 'elif [ -f "main.py" ]; then' >> /entrypoint.sh && \\
    echo '  python main.py --port \${DEFAULT_PYTHON_PORT}' >> /entrypoint.sh && \\
    echo 'elif [ -f "run.py" ]; then' >> /entrypoint.sh && \\
    echo '  python run.py --port \${DEFAULT_PYTHON_PORT}' >> /entrypoint.sh && \\
    echo 'else' >> /entrypoint.sh && \\
    echo '  python app.py --port \${DEFAULT_PYTHON_PORT}' >> /entrypoint.sh && \\
    echo 'fi' >> /entrypoint.sh && \\
    chmod +x /entrypoint.sh

EXPOSE ${DEFAULT_PYTHON_PORT}
CMD ["/entrypoint.sh"]
"""

    elif project_type == 'nodejs':
        return f"""FROM node:24-alpine3.21

# Install git and grep
RUN apk add --no-cache git grep

# Set working directory
WORKDIR /app

# Clone the repository
RUN git clone {github_url} .

# Install dependencies
RUN npm install

# Set default port
ENV DEFAULT_PORT={DEFAULT_NODEJS_PORT}

# Set up entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \\
    echo 'PORT={DEFAULT_NODEJS_PORT}' >> /entrypoint.sh && \\
    echo 'echo "Using port: \{DEFAULT_NODEJS_PORT}"' >> /entrypoint.sh && \\
    echo 'if [ -f "package.json" ]; then' >> /entrypoint.sh && \\
    echo '  main_file=$(node -p "require(\\\"./package.json\\\").main || \\\"index.js\\\"")' >> /entrypoint.sh && \\
    echo '  PORT=\{DEFAULT_NODEJS_PORT} node "$main_file"' >> /entrypoint.sh && \\
    echo 'else' >> /entrypoint.sh && \\
    echo '  PORT=\{DEFAULT_NODEJS_PORT} node index.js' >> /entrypoint.sh && \\
    echo 'fi' >> /entrypoint.sh && \\
    chmod +x /entrypoint.sh

EXPOSE ${DEFAULT_NODEJS_PORT}
CMD ["/entrypoint.sh"]
"""

# ...existing imports and code...
@docker_mcp.tool
async def kill_container(container_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Kill/stop a running Docker container by its ID or name.

    Args:
        container_id: The container ID or name to kill

    Returns:
        Dictionary containing kill operation status and details
    """
    try:
        # Verify container exists
        verify_process = subprocess.run(
            ['docker', 'inspect', container_id],
            capture_output=True,
            text=True
        )

        if verify_process.returncode != 0:
            raise ToolError(f"Container {container_id} not found")

        await ctx.info(f"Stopping container: {container_id}")

        # Stop the container
        stop_process = subprocess.run(
            ['docker', 'stop', container_id],
            check=True,
            capture_output=True,
            text=True
        )

        if stop_process.returncode != 0:
            raise ToolError(f"Failed to stop container: {stop_process.stderr}")

        # Remove the container
        remove_process = subprocess.run(
            ['docker', 'rm', container_id],
            check=True,
            capture_output=True,
            text=True
        )

        if remove_process.returncode != 0:
            raise ToolError(f"Failed to remove container: {remove_process.stderr}")

        await ctx.info(f"Container {container_id} successfully stopped and removed")

        return {
            'status': 'success',
            'container_id': container_id,
            'message': 'Container stopped and removed successfully'
        }

    except Exception as e:
        error_msg = f"Error killing container: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)


if __name__ == "__main__":
    print("🐳 Starting Docker MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server will be available at: http://127.0.0.1:8002/docker/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    docker_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8002,
        path="/docker/mcp",
        log_level="info"  
    )