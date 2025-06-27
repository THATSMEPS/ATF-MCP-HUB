import json
from typing import Optional, Dict, Any, Union
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import pymongo
import mysql.connector
from urllib.parse import quote_plus
import os

mcp = FastMCP(name="Database Query MCP Server")

class DatabaseConfig:
    def __init__(self, db_type: str, host: str, port: int, username: str, password: str, database: str):
        self.db_type = db_type.lower()
        self.host = host
        self.port = port
        self.username = quote_plus(username)
        self.password = quote_plus(password)
        self.database = database

@mcp.tool
async def execute_query(
    db_config: Dict[str, Any],
    query: str,
    ctx: Context,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a database query for AI evaluation.
    
    Args:
        db_config: Database configuration dictionary
        query: Query string to execute
        ctx: MCP Context object
        params: Optional query parameters
        
    Returns:
        Dictionary containing query results
    """
    try:
        config = DatabaseConfig(**db_config)
        await ctx.info(f"Executing query on {config.db_type} database")
        
        if config.db_type == "mongodb":
            return await execute_mongodb_query(config, query, ctx, params)
        elif config.db_type == "mysql":
            return await execute_sql_query(config, query, ctx, params)
        else:
            raise ToolError(f"Unsupported database type: {config.db_type}")

    except Exception as e:
        error_msg = f"Database query error: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

async def execute_mongodb_query(
    config: DatabaseConfig,
    query: str,
    ctx: Context,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute MongoDB query"""
    try:
        uri = os.getenv('MONGODB_URI',f"mongodb://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}")
        client = pymongo.MongoClient(uri)
        db = client[config.database]
        
        # Parse the query string as JSON
        query_dict = json.loads(query)
        collection_name = query_dict.get("collection")
        operation = query_dict.get("operation")
        
        if not collection_name or not operation:
            raise ToolError("Query must specify 'collection' and 'operation'")
            
        collection = db[collection_name]
        
        operations = {
            "find": lambda: list(collection.find(query_dict.get("filter", {}))),
            "insert": lambda: collection.insert_one(query_dict.get("document", {})),
            "update": lambda: collection.update_many(
                query_dict.get("filter", {}),
                query_dict.get("update", {})
            ),
            "delete": lambda: collection.delete_many(query_dict.get("filter", {}))
        }
        
        if operation not in operations:
            raise ToolError(f"Unsupported MongoDB operation: {operation}")
        
        result = operations[operation]()
        
        return {
            "status": "success",
            "operation": operation,
            "result": result if isinstance(result, list) else str(result)
        }

    finally:
        client.close()

async def execute_sql_query(
    config: DatabaseConfig,
    query: str,
    ctx: Context,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute SQL query"""
    connection = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", config.host),
            port=config.port,
            user=config.username,
            password=config.password,
            database=config.database
        )
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or {})
        
        if query.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()
        else:
            connection.commit()
            result = {"affected_rows": cursor.rowcount}
            
        return {
            "status": "success",
            "query_type": "select" if query.strip().upper().startswith("SELECT") else "modify",
            "result": result
        }

    finally:
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    print("🚀 Starting Database Query MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server endpoints:")
    print("   MongoDB: http://localhost:8001/db_query/mcp/execute_query")
    print("\nPress Ctrl+C to stop the server")
    
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
        path="/db_query/mcp",
        log_level="info"
    )