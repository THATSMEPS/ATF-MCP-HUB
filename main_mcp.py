from contextlib import asynccontextmanager
import contextlib
import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

# Import your MCP servers
from docker_mcp import docker_mcp
from git_clone_mcp import git_clone_mcp 
from dependencies_mcp import dependencies_mcp
from mysql_query_mcp import mysql_query_mcp
from mongodb_mcp import mongodb_mcp
from image_processing_mcp import image_processing_mcp
from fastapi_mcp import fastapi_mcp
from react_contest_mcp import react_contest_mcp
from nodejs_mcp import nodejs_mcp

# Create main MCP instance
main_mcp = FastMCP(name="ATF Tools Main Server")

def _server():
    """Configure and mount all MCP servers"""
    main_mcp.mount("docker", docker_mcp)
    main_mcp.mount("git_clone", git_clone_mcp)
    main_mcp.mount("dependencies", dependencies_mcp)
    main_mcp.mount("mysql_query", mysql_query_mcp)
    main_mcp.mount("mongodb", mongodb_mcp)
    main_mcp.mount("image_processing", image_processing_mcp)
    main_mcp.mount("fastapi", fastapi_mcp)
    main_mcp.mount("react_contest", react_contest_mcp)
    main_mcp.mount("nodejs", nodejs_mcp)

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
    mysql_query_app = mysql_query_mcp.http_app()
    mongodb_app = mongodb_mcp.http_app()
    image_processing_app = image_processing_mcp.http_app()
    fastapi_app = fastapi_mcp.http_app()
    react_contest_app = react_contest_mcp.http_app()
    nodejs_mcp_app = nodejs_mcp.http_app()

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(docker_app.lifespan(docker_app))
            await stack.enter_async_context(git_clone_app.lifespan(git_clone_app))
            await stack.enter_async_context(dependencies_app.lifespan(dependencies_app))
            await stack.enter_async_context(mysql_query_app.lifespan(mysql_query_app))
            await stack.enter_async_context(mongodb_app.lifespan(mongodb_app))
            await stack.enter_async_context(image_processing_app.lifespan(image_processing_app))
            await stack.enter_async_context(fastapi_app.lifespan(fastapi_app))
            await stack.enter_async_context(react_contest_app.lifespan(react_contest_app))
            await stack.enter_async_context(nodejs_mcp_app.lifespan(nodejs_mcp_app))
            yield

    http_app = Starlette(
        routes=[
            Mount("/tools/docker", app=docker_app),
            Mount("/tools/git_clone", app=git_clone_app),
            Mount("/tools/dependencies", app=dependencies_app),
            Mount("/tools/mysql_query", app=mysql_query_app),
            Mount("/tools/mongodb", app=mongodb_app),
            Mount("/tools/image_processing", app=image_processing_app),
            Mount("/tools/fastapi", app=fastapi_app),
            Mount("/tools/react_contest", app=react_contest_app),
            Mount("/tools/nodejs", app=nodejs_mcp_app)
        ],
        lifespan=lifespan
    )

    uvicorn.run(http_app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    print("🚀 Starting ATF Tools Main Server...")
    print("📡 Transport: FastAPI/Starlette")
    print("🌐 Server endpoints available at:")
    print("   - http://127.0.0.1:8002/tools/docker/mcp")
    print("   - http://127.0.0.1:8004/tools/git_clone/mcp")
    print("   - http://127.0.0.1:8001/tools/dependencies/mcp")
    print("   - http://127.0.0.1:8007/tools/mysql_query/mcp")
    print("   - http://127.0.0.1:8006/tools/mongodb/mcp")
    print("   - http://127.0.0.1:8003/tools/fastapi/mcp")
    print("   - http://127.0.0.1:8005/tools/image_processing/mcp")
    print("   - http://127.0.0.1:8009/tools/react_contest/mcp")
    print("   - http://127.0.0.1:8008/tools/nodejs/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    _server()
    main_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        path="/tools/mcp",
        log_level="info"  # 5 minute timeout for the server
    )