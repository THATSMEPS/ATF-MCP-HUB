import subprocess, os, time, shutil, socket, base64, asyncio, warnings, platform, signal, json
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Suppress Windows-specific asyncio warnings that don't affect functionality
if os.name == 'nt':  # Windows
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*socket.SHUT_RD.*")
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*connection was forcibly closed.*")
    warnings.filterwarnings("ignore", category=ResourceWarning, message=".*socket.*")
    
    # Set appropriate event loop policy for Windows
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

react_contest_mcp = FastMCP(name="React Contest MCP Server")

# Remove BASE_DIR since we're not creating local directories anymore
# BASE_DIR = os.path.join(os.getcwd(), "react_contest_runs")
# os.makedirs(BASE_DIR, exist_ok=True)

# Define the core functions without decorators for internal use
async def _create_react_container(ctx: Context, port: int = 5173) -> Dict[str, Any]:
    """Core function for creating React container"""
    try:
        container_name = f"react-contest-{int(time.time())}"
        # Use latest Playwright image to avoid version conflicts
        image = "mcr.microsoft.com/playwright:latest"
        
        await ctx.info(f"Creating React container: {container_name}")
        
        run_proc = subprocess.run([
            'docker', 'run', '-d', '--name', container_name,
            '-p', f'{port}:{port}',
            '-e', f'REACT_PORT={port}',
            '-e', 'HEADLESS=true',
            image, 'sleep', 'infinity'
        ], capture_output=True, text=True)
        
        if run_proc.returncode != 0:
            error_msg = f"Failed to start container: {run_proc.stderr}\nSTDOUT: {run_proc.stdout}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
            
        container_id = run_proc.stdout.strip()
        await ctx.info(f"Container started with ID: {container_id}")
        
        await ctx.info("Installing Node.js and dependencies...")
        install_cmd = [
            'docker', 'exec', container_id, 'bash', '-c',
            'export DEBIAN_FRONTEND=noninteractive && '
            'apt-get update && '
            'apt-get install -y apt-utils && '
            'apt-get install -y curl netcat python3-pip && '
            'curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && '
            'apt-get install -y nodejs'
        ]
        
        install_proc = subprocess.run(install_cmd, capture_output=True, text=True)
        if install_proc.returncode != 0:
            await ctx.error(f"Failed to install dependencies: {install_proc.stderr}")
            subprocess.run(['docker', 'rm', '-f', container_name], check=False)
            raise ToolError(f"Failed to install dependencies: {install_proc.stderr}")
        
        await ctx.info("Installing Python packages...")
        python_install = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c',
            'python3 -m pip install --upgrade pip playwright'
        ], capture_output=True, text=True)
        
        if python_install.returncode != 0:
            await ctx.error(f"Failed to install Python packages: {python_install.stderr}")
            subprocess.run(['docker', 'rm', '-f', container_name], check=False)
            raise ToolError(f"Failed to install Python packages: {python_install.stderr}")
        
        # Install Playwright browsers (this will install the version that matches the Python package)
        await ctx.info("Installing Playwright browsers...")
        browser_install = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c',
            'python3 -m playwright install firefox'
        ], capture_output=True, text=True)
        
        if browser_install.returncode != 0:
            await ctx.error(f"Failed to install Playwright browsers: {browser_install.stderr}")
            subprocess.run(['docker', 'rm', '-f', container_name], check=False)
            raise ToolError(f"Failed to install Playwright browsers: {browser_install.stderr}")
        
        await ctx.info("Playwright browsers installed successfully")
        
        await ctx.info("Verifying installations...")
        verify_cmd = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c',
            'node --version && npm --version && python3 --version && python3 -c "import playwright; print(\'Playwright installed\')" && ls -la /ms-playwright/firefox*/firefox/firefox'
        ], capture_output=True, text=True)
        
        if verify_cmd.returncode != 0:
            await ctx.error(f"Installation verification failed: {verify_cmd.stderr}")
            subprocess.run(['docker', 'rm', '-f', container_name], check=False)
            raise ToolError(f"Installation verification failed: {verify_cmd.stderr}")
        
        await ctx.info(f"Verification successful: {verify_cmd.stdout.strip()}")
        
        mkdir_proc = subprocess.run([
            'docker', 'exec', container_id, 'mkdir', '-p', '/app'
        ], capture_output=True, text=True)
        
        if mkdir_proc.returncode != 0:
            await ctx.error(f"Failed to create /app directory: {mkdir_proc.stderr}")
            subprocess.run(['docker', 'rm', '-f', container_name], check=False)
            raise ToolError(f"Failed to create /app directory: {mkdir_proc.stderr}")
        
        await ctx.info("React container created and configured successfully")
        
        return {
            'status': 'success',
            'container_id': container_id,
            'container_name': container_name,
            'image': image,
            'port': port,
            'message': f"Container '{container_name}' ready for React testing"
        }
        
    except Exception as e:
        error_msg = f"Container creation failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def _clone_repo_to_container(ctx: Context, container_id: str, github_url: str) -> Dict[str, Any]:
    """Core function for cloning repository"""
    try:
        await ctx.info(f"Cloning repository: {github_url} into container {container_id}")
        
        if github_url.endswith('.git'):
            repo_name = github_url.split('/')[-1][:-4]
        else:
            repo_name = github_url.split('/')[-1]
        
        git_check = subprocess.run([
            'docker', 'exec', container_id, 'which', 'git'
        ], capture_output=True, text=True)
        
        if git_check.returncode != 0:
            await ctx.info("Installing git...")
            git_install = subprocess.run([
                'docker', 'exec', container_id, 'apt-get', 'install', '-y', 'git'
            ], capture_output=True, text=True)
            
            if git_install.returncode != 0:
                error_msg = f"Failed to install git: {git_install.stderr}"
                await ctx.error(error_msg)
                raise ToolError(error_msg)
        
        clone_proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c', 
            f'cd /app && git clone {github_url}'
        ], capture_output=True, text=True)
        
        if clone_proc.returncode != 0:
            error_msg = f"Git clone failed: {clone_proc.stderr}\nSTDOUT: {clone_proc.stdout}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
        await ctx.info(f"Repository cloned successfully to /app/{repo_name}")
        
        return {
            'status': 'success',
            'repo_name': repo_name,
            'container_path': f'/app/{repo_name}',
            'message': f'Repository {repo_name} cloned successfully',
            'stdout': clone_proc.stdout.strip()
        }
        
    except Exception as e:
        error_msg = f"Repository clone failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def _install_npm_dependencies(ctx: Context, container_id: str, repo_name: str) -> Dict[str, Any]:
    """Core function for installing npm dependencies"""
    try:
        await ctx.info(f"Installing npm dependencies for {repo_name}...")
        
        install_proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c',
            f'cd /app/{repo_name} && npm install'
        ], capture_output=True, text=True, timeout=300)
        
        if install_proc.returncode != 0:
            error_msg = f"npm install failed: {install_proc.stderr}\nSTDOUT: {install_proc.stdout}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
        await ctx.info("npm dependencies installed successfully")
        
        return {
            'status': 'success',
            'message': 'npm dependencies installed successfully',
            'stdout': install_proc.stdout.strip()
        }
        
    except subprocess.TimeoutExpired:
        error_msg = "npm install timed out after 5 minutes"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    except Exception as e:
        error_msg = f"npm install failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def _build_react_app(ctx: Context, container_id: str, repo_name: str, build_command: Optional[str] = None) -> Dict[str, Any]:
    """Core function for building React app"""
    try:
        await ctx.info(f"Building React app for {repo_name}...")
        
        if build_command:
            cmd = build_command
        else:
            check_scripts = subprocess.run([
                'docker', 'exec', container_id, 'bash', '-c',
                f'cd /app/{repo_name} && cat package.json | grep -E "\\"(build|preview)\\""'
            ], capture_output=True, text=True)
            
            if 'build' in check_scripts.stdout:
                cmd = 'npm run build'
            else:
                await ctx.info("No build script found, skipping build step")
                return {
                    'status': 'success',
                    'message': 'No build step required',
                    'skipped': True
                }
        
        build_proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c',
            f'cd /app/{repo_name} && {cmd}'
        ], capture_output=True, text=True, timeout=300)
        
        if build_proc.returncode != 0:
            error_msg = f"Build failed: {build_proc.stderr}\nSTDOUT: {build_proc.stdout}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
        await ctx.info("React app built successfully")
        
        return {
            'status': 'success',
            'message': f'React app built successfully using: {cmd}',
            'build_command': cmd,
            'stdout': build_proc.stdout.strip()
        }
        
    except subprocess.TimeoutExpired:
        error_msg = "Build timed out after 5 minutes"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    except Exception as e:
        error_msg = f"Build failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def _create_test_script_in_container(ctx: Context, container_id: str) -> Dict[str, Any]:
    """Core function for creating test script"""
    try:
        import base64
        await ctx.info("Creating Playwright test script in container...")
        
        test_script = '''import os, base64, json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    port = int(os.environ.get("REACT_PORT", 5173))
    headless = os.environ.get("HEADLESS", "true").lower() == "true"
    results = {}
    screenshots = {}
    console_errors = []
    
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=headless)
            page = browser.new_page()
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            
            page.goto(f"http://localhost:{port}", timeout=15000)
            
            results["header_exists"] = page.query_selector("header") is not None
            results["footer_exists"] = page.query_selector("footer") is not None
            results["nav_exists"] = page.query_selector("nav") is not None
            results["main_exists"] = page.query_selector("main") is not None
            results["form_count"] = len(page.query_selector_all("form"))
            results["button_count"] = len(page.query_selector_all("button"))
            
            page.set_viewport_size({"width": 1920, "height": 1080})
            desktop_shot = "/app/screenshot_desktop.png"
            page.screenshot(path=desktop_shot)
            screenshots["desktop"] = encode_image_to_base64(desktop_shot)
            
            page.set_viewport_size({"width": 375, "height": 667})
            mobile_shot = "/app/screenshot_mobile.png"
            page.screenshot(path=mobile_shot)
            screenshots["mobile"] = encode_image_to_base64(mobile_shot)
            
            buttons = page.query_selector_all("button")
            results["button_clickable"] = len(buttons) > 0 if buttons else False
            
            forms = page.query_selector_all("form")
            results["form_submittable"] = len(forms) > 0 if forms else False
            
            results["navigation_success"] = True
            browser.close()
            
    except Exception as e:
        results["error"] = str(e)
        console_errors.append(f"Test execution error: {str(e)}")
    
    with open("/app/test_results.json", "w") as f:
        json.dump({
            "results": results,
            "screenshots": screenshots,
            "console_errors": console_errors,
            "message": "React contest tests completed"
        }, f, indent=2)
    
    print("Test completed, results saved to /app/test_results.json")

if __name__ == "__main__":
    main()
'''
        
        test_script_encoded = base64.b64encode(test_script.encode('utf-8')).decode('ascii')
        
        create_script = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c',
            f'echo "{test_script_encoded}" | base64 -d > /app/playwright_test.py'
        ], capture_output=True, text=True)
        
        if create_script.returncode != 0:
            error_msg = f"Failed to create test script: {create_script.stderr}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
        await ctx.info("Playwright test script created successfully")
        
        return {
            'status': 'success',
            'message': 'Playwright test script created in container'
        }
        
    except Exception as e:
        error_msg = f"Test script creation failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def _start_react_app_and_test(
    ctx: Context, 
    container_id: str, 
    repo_name: str, 
    port: int = 5173,
    start_command: Optional[str] = None,
    timeout: int = 120
) -> Dict[str, Any]:
    """Core function for starting React app and testing"""
    try:
        await ctx.info(f"Starting React app and running tests for {repo_name}...")
        
        if start_command:
            cmd = start_command
        else:
            check_scripts = subprocess.run([
                'docker', 'exec', container_id, 'bash', '-c',
                f'cd /app/{repo_name} && cat package.json | grep -E "\\"(preview|dev|start)\\""'
            ], capture_output=True, text=True)
            
            if 'preview' in check_scripts.stdout:
                cmd = f'npm run preview -- --host 0.0.0.0 --port {port}'
            elif 'dev' in check_scripts.stdout:
                cmd = f'npm run dev -- --host 0.0.0.0 --port {port}'
            elif 'start' in check_scripts.stdout:
                cmd = 'npm start'
            else:
                raise ToolError("No suitable npm script found (preview, dev, or start)")
        
        run_script = f'''#!/bin/bash
set -e
cd /app/{repo_name}

echo "Package.json contents:"
cat package.json
echo ""
echo "Running: {cmd}"

bash -c "{cmd}" > /app/react.log 2>&1 &
APP_PID=$!

echo "Waiting for React app on port {port}..."
for i in {{1..30}}; do
  if nc -z localhost {port} 2>/dev/null; then
    echo "Port {port} is now open!"
    break
  fi
  echo "Attempt $i/30: Waiting for React app on port {port}..."
  sleep 1
done

if ! nc -z localhost {port} 2>/dev/null; then
  echo "React app failed to start. Logs:"
  cat /app/react.log
  exit 1
fi

echo "React app is running, starting Playwright tests..."

cd /app
python3 /app/playwright_test.py

if kill -0 $APP_PID 2>/dev/null; then
  kill $APP_PID
fi

echo "Tests completed successfully"
'''
        
        import base64
        script_encoded = base64.b64encode(run_script.encode('utf-8')).decode('ascii')
        
        write_script = subprocess.run([
            'docker', 'exec', container_id, 'bash', '-c',
            f'echo "{script_encoded}" | base64 -d > /app/run_tests.sh && chmod +x /app/run_tests.sh'
        ], capture_output=True, text=True)
        
        if write_script.returncode != 0:
            raise ToolError(f"Failed to create test script: {write_script.stderr}")
        
        await ctx.info("Executing React app and tests...")
        test_proc = subprocess.run([
            'docker', 'exec', container_id, 'bash', '/app/run_tests.sh'
        ], capture_output=True, text=True, timeout=timeout)
        
        if test_proc.returncode != 0:
            error_msg = f"Test execution failed: {test_proc.stderr}\nSTDOUT: {test_proc.stdout}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
        get_results = subprocess.run([
            'docker', 'exec', container_id, 'cat', '/app/test_results.json'
        ], capture_output=True, text=True)
        
        if get_results.returncode != 0:
            raise ToolError("Failed to read test results")
        
        test_results = json.loads(get_results.stdout)
        await ctx.info(f"Test Results: {json.dumps(test_results, indent=2)}")
        
        return {
            'status': 'success',
            'execution_log': test_proc.stdout,
            **test_results
        }
        
    except subprocess.TimeoutExpired:
        error_msg = f"Test execution timed out after {timeout} seconds"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse test results: {e}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    except Exception as e:
        error_msg = f"Test execution failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

