# image_processing_mcp.py
import subprocess, os, time, shutil, base64
from typing import Dict, Any, List
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

image_processing_mcp = FastMCP(name="Image Processing MCP Server")

BASE_DIR = os.path.join(os.getcwd(), "image_contest_runs")
os.makedirs(BASE_DIR, exist_ok=True)

def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_info(image_path: str) -> Dict[str, Any]:
    """Get image information including base64 encoding"""
    try:
        file_size = os.path.getsize(image_path)
        file_ext = os.path.splitext(image_path)[1].lower()
        
        # Only encode if file is reasonably small (< 5MB)
        if file_size < 5 * 1024 * 1024:
            base64_data = encode_image_to_base64(image_path)
            return {
                "filename": os.path.basename(image_path),
                "file_size": file_size,
                "file_extension": file_ext,
                "base64_data": base64_data,
                "mime_type": f"image/{file_ext[1:]}" if file_ext else "image/jpeg"
            }
        else:
            return {
                "filename": os.path.basename(image_path),
                "file_size": file_size,
                "file_extension": file_ext,
                "base64_data": None,
                "error": "File too large for base64 encoding"
            }
    except Exception as e:
        return {
            "filename": os.path.basename(image_path),
            "error": str(e)
        }

@image_processing_mcp.tool
async def run_image_processing(
    github_url: str,
    ctx: Context,
    image_filename: str = "input.png",
    input_image_path: str = "./sample_problems/input.png"
) -> Dict[str, Any]:
    """
    Clone repo, create Docker image, run it with mounted input/output.

    Args:
        github_url: GitHub repo with image processing code
        ctx: context object
        image_filename: what filename user expects (inside /input/)
        input_image_path: where host image is (will be mounted)

    Returns:
        Dictionary with Docker run result
    """
    try:
        repo_name = github_url.split("/")[-1].replace(".git", "")
        run_dir = os.path.join(BASE_DIR, repo_name)
        code_dir = os.path.join(run_dir, "code")
        input_dir = os.path.join(run_dir, "input")
        output_dir = os.path.join(run_dir, "output")

        # Prepare directories
        await ctx.info("Setting up run directories...")
        for d in [code_dir, input_dir, output_dir]:
            os.makedirs(d, exist_ok=True)

        # Clean up existing code directory if it exists
        if os.path.exists(code_dir) and os.listdir(code_dir):
            await ctx.info("Removing existing code directory...")
            shutil.rmtree(code_dir)
            os.makedirs(code_dir, exist_ok=True)

        # Clone user repo
        await ctx.info("Cloning user repo...")
        subprocess.run(["git", "clone", github_url, code_dir], check=True)

        # Copy image to input folder
        shutil.copyfile(input_image_path, os.path.join(input_dir, image_filename))

        # Create Dockerfile
        await ctx.info("Creating Dockerfile...")
        dockerfile = f"""
        FROM python:3.10-slim

        RUN apt-get update && apt-get install -y \\
            git \\
            libgl1-mesa-glx \\
            libglib2.0-0 \\
            libsm6 \\
            libxext6 \\
            libxrender-dev \\
            libgomp1 \\
            && pip install --no-cache-dir opencv-python numpy matplotlib pillow scikit-image \\
            && apt-get clean \\
            && rm -rf /var/lib/apt/lists/*

        WORKDIR /app

        COPY code/ /app/
        COPY input/ /input/
        VOLUME /output/

        CMD ["python", "main.py"]
        """

        with open(os.path.join(run_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile)

        image_tag = f"{repo_name.lower()}-image:latest"

        # Build Docker image
        await ctx.info("Building Docker image...")
        subprocess.run(["docker", "build", "-t", image_tag, run_dir], check=True)

        # Run Docker container
        await ctx.info("Running Docker container...")
        subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{input_dir}:/input",
            "-v", f"{output_dir}:/output",
            image_tag
        ], check=True)

        # Check output
        result_files = os.listdir(output_dir)
        return {
            "status": "success",
            "output_files": result_files,
            "output_path": output_dir
        }

    except Exception as e:
        error_msg = f"Image processing contest failed: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

@image_processing_mcp.tool
async def get_output_images_data(
    ctx: Context,
    repo_name: str
) -> Dict[str, Any]:
    """
    Get output images data with base64 encoding for future agent consumption.
    
    Args:
        ctx: context object
        repo_name: name of the repository/run to get images from
    
    Returns:
        Dictionary with encoded image data for agent to consume
    """
    try:
        run_dir = os.path.join(BASE_DIR, repo_name)
        output_dir = os.path.join(run_dir, "output")
        
        if not os.path.exists(output_dir):
            raise ToolError(f"Output directory not found: {output_dir}")
        
        # Get and encode all images
        image_data = []
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                    image_info = get_image_info(file_path)
                    if image_info.get('base64_data'):
                        image_data.append(image_info)
        
        await ctx.info(f"Prepared {len(image_data)} images for agent consumption")
        
        return {
            "status": "success",
            "repo_name": repo_name,
            "output_path": output_dir,
            "images": image_data,
            "image_count": len(image_data),
            "message": "Image data ready for agent consumption"
        }
        
    except Exception as e:
        error_msg = f"Error preparing image data: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

if __name__ == "__main__":
    print("🚀 Starting Image Processing MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server endpoints available at:")
    print("🌐 Server available at: http://127.0.0.1:8005/image_processing/mcp")
    print("\nPress Ctrl+C to stop the server")

    image_processing_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8005,
        path="/image_processing/mcp",
        log_level="info"
    )
