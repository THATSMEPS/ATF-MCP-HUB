import json
from typing import Optional, Dict, Any
import requests
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

mcp = FastMCP(name="Node.js Request MCP Server")

@mcp.tool
async def make_api_request(method: str, url: str, ctx: Context, payload: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute an HTTP request and return the response.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: Target URL for the request
        ctx: MCP Context object
        payload: Optional JSON payload string for POST/PUT requests
        
    Returns:
        Dictionary containing the API response details
    """
    try:
        await ctx.info(f"Making {method.upper()} request to: {url}")
        await ctx.report_progress(progress=0, total=100)

        headers = {'Content-Type': 'application/json'}
        
        # Parse payload if provided
        if payload:
            try:
                json_payload = json.loads(payload)
                await ctx.info("Payload parsed successfully")
            except json.JSONDecodeError as e:
                raise ToolError(f"Invalid JSON payload: {str(e)}")
        else:
            json_payload = None

        await ctx.report_progress(progress=30, total=100)

        # Execute the request
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                json=json_payload,
                headers=headers,
                timeout=10
            )
            await ctx.report_progress(progress=70, total=100)
            
            # Try to parse response as JSON
            try:
                response_body = response.json()
                await ctx.info("Response received and parsed as JSON")
            except json.JSONDecodeError:
                response_body = response.text
                await ctx.info("Response received as text")

            result = {
                "status": "success",
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body
            }
            
        except requests.exceptions.RequestException as e:
            raise ToolError(f"API request failed: {str(e)}")

        await ctx.report_progress(progress=100, total=100)
        await ctx.info(f"Request completed with status code: {response.status_code}")
        
        return result

    except Exception as e:
        error_msg = f"Error making API request: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)
    
if __name__ == "__main__":
    # Start the MCP server
    print("🚀 Starting Nodejs Request MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server will be available at: http://127.0.0.1:8000/git_clone/mcp")
    print("\nPress Ctrl+C to stop the server")

    mcp.run(
        host="127.0.0.1",
        port=8000,
        path="/nodejs_mcp",
        transport="streamable-http",
        log_level="info"
    )