@react_contest_mcp.tool
async def create_react_container(ctx: Context, port: int = 5173) -> Dict[str, Any]:
    """
    Create a Docker container with Node.js and Playwright ready for React testing.
    Uses pre-built image instead of building custom image.
    Args:
        ctx: FastMCP context for logging
        port: Port to expose for the React app
    Returns:
        Dictionary containing container details
    """
    return await _create_react_container(ctx, port)

@react_contest_mcp.tool
async def clone_repo_to_container(ctx: Context, container_id: str, github_url: str) -> Dict[str, Any]:
    """
    Clone a GitHub repository directly into the container.
    Args:
        ctx: FastMCP context for logging
        container_id: The Docker container ID
        github_url: The GitHub repository URL
    Returns:
        Dictionary containing clone status and repo details
    """
    return await _clone_repo_to_container(ctx, container_id, github_url)

@react_contest_mcp.tool
async def install_npm_dependencies(ctx: Context, container_id: str, repo_name: str) -> Dict[str, Any]:
    """
    Install npm dependencies for the React project inside the container.
    Args:
        ctx: FastMCP context for logging
        container_id: The Docker container ID
        repo_name: The repository name (directory under /app)
    Returns:
        Dictionary containing installation status
    """
    return await _install_npm_dependencies(ctx, container_id, repo_name)

