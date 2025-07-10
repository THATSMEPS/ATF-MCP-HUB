import subprocess
import os
import json
import time
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import mysql.connector

mysql_query_mcp = FastMCP(name="MySQL Evaluator MCP Server")

@mysql_query_mcp.tool
async def create_mysql_docker_environment(
    ctx: Context,
    database_name: str = "contest_db",
    mysql_port: int = 3306
) -> Dict[str, Any]:
    """
    Create a MySQL Docker container for query evaluation.
    
    Args:
        ctx: MCP Context object
        database_name: Name of the database to create
        mysql_port: Port to expose MySQL on
        
    Returns:
        Dictionary containing MySQL container details
    """
    try:
        await ctx.info("Creating MySQL Docker environment...")
        
        # Generate a unique container name
        container_name = f"mysql-evaluator-{int(time.time())}"
        
        # Run MySQL container
        run_process = subprocess.run([
            'docker', 'run',
            '-d',  # Detached mode
            '--name', container_name,
            '-e', 'MYSQL_ROOT_PASSWORD=rootpassword',
            '-e', f'MYSQL_DATABASE={database_name}',
            '-e', 'MYSQL_USER=evaluator',
            '-e', 'MYSQL_PASSWORD=evaluatorpass',
            '-p', f'{mysql_port}:3306',
            'mysql'
        ], capture_output=True, text=True, check=True)
        
        container_id = run_process.stdout.strip()
        
        # Wait for MySQL to be ready
        await ctx.info("Waiting for MySQL to be ready...")
        await _wait_for_mysql_ready(container_id, ctx)
        
        return {
            'status': 'success',
            'container_id': container_id,
            'container_name': container_name,
            'database_name': database_name,
            'port': mysql_port,
            'connection_info': {
                'host': 'localhost',
                'port': mysql_port,
                'user': 'evaluator',
                'password': 'evaluatorpass',
                'database': database_name
            }
        }
        
    except Exception as e:
        error_msg = f"Error creating MySQL environment: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

@mysql_query_mcp.tool
async def setup_contest_database(
    container_id: str,
    setup_queries: List[str],
    ctx: Context
) -> Dict[str, Any]:
    """
    Setup the contest database with initial tables and data.
    
    Args:
        container_id: MySQL container ID
        setup_queries: List of SQL queries to setup the database
        ctx: MCP Context object
        
    Returns:
        Dictionary containing setup status
    """
    try:
        await ctx.info("Setting up contest database...")
        
        for i, query in enumerate(setup_queries):
            await ctx.info(f"Executing setup query {i+1}/{len(setup_queries)}")
            
            # Execute query inside the container
            exec_process = subprocess.run([
                'docker', 'exec', container_id,
                'mysql', '-u', 'evaluator', '-pevaluatorpass', 'contest_db',
                '-e', query
            ], capture_output=True, text=True)
            
            if exec_process.returncode != 0:
                raise ToolError(f"Setup query failed: {exec_process.stderr}")
                
        await ctx.info("Database setup completed successfully")
        
        return {
            'status': 'success',
            'queries_executed': len(setup_queries),
            'message': 'Database setup completed'
        }
        
    except Exception as e:
        error_msg = f"Error setting up database: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

