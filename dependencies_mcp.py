import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import requests


dependencies_mcp = FastMCP(name="Dependencies Installation Server")

@dependencies_mcp.tool
async def install_dependencies_python(cloned_path: str, ctx: Context) -> Dict[str, Any]:
    """
    Install Python dependencies for a cloned repository.
    
    Args:
        cloned_path: The local path to the cloned repository
    
    Returns:
        Dictionary containing installation status and details
    """
    # Log the start of the operation
    await ctx.info(f"Starting to install Python dependencies in: {cloned_path}")
    
    if not os.path.exists(cloned_path):
        raise ToolError(f"Path does not exist: {cloned_path}")
    
    try:
        # Change to the cloned repository directory
        os.chdir(cloned_path)
        await ctx.info(f"Changed working directory to: {cloned_path}")
        
        # Report initial progress
        await ctx.report_progress(progress=0, total=100)
        
        # Check for requirements.txt
        if os.path.exists('requirements.txt'):
            await ctx.info("Found requirements.txt, installing dependencies...")
            process = subprocess.run(
                ['pip', 'install', '-r', 'requirements.txt'],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if process.returncode != 0:
                error_msg = f"Pip install failed: {process.stderr}"
                await ctx.error(error_msg)
                raise ToolError(error_msg)
            
            await ctx.report_progress(progress=50, total=100)
        
        # Check for pyproject.toml
        if os.path.exists('pyproject.toml'):
            await ctx.info("Found pyproject.toml, installing with pip...")
            process = subprocess.run(
                ['pip', 'install', '-e', '.'],
                check=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            if process.returncode != 0:
                error_msg = f"Package installation failed: {process.stderr}"
                await ctx.error(error_msg)
                raise ToolError(error_msg)
            
            await ctx.report_progress(progress=100, total=100)
        
        if not os.path.exists('requirements.txt') and not os.path.exists('pyproject.toml'):
            await ctx.warning("No requirements.txt or pyproject.toml found")
            return {
                'status': 'warning',
                'message': 'No dependency files found',
                'path': cloned_path
            }
        
        await ctx.info("Successfully installed all Python dependencies")
        return {
            'status': 'success',
            'message': 'Python dependencies installed successfully',
            'path': cloned_path
        }
        
    except subprocess.TimeoutExpired:
        error_msg = "Dependency installation timed out (5 minutes)"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error during dependency installation: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

@dependencies_mcp.tool
async def install_dependencies_node(cloned_path: str, ctx: Context, package_manager: Optional[str] = "npm") -> Dict[str, Any]:
    """
    Install Node.js dependencies for a cloned repository.
    
    Args:
        cloned_path: The local path to the cloned repository
        package_manager: The package manager to use ('npm' or 'yarn'). Defaults to 'npm'
    
    Returns:
        Dictionary containing installation status and details
    """
    # Log the start of the operation
    await ctx.info(f"Starting to install Node.js dependencies in: {cloned_path}")
    
    if not os.path.exists(cloned_path):
        raise ToolError(f"Path does not exist: {cloned_path}")
        
    if package_manager not in ["npm", "yarn"]:
        raise ToolError(f"Invalid package manager. Must be 'npm' or 'yarn'")
    
    try:
        # Change to the cloned repository directory
        os.chdir(cloned_path)
        await ctx.info(f"Changed working directory to: {cloned_path}")
        
        # Report initial progress
        await ctx.report_progress(progress=0, total=100)
        
        # Check for package.json
        if not os.path.exists('package.json'):
            await ctx.warning("No package.json found")
            return {
                'status': 'warning',
                'message': 'No package.json found',
                'path': cloned_path
            }
            
        # Install dependencies based on package manager
        if package_manager == "npm":
            install_cmd = ['npm', 'install']
        else:
            install_cmd = ['yarn', 'install']
            
        await ctx.info(f"Installing dependencies using {package_manager}...")
        process = subprocess.run(
            install_cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if process.returncode != 0:
            error_msg = f"{package_manager} install failed: {process.stderr}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
        # Report progress after successful installation
        await ctx.report_progress(progress=100, total=100)
        
        # Check for Express.js specific dependencies
        with open('package.json', 'r') as f:
            import json
            package_data = json.load(f)
            dependencies = package_data.get('dependencies', {})
            if 'express' in dependencies:
                await ctx.info("Express.js project detected")
        
        await ctx.info("Successfully installed all Node.js dependencies")
        return {
            'status': 'success',
            'message': 'Node.js dependencies installed successfully',
            'path': cloned_path,
            'package_manager': package_manager
        }
        
    except subprocess.TimeoutExpired:
        error_msg = "Dependency installation timed out (5 minutes)"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error during dependency installation: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

if __name__ == "__main__":
    print("🚀 Starting Dependencies Installation MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server will be available at: http://127.0.0.1:8001/dependencies/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    dependencies_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
        path="/dependencies/mcp",
        log_level="info"
    )