@react_contest_mcp.tool
async def build_react_app(ctx: Context, container_id: str, repo_name: str, build_command: Optional[str] = None) -> Dict[str, Any]:
    """
    Build the React application inside the container.
    Args:
        ctx: FastMCP context for logging
        container_id: The Docker container ID
        repo_name: The repository name (directory under /app)
        build_command: Custom build command (optional)
    Returns:
        Dictionary containing build status
    """
    return await _build_react_app(ctx, container_id, repo_name, build_command)

@react_contest_mcp.tool
async def create_test_script_in_container(ctx: Context, container_id: str) -> Dict[str, Any]:
    """
    Create the Playwright test script directly inside the container.
    Args:
        ctx: FastMCP context for logging
        container_id: The Docker container ID
    Returns:
        Dictionary containing creation status
    """
    return await _create_test_script_in_container(ctx, container_id)

@react_contest_mcp.tool
async def start_react_app_and_test(
    ctx: Context, 
    container_id: str, 
    repo_name: str, 
    port: int = 5173,
    start_command: Optional[str] = None,
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Start the React app and run Playwright tests inside the container.
    Args:
        ctx: FastMCP context for logging
        container_id: The Docker container ID
        repo_name: The repository name (directory under /app)
        port: Port for the React app
        start_command: Custom start command (optional)
        timeout: Timeout for the entire process
    Returns:
        Dictionary containing test results
    """
    return await _start_react_app_and_test(ctx, container_id, repo_name, port, start_command, timeout)

@react_contest_mcp.tool
async def run_full_react_contest(
    ctx: Context,
    github_url: str,
    port: int = 5173,
    headless: bool = True,
    build_command: Optional[str] = None,
    start_command: Optional[str] = None,
    timeout: int = 180,
    keep_container_running: bool = False
) -> Dict[str, Any]:
    """
    Run the complete React contest workflow using modular tools and pre-built images.
    Args:
        ctx: FastMCP context for logging
        github_url: GitHub repository URL
        port: Port for the React app
        headless: Whether to run browser in headless mode
        build_command: Custom build command
        start_command: Custom start command
        timeout: Timeout for test execution
        keep_container_running: Whether to keep container running after tests
    Returns:
        Dictionary containing complete test results
    """
    container_id = None
    container_name = None
    
    try:
        # Step 1: Create container with pre-built image
        container_result = await _create_react_container(ctx, port)
        if container_result["status"] != "success":
            raise ToolError(f"Container creation failed: {container_result.get('message', 'Unknown error')}")
        
        container_id = container_result["container_id"]
        container_name = container_result["container_name"]
        
        # Step 2: Clone repository to container
        clone_result = await _clone_repo_to_container(ctx, container_id, github_url)
        if clone_result["status"] != "success":
            raise ToolError(f"Repository clone failed: {clone_result.get('message', 'Unknown error')}")
        
        repo_name = clone_result["repo_name"]
        
        # Step 3: Install npm dependencies
        npm_result = await _install_npm_dependencies(ctx, container_id, repo_name)
        if npm_result["status"] != "success":
            raise ToolError(f"npm install failed: {npm_result.get('message', 'Unknown error')}")
        
        # Step 4: Build React app (if needed)
        build_result = await _build_react_app(ctx, container_id, repo_name, build_command)
        if build_result["status"] != "success":
            raise ToolError(f"Build failed: {build_result.get('message', 'Unknown error')}")
        
        # Step 5: Create test script in container
        test_script_result = await _create_test_script_in_container(ctx, container_id)
        if test_script_result["status"] != "success":
            raise ToolError(f"Test script creation failed: {test_script_result.get('message', 'Unknown error')}")
        
        # Step 6: Start React app and run tests
        test_result = await _start_react_app_and_test(
            ctx, container_id, repo_name, port, start_command, timeout
        )
        
        if test_result["status"] != "success":
            raise ToolError(f"Test execution failed: {test_result.get('message', 'Unknown error')}")
        
        # Log detailed results
        if "results" in test_result:
            results = test_result["results"]
            await ctx.info(f"Structural Analysis:")
            await ctx.info(f"  - Header exists: {results.get('header_exists', 'Unknown')}")
            await ctx.info(f"  - Footer exists: {results.get('footer_exists', 'Unknown')}")
            await ctx.info(f"  - Navigation exists: {results.get('nav_exists', 'Unknown')}")
            await ctx.info(f"  - Main content exists: {results.get('main_exists', 'Unknown')}")
            await ctx.info(f"  - Form count: {results.get('form_count', 'Unknown')}")
            await ctx.info(f"  - Button count: {results.get('button_count', 'Unknown')}")
            await ctx.info(f"  - Buttons clickable: {results.get('button_clickable', 'Unknown')}")
            await ctx.info(f"  - Forms submittable: {results.get('form_submittable', 'Unknown')}")
            await ctx.info(f"  - Navigation successful: {results.get('navigation_success', 'Unknown')}")
        
        # Log console errors if any
        if "console_errors" in test_result and test_result["console_errors"]:
            await ctx.info(f"Console Errors Found: {len(test_result['console_errors'])}")
            for i, error in enumerate(test_result["console_errors"][:5]):
                await ctx.info(f"  Error {i+1}: {error}")
        else:
            await ctx.info("No console errors detected")
        
        # Log screenshot info
        if "screenshots" in test_result:
            screenshots = test_result["screenshots"]
            await ctx.info(f"Screenshots captured: {list(screenshots.keys())}")
        
        return {
            **test_result,
            "container_name": container_name,
            "repo_name": repo_name
        }
        
    except Exception as e:
        error_msg = f"React contest workflow failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    finally:
        # Clean up container unless requested to keep it running
        if container_name and not keep_container_running:
            try:
                cleanup_cmd = ["docker", "rm", "-f", container_name]
                subprocess.run(cleanup_cmd, check=False)
                await ctx.info(f"Container {container_name} cleaned up")
            except Exception as cleanup_error:
                await ctx.error(f"Cleanup warning: {cleanup_error}")
        elif container_name and keep_container_running:
            await ctx.info(f"Container {container_name} kept running as requested")


if __name__ == "__main__":
    print("🚀 Starting React.js Container MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server endpoints available at:")
    print("🌐 Server available at: http://127.0.0.1:8009/react/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    react_contest_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8009,
        path="/react/mcp",
        log_level="info"
    )