@mysql_query_mcp.tool
async def evaluate_mysql_query(
    container_id: str,
    user_query: str,
    expected_result: Optional[List[Dict[str, Any]]],
    ctx: Context,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """
    Evaluate a MySQL query against the contest database.
    
    Args:
        container_id: MySQL container ID
        user_query: SQL query to evaluate
        expected_result: Expected query result for comparison
        ctx: MCP Context object
        timeout_seconds: Query timeout in seconds
        
    Returns:
        Dictionary containing evaluation results
    """
    try:
        await ctx.info(f"Evaluating query: {user_query[:100]}...")
        
        # Execute the query inside the container
        exec_process = subprocess.run([
            'docker', 'exec', container_id,
            'mysql', '-u', 'evaluator', '-pevaluatorpass', 'contest_db',
            '--batch',  # Non-interactive mode
            '--raw',    # Don't escape special characters
            '--skip-column-names',  # Don't include column headers
            '-e', user_query
        ], capture_output=True, text=True, timeout=timeout_seconds)
        
        if exec_process.returncode != 0:
            return {
                'status': 'error',
                'error': exec_process.stderr,
                'query': user_query,
                'execution_time': None,
                'correct': False
            }
        
        # Parse the JSON result
        try:
            if exec_process.stdout.strip():
                actual_result = json.loads(exec_process.stdout)
            else:
                actual_result = []
        except json.JSONDecodeError:
            # If not JSON, treat as simple text output
            actual_result = exec_process.stdout.strip()
        
        # Compare with expected result if provided
        is_correct = True
        comparison_details = None
        
        if expected_result is not None:
            is_correct = _compare_results(actual_result, expected_result)
            comparison_details = {
                'expected': expected_result,
                'actual': actual_result,
                'match': is_correct
            }
        
        return {
            'status': 'success',
            'query': user_query,
            'result': actual_result,
            'correct': is_correct,
            'comparison': comparison_details,
            'execution_time': None  # Could be enhanced to measure time
        }
        
    except subprocess.TimeoutExpired:
        return {
            'status': 'timeout',
            'error': f'Query timed out after {timeout_seconds} seconds',
            'query': user_query,
            'correct': False
        }
    except Exception as e:
        error_msg = f"Error evaluating query: {str(e)}"
        await ctx.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'query': user_query,
            'correct': False
        }

@mysql_query_mcp.tool
async def cleanup_mysql_environment(container_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Clean up the MySQL Docker environment.
    
    Args:
        container_id: MySQL container ID to cleanup
        ctx: MCP Context object
        
    Returns:
        Dictionary containing cleanup status
    """
    try:
        await ctx.info(f"Cleaning up MySQL container: {container_id}")
        
        # Stop the container
        subprocess.run(['docker', 'stop', container_id], 
                      capture_output=True, text=True, check=True)
        
        # Remove the container
        subprocess.run(['docker', 'rm', container_id], 
                      capture_output=True, text=True, check=True)
        
        return {
            'status': 'success',
            'message': f'Container {container_id} cleaned up successfully'
        }
        
    except Exception as e:
        error_msg = f"Error cleaning up container: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def _wait_for_mysql_ready(container_id: str, ctx: Context, max_attempts: int = 30):
    """Wait for MySQL to be ready to accept connections"""
    for attempt in range(max_attempts):
        try:
            check_process = subprocess.run([
                'docker', 'exec', container_id,
                'mysql', '-u', 'evaluator', '-pevaluatorpass', '-e', 'SELECT 1'
            ], capture_output=True, text=True, timeout=5)
            
            if check_process.returncode == 0:
                await ctx.info("MySQL is ready!")
                return
                
        except subprocess.TimeoutExpired:
            pass
            
        await ctx.info(f"Waiting for MySQL... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    raise ToolError("MySQL failed to become ready within timeout period")

def _compare_results(actual: Any, expected: Any) -> bool:
    """Compare actual and expected query results"""
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False
        
        # Sort both results for comparison (in case order doesn't matter)
        try:
            actual_sorted = sorted(actual, key=lambda x: str(x) if x else "")
            expected_sorted = sorted(expected, key=lambda x: str(x) if x else "")
            return actual_sorted == expected_sorted
        except:
            return actual == expected
    
    return actual == expected

if __name__ == "__main__":
    print("🔧 Starting MySQL Evaluator MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server will be available at: http://127.0.0.1:8007/mysql/mcp")
    print("\nPress Ctrl+C to stop the server")
    
    mysql_query_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8007,
        path="/mysql/mcp",
        log_level="info"
    )