import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, Any
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import requests

# Create the FastMCP server
git_clone_mcp = FastMCP(name="GitHub Clone Server")

@git_clone_mcp.tool
async def github_clone_repo(github_url: str, ctx: Context) -> Dict[str, Any]:
    """
    Clone a GitHub repository to a temporary directory.
    
    Args:
        github_url: The GitHub repository URL (e.g., https://github.com/user/repo.git)
    
    Returns:
        Dictionary containing clone status, local path, and repository information
    """
    
    # Log the start of the operation
    await ctx.info(f"Starting to clone repository: {github_url}")
    
    # Validate the GitHub URL
    if not github_url.startswith(('https://github.com/', 'git@github.com:')):
        raise ToolError("Invalid GitHub URL. Must start with 'https://github.com/' or 'git@github.com:'")
    
    
    try:
        # Extract repository name from URL
        if github_url.endswith('.git'):
            repo_name = github_url.split('/')[-1][:-4]  # Remove .git extension
        else:
            repo_name = github_url.split('/')[-1]
        
        clone_path = os.path.join("/Volumes/MY  DISK/ATF/test_atf", repo_name)
        clone_path = Path("/Volumes/MY  DISK/ATF/test_atf") / repo_name
        
        await ctx.info(f"Cloning to temporary directory: {clone_path}")
        
        # Report initial progress
        await ctx.report_progress(progress=0, total=100)
        
        # git clone command
        process = subprocess.run(
            ['git', 'clone', github_url],
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Report progress after clone attempt
        await ctx.report_progress(progress=80, total=100)
        
        if process.returncode != 0:
            # Clean up on failure
            shutil.rmtree(clone_path, ignore_errors=True)
            error_msg = f"Git clone failed: {process.stderr}"
            await ctx.error(error_msg)
            raise ToolError(error_msg)
        
       
        
        # Report completion
        await ctx.report_progress(progress=100, total=100)
        await ctx.info(f"Successfully cloned repository to {clone_path}")
        
        return {
            'status': 'success',
            'message': 'Repository cloned successfully',
            'local_path': str(clone_path)
        }
        
    except subprocess.TimeoutExpired:
       # Clean up on timeout - use clone_path, not temp_dir
       if 'clone_path' in locals() and os.path.exists(clone_path):
        shutil.rmtree(clone_path, ignore_errors=True)
        error_msg = "Git clone operation timed out (5 minutes)"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
        
    except Exception as e:
       # Clean up on any other error - use clone_path, not temp_dir
        if 'clone_path' in locals() and os.path.exists(clone_path):
            shutil.rmtree(clone_path, ignore_errors=True)
        error_msg = f"Unexpected error during clone: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

@git_clone_mcp.tool
async def cleanup_clone(local_path: str, ctx: Context) -> Dict[str, Any]:
    """
    Clean up a cloned repository directory.
    
    Args:
        local_path: The local path to the cloned repository
    
    Returns:
        Dictionary containing cleanup status
    """
    await ctx.info(f"Cleaning up directory: {local_path}")
    
    try:
        if os.path.exists(local_path):
            temp_dir = str(Path(local_path))
            shutil.rmtree(temp_dir, ignore_errors=True)
            await ctx.info(f"Successfully cleaned up {temp_dir}")
            return {
                'status': 'success',
                'message': f'Cleaned up directory: {temp_dir}',
                'path': temp_dir
            }
        else:
            await ctx.warning(f"Directory does not exist: {local_path}")
            return {
                'status': 'warning',
                'message': f'Directory does not exist: {local_path}',
                'path': local_path
            }
    except Exception as e:
        error_msg = f"Error cleaning up directory: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)


if __name__ == "__main__":
    print("🚀 Starting GitHub Clone MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server will be available at: http://127.0.0.1:8004/git_clone/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    git_clone_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8004,
        path="/git_clone/mcp",
        log_level="info"
    )