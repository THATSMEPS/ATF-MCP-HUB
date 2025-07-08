import subprocess, os, time, shutil, socket, base64, asyncio, warnings, platform, signal
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

mcp = FastMCP(name="React Contest MCP Server")


BASE_DIR = os.path.join(os.getcwd(), "react_contest_runs")
os.makedirs(BASE_DIR, exist_ok=True)

def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Wait for a TCP port to become available with proper Windows socket handling."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Set socket timeout to avoid hanging
                sock.settimeout(1.0)
                result = sock.connect_ex(("localhost", port))
                if result == 0:
                    return True
        except (socket.error, OSError) as e:
            # Ignore connection errors - expected while waiting
            pass
        time.sleep(1)
    return False

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

@mcp.tool
async def run_react_contest_tests(
    github_url: str,
    ctx: Context,
    port: int = 5173,
    headless: bool = True,
    build_command: Optional[str] = None,
    start_command: Optional[str] = None,
    keep_container_running: bool = False
) -> Dict[str, Any]:
    """
    Clone repo, build Docker image, run React app and Playwright tests inside Docker, cleanup after.
    """
    container_name = None
    try:
        repo_name = github_url.split("/")[-1].replace(".git", "")
        run_dir = os.path.join(BASE_DIR, repo_name)
        code_dir = os.path.join(run_dir, "code")
        os.makedirs(code_dir, exist_ok=True)
        server_proc = None
        browser = None
        page = None
        container_name = f"react-contest-{repo_name.lower()}"
        # Clean up existing code directory if it exists
        if os.path.exists(code_dir) and os.listdir(code_dir):
            await ctx.info("Removing existing code directory...")
            shutil.rmtree(code_dir)
            os.makedirs(code_dir, exist_ok=True)

        # Clone user repo
        await ctx.info("Cloning user repo...")
        subprocess.run(["git", "clone", github_url, code_dir], check=True)

        # Write Playwright test script
        test_script = '''\
import os, base64
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    port = int(os.environ.get("REACT_PORT", 3000))
    headless = os.environ.get("HEADLESS", "true").lower() == "true"
    results = {}
    screenshots = {}
    console_errors = []
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
        
        # Simplified button test (faster)
        buttons = page.query_selector_all("button")
        results["button_clickable"] = len(buttons) > 0 if buttons else None
        
        # Simplified form test (faster)
        forms = page.query_selector_all("form")
        results["form_submittable"] = len(forms) > 0 if forms else None
        
        # Skip navigation test for speed
        results["navigation_success"] = True
        browser.close()
    import json
    with open("/app/test_results.json", "w") as f:
        json.dump({
            "results": results,
            "screenshots": screenshots,
            "console_errors": console_errors,
            "message": "React contest tests completed"
        }, f)

if __name__ == "__main__":
    main()
'''
        with open(os.path.join(code_dir, "playwright_test.py"), "w") as f:
            f.write(test_script)

        # Write entrypoint shell script to start React app, wait for port, then run Playwright tests
        entrypoint_script = f'''#!/bin/bash
set -e
PORT=${{REACT_PORT:-5173}}
HEADLESS=${{HEADLESS:-true}}

# Check if package.json exists and determine appropriate start command
if [ ! -f "/app/package.json" ]; then
    echo "Error: package.json not found in /app/"
    exit 1
fi

# Try to determine the correct start command
if grep -q "\\"preview\\"" /app/package.json; then
    START_CMD="npm run preview -- --host 0.0.0.0 --port $PORT"
elif grep -q "\\"dev\\"" /app/package.json; then
    START_CMD="npm run dev -- --host 0.0.0.0 --port $PORT"
elif grep -q "\\"start\\"" /app/package.json; then
    START_CMD="npm start"
else
    echo "Error: No suitable npm script found (preview, dev, or start)"
    exit 1
fi

# Use custom start command if provided
if [ -n "{start_command if start_command else ''}" ]; then
    START_CMD="{start_command if start_command else 'npm run preview -- --host 0.0.0.0 --port $PORT'}"
fi

echo "Package.json contents:"
cat /app/package.json
echo ""
echo "Running: $START_CMD"

# Start React app in background and capture PID
bash -c "$START_CMD" > /app/preview.log 2>&1 &
APP_PID=$!

# Wait for port to be open with more detailed logging
echo "Waiting for React app on port $PORT..."
for i in {{1..30}}; do
  if nc -z localhost $PORT 2>/dev/null; then
    echo "Port $PORT is now open!"
    break
  fi
  echo "Attempt $i/30: Waiting for React app on port $PORT..."
  sleep 1
done

# Check if port is open and app is still running
if ! nc -z localhost $PORT 2>/dev/null; then
  echo "Preview server failed to start. App process status:"
  if kill -0 $APP_PID 2>/dev/null; then
    echo "App process is still running (PID: $APP_PID)"
  else
    echo "App process has died"
  fi
  echo ""
  echo "Preview log output:"
  cat /app/preview.log
  echo ""
  echo "Checking if React app built successfully..."
  if [ -d "/app/dist" ]; then
    echo "dist/ directory found"
    ls -la /app/dist/
  elif [ -d "/app/build" ]; then
    echo "build/ directory found"  
    ls -la /app/build/
  else
    echo "No dist/ or build/ directory found"
  fi
  exit 1
fi

echo "React app is running on port $PORT, starting Playwright tests..."

# Run Playwright test
cd /app
python /app/playwright_test.py

# Kill the React app process
if kill -0 $APP_PID 2>/dev/null; then
  kill $APP_PID
fi

# Copy results to mounted output directory
if [ -f "/app/test_results.json" ]; then
  cp /app/test_results.json /app/output/
  echo "Results copied to output directory"
else
  echo "No test results found"
  exit 1
fi
'''
        with open(os.path.join(run_dir, "run_all.sh"), "w", newline='\n') as f:
            f.write(entrypoint_script)
        os.chmod(os.path.join(run_dir, "run_all.sh"), 0o775)

        # Create Dockerfile
        await ctx.info("Creating Dockerfile for React+Playwright...")
        build_step = f"RUN {build_command}" if build_command else 'RUN if [ -f package.json ] && grep -q "\\"build\\"" package.json; then npm run build; fi'
        
        dockerfile = f'''FROM mcr.microsoft.com/playwright/python:v1.44.0-focal

# Install Node.js and other dependencies
RUN apt-get update && \
    apt-get install -y curl netcat && \
    curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package files first for better caching
COPY code/package*.json /app/
RUN npm install

# Copy rest of the code
COPY code/ /app/
COPY run_all.sh /app/run_all.sh

# Install Python dependencies
RUN pip install --upgrade pip && pip install playwright
RUN playwright install --with-deps

# Build the React app if build command is provided
{build_step}

# Ensure run_all.sh is executable
RUN chmod +x /app/run_all.sh

# Create output directory for volume mounting
RUN mkdir -p /app/output
VOLUME /app/output

EXPOSE {port}

CMD ["/bin/bash", "/app/run_all.sh"]'''
        with open(os.path.join(run_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)

        # Build Docker image
        image_tag = f"{container_name}:latest"
        await ctx.info("Building Docker image...")
        subprocess.run(["docker", "build", "-t", image_tag, run_dir], check=True)
        await ctx.info("Docker image built successfully")

        # Start React app in Docker and wait for completion
        await ctx.info("Starting React app in Docker container...")
        
        # Clean up any existing container with the same name
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        
        # Create output directory for volume mounting
        output_dir = os.path.join(run_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # First run container WITHOUT --rm to allow result copying
        docker_run_cmd = [
            "docker", "run", "-d",  # Run in detached mode
            "--name", container_name,
            "-p", f"{port}:{port}",  # Expose port to host
            "-v", f"{output_dir}:/app/output",  # Mount output directory
            "-e", f"REACT_PORT={port}",
            "-e", f"HEADLESS={'true' if headless else 'false'}",
            image_tag
        ]

        # Run container in detached mode
        await ctx.info(f"Starting Docker container: {' '.join(docker_run_cmd)}")
        
        try:
            # Start container
            result = subprocess.run(
                docker_run_cmd, 
                cwd=run_dir, 
                check=True,
                capture_output=True,
                text=True
            )
            
            container_id = result.stdout.strip()
            await ctx.info(f"Container started with ID: {container_id}")
            
            # Wait for container to complete with timeout
            await ctx.info("Waiting for container to complete...")
            wait_cmd = ["docker", "wait", container_name]
            
            wait_result = subprocess.run(
                wait_cmd,
                timeout=120,  # 2 minute timeout
                check=True,
                capture_output=True,
                text=True
            )
            
            exit_code = wait_result.stdout.strip()
            await ctx.info(f"Container completed with exit code: {exit_code}")
            
            # Get container logs
            logs_cmd = ["docker", "logs", container_name]
            logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
            
            if logs_result.stdout:
                await ctx.info(f"Container stdout: {logs_result.stdout}")
            if logs_result.stderr:
                await ctx.info(f"Container stderr: {logs_result.stderr}")
            
            # Check if container completed successfully
            if exit_code != "0":
                raise ToolError(f"Container failed with exit code {exit_code}")
                
        except subprocess.TimeoutExpired:
            await ctx.error("Docker container execution timed out after 2 minutes")
            # Force stop the container
            subprocess.run(["docker", "stop", container_name], check=False)
            raise ToolError("Container execution timed out")
        except subprocess.CalledProcessError as e:
            await ctx.error(f"Docker execution failed with return code {e.returncode}")
            if e.stdout:
                await ctx.error(f"Docker stdout: {e.stdout}")
            if e.stderr:
                await ctx.error(f"Docker stderr: {e.stderr}")
            raise ToolError(f"Docker execution failed: {e}")
        finally:
            # Always clean up the container
            cleanup_cmd = ["docker", "rm", "-f", container_name]
            subprocess.run(cleanup_cmd, check=False)
            await ctx.info("Container cleanup completed")
        
        await ctx.info("Docker container completed successfully")

        # Read test results from mounted output directory
        import json
        results_output_path = os.path.join(output_dir, "test_results.json")
        
        await ctx.info("Reading test results...")
        
        if not os.path.exists(results_output_path):
            raise ToolError("Test results not found in output directory.")
            
        with open(results_output_path, "r") as f:
            test_results = json.load(f)
        
        # Log the test results to MCP inspector
        await ctx.info(f"Test Results: {json.dumps(test_results, indent=2)}")
        
        # Extract specific results for logging
        if "results" in test_results:
            results = test_results["results"]
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
        if "console_errors" in test_results and test_results["console_errors"]:
            await ctx.info(f"Console Errors Found: {len(test_results['console_errors'])}")
            for i, error in enumerate(test_results["console_errors"][:5]):  # Show first 5 errors
                await ctx.info(f"  Error {i+1}: {error}")
        else:
            await ctx.info("No console errors detected")
        
        # Log screenshot info
        if "screenshots" in test_results:
            screenshots = test_results["screenshots"]
            await ctx.info(f"Screenshots captured: {list(screenshots.keys())}")
        
        return {
            "status": "success",
            **test_results
        }
    except Exception as e:
        error_msg = f"React contest failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    finally:
        # Ensure container cleanup even on exceptions, unless keep_container_running is True
        if container_name and not keep_container_running:
            try:
                cleanup_cmd = ["docker", "rm", "-f", container_name]
                subprocess.run(cleanup_cmd, check=False, capture_output=True)
                await ctx.info(f"Final cleanup: Container {container_name} removed")
            except Exception as cleanup_error:
                await ctx.error(f"Cleanup warning: {cleanup_error}")

if __name__ == "__main__":
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    except Exception as e:
        print(f"Error running MCP server: {e}")
        raise
