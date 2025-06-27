from contextlib import asynccontextmanager
import contextlib
import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

# Import your MCP servers
from docker_mcp import mcp as docker_mcp
from git_clone_mcp import mcp as git_clone_mcp 
from dependencies_mcp import mcp as dependencies_mcp

# Create main MCP instance
main_mcp = FastMCP(name="ATF Tools Main Server")

def _server():
    """Configure and mount all MCP servers"""
    main_mcp.mount("docker", docker_mcp)
    main_mcp.mount("git_clone", git_clone_mcp)
    main_mcp.mount("dependencies", dependencies_mcp)

def run_streamable_http():
    """Run with streamable HTTP transport"""
    _server()
    main_mcp.run(transport="streamable-http")

def run_fast_api():
    """Run with FastAPI/Starlette setup"""
    # Get HTTP apps from each MCP
    docker_app = docker_mcp.http_app()
    git_clone_app = git_clone_mcp.http_app()
    dependencies_app = dependencies_mcp.http_app()

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(docker_app.lifespan(docker_app))
            await stack.enter_async_context(git_clone_app.lifespan(git_clone_app))
            await stack.enter_async_context(dependencies_app.lifespan(dependencies_app))
            yield

    http_app = Starlette(
        routes=[
            Mount("/tools/docker", app=docker_app),
            Mount("/tools/git_clone", app=git_clone_app),
            Mount("/tools/dependencies", app=dependencies_app)
        ],
        lifespan=lifespan
    )

    uvicorn.run(http_app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    print("🚀 Starting ATF Tools Main Server...")
    print("📡 Transport: FastAPI/Starlette")
    print("🌐 Server endpoints available at:")
    print("   - http://127.0.0.1:8000/tools/docker")
    print("   - http://127.0.0.1:8000/tools/git_clone")
    print("   - http://127.0.0.1:8000/tools/dependencies")
    print("\nPress Ctrl+C to stop the server")
    
    _server()
    main_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        path="/tools/mcp",
        log_level="info"  # 5 minute timeout for the server
    )