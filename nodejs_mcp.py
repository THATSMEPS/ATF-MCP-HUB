import subprocess
import time
from typing import Dict, Any
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import requests

# Tool: Create Node.js-ready Docker Container
nodejs_mcp = FastMCP(name="Node.js Container MCP Server")

@nodejs_mcp.tool
async def create_docker_container(port: int = 3000) -> Dict[str, Any]:
    """
    Create a Docker container running node:latest, ready for Node.js/Express, exposing the given port.
    Returns container id and details.
    """
    container_name = f"nodejs-{int(time.time())}"
    image = f"node:20-alpine"
    try:
        # Generate a unique 4-digit host port using current time (mmss), always 4 digits and valid
        host_port = 3000
        run_proc = subprocess.run([
            'docker', 'run', '-d', '--name', container_name,
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
            'docker', 'exec', container_id, 'sh', '-c', 'cd app && pwd'
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

@nodejs_mcp.tool
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
                'docker', 'exec', container_id, 'apk', 'update'
            ], capture_output=True, text=True)
            if update_proc.returncode != 0:
                await ctx.error(f"Failed to update apk: {update_proc.stderr}\nSTDOUT: {update_proc.stdout}")
                raise ToolError(f"Failed to update apk: {update_proc.stderr}\nSTDOUT: {update_proc.stdout}")
            
            install_proc = subprocess.run([
                'docker', 'exec', container_id, 'apk', 'add', 'git'
            ], capture_output=True, text=True)
            if install_proc.returncode != 0:
                await ctx.error(f"Failed to install git: {install_proc.stderr}\nSTDOUT: {install_proc.stdout}")
                raise ToolError(f"Failed to install git: {install_proc.stderr}\nSTDOUT: {install_proc.stdout}")
        
        # Create a new folder for the repo and clone into it
        await ctx.info(f"Creating new folder /app/{repo_name} and cloning repo into it")
        mkdir_repo_proc = subprocess.run([
            'docker', 'exec', container_id, 'mkdir', '-p', f'app/{repo_name}'
        ], capture_output=True, text=True)
        
        if mkdir_repo_proc.returncode != 0:
            error_msg = f"Failed to create repo directory: {mkdir_repo_proc.stderr}\nSTDOUT: {mkdir_repo_proc.stdout}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
        # Clone the repo into the new folder
        await ctx.info(f"Cloning repo into /app/{repo_name} in container {container_id}")
        clone_proc = subprocess.run([
            'docker', 'exec', container_id, 'sh', '-c', f'cd app/{repo_name} && git clone {github_url} .'
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

@nodejs_mcp.tool
def install_dependencies(container_id: str, repo_name: str) -> dict:
    """
    Install package.json dependencies in the given repo directory inside the container. 
    repo_name should be the name of the repo cloned to /app/repo_name.
    """
    try:
        # Run npm install in the repo directory
        install_proc = subprocess.run([
            'docker', 'exec', container_id, 'sh', '-c', f'cd app/{repo_name} && npm install'
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        
        stdout = install_proc.stdout if install_proc.stdout is not None else ''
        stderr = install_proc.stderr if install_proc.stderr is not None else ''
        
        if install_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f'Failed to install dependencies: {stderr}\nSTDOUT: {stdout}',
                'container_id': container_id,
                'repo_name': repo_name
            }
        
        return {
            'status': 'success',
            'message': 'Dependencies installed.',
            'stdout': stdout.strip(),
            'container_id': container_id,
            'repo_name': repo_name
        }
    except subprocess.TimeoutExpired:
        return {
            'status': 'error',
            'message': 'npm install operation timed out (15 minutes)'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@nodejs_mcp.tool
def start_server(container_id: str, repo_name: str, run_command: str = None) -> dict:
    """
    Start the Node.js/Express server inside the specified container and repo directory.
    If no run_command is provided, it will read package.json and use the main entry point.
    Args:
        container_id: The Docker container ID
        repo_name: The name of the repository (directory under /app)
        run_command: Optional command to run. If None, will auto-detect from package.json
    Returns:
        dict: Status, message, and info about the running server
    """
    try:
        # If no run_command provided, read package.json to determine the command
        if run_command is None:
            # Read package.json to get main entry point and scripts
            package_result = read_package_json(container_id, repo_name)
            
            if package_result['status'] == 'error':
                return {
                    'status': 'error',
                    'message': f'Failed to read package.json: {package_result["message"]}',
                    'container_id': container_id,
                    'repo_name': repo_name
                }
            
            scripts = package_result.get('scripts', {})
            main_entry = package_result.get('main_entry', 'index.js')
            
            # Determine the best command to use
            if 'start' in scripts:
                run_command = 'npm start'
            elif 'dev' in scripts:
                run_command = 'npm run dev'
            elif main_entry:
                run_command = f'node {main_entry}'
            else:
                run_command = 'node index.js'  # fallback
        
        # Run the command in the background inside the container at /app/repo_name
        bash_cmd = f"cd app/{repo_name} && nohup {run_command} > nodejs.log 2>&1 &"
        proc = subprocess.run([
            'docker', 'exec', container_id, 'sh', '-c', bash_cmd
        ], capture_output=True, text=True)
        
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f'Failed to start server: {proc.stderr}\nSTDOUT: {proc.stdout}',
                'container_id': container_id,
                'repo_name': repo_name,
                'attempted_command': run_command
            }
        
        return {
            'status': 'success',
            'message': f'Node.js server started successfully using command: {run_command}',
            'container_id': container_id,
            'repo_name': repo_name,
            'command_used': run_command
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@nodejs_mcp.tool
def create_express_server(container_id: str, repo_name: str, port: int = 3000) -> dict:
    """
    Create a basic Express.js server file in the specified container and repo directory.
    Args:
        container_id: The Docker container ID
        repo_name: The name of the repository (directory under /app)
        port: The port for the Express server (default: 3000)
    Returns:
        dict: Status and message about server file creation
    """
    try:
        # Create a basic Express server
        express_server_code = f'''const express = require('express');
const app = express();
const port = process.env.PORT || {port};

// Middleware to parse JSON
app.use(express.json());

// Basic route
app.get('/', (req, res) => {{
  res.json({{ message: 'Hello from Express.js server!' }});
}});

// Health check endpoint
app.get('/health', (req, res) => {{
  res.json({{ status: 'OK', timestamp: new Date().toISOString() }});
}});

// Start server
app.listen(port, '0.0.0.0', () => {{
  console.log(`Server running on port ${{port}}`);
}});

module.exports = app;
'''
        
        # Write the server file
        write_proc = subprocess.run([
            'docker', 'exec', container_id, 'sh', '-c', 
            f'cd app/{repo_name} && echo \'{express_server_code}\' > server.js'
        ], capture_output=True, text=True)
        
        if write_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f'Failed to create server file: {write_proc.stderr}\nSTDOUT: {write_proc.stdout}',
                'container_id': container_id,
                'repo_name': repo_name
            }
        
        # Create package.json if it doesn't exist
        package_json = f'''{{
  "name": "{repo_name}",
  "version": "1.0.0",
  "description": "Express.js server",
  "main": "server.js",
  "scripts": {{
    "start": "node server.js",
    "dev": "nodemon server.js"
  }},
  "dependencies": {{
    "express": "^4.18.2"
  }},
  "devDependencies": {{
    "nodemon": "^3.0.1"
  }}
}}
'''
        
        # Check if package.json exists
        check_proc = subprocess.run([
            'docker', 'exec', container_id, 'sh', '-c', f'cd app/{repo_name} && ls package.json'
        ], capture_output=True, text=True)
        
        if check_proc.returncode != 0:
            # Create package.json
            package_proc = subprocess.run([
                'docker', 'exec', container_id, 'sh', '-c', 
                f'cd app/{repo_name} && echo \'{package_json}\' > package.json'
            ], capture_output=True, text=True)
            
            if package_proc.returncode != 0:
                return {
                    'status': 'error',
                    'message': f'Failed to create package.json: {package_proc.stderr}\nSTDOUT: {package_proc.stdout}',
                    'container_id': container_id,
                    'repo_name': repo_name
                }
        
        return {
            'status': 'success',
            'message': f'Express server file created successfully at /app/{repo_name}/server.js',
            'container_id': container_id,
            'repo_name': repo_name,
            'server_file': 'server.js',
            'port': port
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@nodejs_mcp.tool
def requests(
    host_port: int,
    http_method: str,
    api_endpoint: str,
    json_input: dict = {},
    headers: dict = {}
) -> dict:
    """
    Make an HTTP request to the Node.js/Express server running in the Docker container.

    Args:
        host_port: The host port mapped to the container's Node.js port.
        http_method: HTTP method as a string (GET, POST, PATCH, PUT, DELETE).
        api_endpoint: The API endpoint (e.g., '/api/users').
        json_input: Optional JSON data for POST, PUT, PATCH, DELETE.
        headers: Optional headers dictionary.

    Returns:
        dict: Status, response, and error (if any).
    """
    # Ensure endpoint starts with /
    if not api_endpoint.startswith("/"):
        api_endpoint = "/" + api_endpoint
    
    url = f"http://localhost:{host_port}{api_endpoint}"
    method = http_method.upper()
    
    # Default headers
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    import requests as pyrequests
    
    try:
        if method == "GET":
            resp = pyrequests.get(url, headers=default_headers)
        elif method == "POST":
            resp = pyrequests.post(url, json=json_input if json_input else None, headers=default_headers)
        elif method == "PUT":
            resp = pyrequests.put(url, json=json_input if json_input else None, headers=default_headers)
        elif method == "PATCH":
            resp = pyrequests.patch(url, json=json_input if json_input else None, headers=default_headers)
        elif method == "DELETE":
            resp = pyrequests.delete(url, json=json_input if json_input else None, headers=default_headers)
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
            "response": response_data,
            "headers": dict(resp.headers)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}"
        }

@nodejs_mcp.tool
def get_server_logs(container_id: str, repo_name: str, lines: int = 50) -> dict:
    """
    Get the logs from the Node.js server running in the container.
    Args:
        container_id: The Docker container ID
        repo_name: The name of the repository (directory under /app)
        lines: Number of log lines to retrieve (default: 50)
    Returns:
        dict: Status and log content
    """
    try:
        # Get logs from the nodejs.log file
        logs_proc = subprocess.run([
            'docker', 'exec', container_id, 'sh', '-c', 
            f'cd app/{repo_name} && tail -n {lines} nodejs.log 2>/dev/null || echo "No logs found"'
        ], capture_output=True, text=True)
        
        if logs_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f'Failed to get logs: {logs_proc.stderr}\nSTDOUT: {logs_proc.stdout}',
                'container_id': container_id,
                'repo_name': repo_name
            }
        
        return {
            'status': 'success',
            'message': 'Logs retrieved successfully',
            'logs': logs_proc.stdout.strip(),
            'container_id': container_id,
            'repo_name': repo_name
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@nodejs_mcp.tool
def read_package_json(container_id: str, repo_name: str) -> dict:
    """
    Read package.json from the cloned repository and extract main entry point and scripts.
    Args:
        container_id: The Docker container ID
        repo_name: The name of the repository (directory under /app)
    Returns:
        dict: Status, main entry point, scripts, and package.json content
    """
    try:
        # Read package.json content
        read_proc = subprocess.run([
            'docker', 'exec', container_id, 'sh', '-c', f'cd app/{repo_name} && cat package.json'
        ], capture_output=True, text=True)
        
        if read_proc.returncode != 0:
            return {
                'status': 'error',
                'message': f'Failed to read package.json: {read_proc.stderr}\nSTDOUT: {read_proc.stdout}',
                'container_id': container_id,
                'repo_name': repo_name
            }
        
        try:
            import json
            package_data = json.loads(read_proc.stdout)
            
            # Extract main entry point (default to index.js if not specified)
            main_entry = package_data.get('main', 'index.js')
            
            # Extract scripts
            scripts = package_data.get('scripts', {})
            
            # Get name and version
            name = package_data.get('name', repo_name)
            version = package_data.get('version', '1.0.0')
            
            return {
                'status': 'success',
                'message': 'package.json read successfully',
                'container_id': container_id,
                'repo_name': repo_name,
                'main_entry': main_entry,
                'scripts': scripts,
                'name': name,
                'version': version,
                'package_json': package_data
            }
        except json.JSONDecodeError as e:
            return {
                'status': 'error',
                'message': f'Failed to parse package.json: {str(e)}',
                'container_id': container_id,
                'repo_name': repo_name,
                'raw_content': read_proc.stdout
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

@nodejs_mcp.tool
async def clone_install_and_start(ctx: Context, container_id: str, github_url: str, port: int = 3000) -> dict:
    """
    Complete workflow: Clone GitHub repo, install dependencies, read package.json, and start server.
    Args:
        ctx: FastMCP context for logging and progress
        container_id: The Docker container ID
        github_url: The GitHub repository URL
        port: The port for the server (default: 3000)
    Returns:
        dict: Status and details of the complete workflow
    """
    try:
        await ctx.info("Starting complete Node.js deployment workflow...")
        await ctx.report_progress(progress=0, total=100)
        
        # Step 1: Clone repository
        await ctx.info("Step 1: Cloning GitHub repository...")
        clone_result = await github_repo_clone(ctx, container_id, github_url)
        if clone_result['status'] == 'error':
            return {
                'status': 'error',
                'step': 'clone',
                'message': f"Failed at clone step: {clone_result['message']}",
                'details': clone_result
            }
        
        repo_name = clone_result['repo_name']
        await ctx.report_progress(progress=25, total=100)
        
        # Step 2: Install dependencies
        await ctx.info("Step 2: Installing dependencies...")
        install_result = install_dependencies(container_id, repo_name)
        if install_result['status'] == 'error':
            return {
                'status': 'error',
                'step': 'install_dependencies',
                'message': f"Failed at install step: {install_result['message']}",
                'details': install_result,
                'repo_name': repo_name
            }
        
        await ctx.report_progress(progress=50, total=100)
        
        # Step 3: Read package.json
        await ctx.info("Step 3: Reading package.json...")
        package_result = read_package_json(container_id, repo_name)
        if package_result['status'] == 'error':
            return {
                'status': 'error',
                'step': 'read_package_json',
                'message': f"Failed to read package.json: {package_result['message']}",
                'details': package_result,
                'repo_name': repo_name
            }
        
        await ctx.report_progress(progress=75, total=100)
        
        # Step 4: Start server
        await ctx.info("Step 4: Starting server...")
        start_result = start_server(container_id, repo_name)
        if start_result['status'] == 'error':
            return {
                'status': 'error',
                'step': 'start_server',
                'message': f"Failed to start server: {start_result['message']}",
                'details': start_result,
                'repo_name': repo_name,
                'package_info': package_result
            }
        
        await ctx.report_progress(progress=100, total=100)
        await ctx.info("Complete workflow finished successfully!")
        
        return {
            'status': 'success',
            'message': 'Complete Node.js deployment workflow completed successfully',
            'container_id': container_id,
            'repo_name': repo_name,
            'clone_details': clone_result,
            'install_details': install_result,
            'package_details': package_result,
            'start_details': start_result,
            'main_entry': package_result.get('main_entry'),
            'command_used': start_result.get('command_used'),
            'server_port': port
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in workflow: {str(e)}"
        await ctx.error(error_msg)
        return {
            'status': 'error',
            'step': 'workflow',
            'message': error_msg
        }

if __name__ == "__main__":
    print("🚀 Starting Node.js Container MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server available at: http://127.0.0.1:8008/nodejs/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    nodejs_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8008,
        path="/nodejs/mcp",
        log_level="info"
    )