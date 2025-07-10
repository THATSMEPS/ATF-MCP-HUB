import subprocess
import time
import json
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

mongodb_mcp = FastMCP(name="MongoDB Evaluator MCP Server")


# Tool 1: Create MongoDB Docker Container (only needs port)

@mongodb_mcp.tool
async def create_docker_container(
    ctx: Context,
    mongo_port: int = 27017
) -> Dict[str, Any]:
    """
    Create a MongoDB Docker container (mongo) and a mongosh (alpine/mongosh:2.0.2) sidecar container in the same network for query evaluation.
    Only the port is taken from the user.
    """
    try:
        await ctx.info("Creating MongoDB Docker environment with mongo and mongosh sidecar...")
        network_name = f"net-mongo-mcp-evaluator-{int(time.time())}"
        container_name = f"db-mongo-mcp-evaluator-{int(time.time())}"
        mongosh_name = f"sh-mongo-mcp-evaluator-{int(time.time())}"

        # Create a user-defined bridge network
        subprocess.run([
            'docker', 'network', 'create', network_name
        ], capture_output=True, text=True)

        # Start the MongoDB container
        run_mongo = subprocess.run([
            'docker', 'run', '-d', '--name', container_name,
            '--network', network_name,
            '-p', f'{mongo_port}:27017',
            'mongo'
        ], capture_output=True, text=True, check=True)
        db_mongo_container_id = run_mongo.stdout.strip()

        # Start the mongosh sidecar container (it will just sleep, so it stays running)
        run_mongosh = subprocess.run([
            'docker', 'run', '-d', '--name', mongosh_name,
            '--network', network_name,
            'alpine/mongosh:2.0.2', 'sleep', 'infinity'
        ], capture_output=True, text=True, check=True)
        sh_mongo_container_id = run_mongosh.stdout.strip()

        await ctx.info("MongoDB and mongosh containers created and running in the same network.")
        return {
            'status': 'success',
            'db_mongo_container_id': db_mongo_container_id,
            'sh_mongo_container_id': sh_mongo_container_id,
            'mongo_container_name': container_name,
            'mongosh_container_name': mongosh_name,
            'network_name': network_name,
            'port': mongo_port,
            'message': 'MongoDB and mongosh containers created and running.'
        }
    except Exception as e:
        error_msg = f"Error creating MongoDB/mongosh environment: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

# Tool 2: Create Database in Existing MongoDB Container (using mongosh container)
@mongodb_mcp.tool
async def create_database(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str = 'mcp_database'
) -> Dict[str, Any]:
    """
    Create a database in a running MongoDB container by using mongosh in the mongosh container.
    """
    try:
        await ctx.info(f"Creating database '{database_name}' in MongoDB container '{db_mongo_container_name}' using mongosh container '{sh_mongo_container_name}'...")
        # Use mongosh container to connect to the mongo container and insert a test document
        insert_process = subprocess.run([
            'docker', 'exec', '-it', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--eval', 'db.testcollection.insertOne({ name: "test" })',
        ], capture_output=True, text=True)
        if insert_process.returncode != 0:
            raise ToolError(f"Failed to insert test document: {insert_process.stderr}\nSTDOUT: {insert_process.stdout}")
        
        return {
            'status': 'success',
            'db_mongo_container_name': db_mongo_container_name,
            'sh_mongo_container_name': sh_mongo_container_name,
            'database_name': database_name,
            'message': f"Database '{database_name}' created and test document inserted successfully."
        }
    except Exception as e:
        error_msg = f"Error creating MongoDB database: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

# Tool 3: Delete Database
@mongodb_mcp.tool
async def delete_database(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str
) -> Dict[str, Any]:
    """
    Delete a database in a running MongoDB container using mongosh in the mongosh container.
    """
    try:
        await ctx.info(f"Dropping database '{database_name}' in MongoDB container '{db_mongo_container_name}' using mongosh container '{sh_mongo_container_name}'...")
        drop_process = subprocess.run([
            'docker', 'exec', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--eval', 'db.dropDatabase()'
        ], capture_output=True, text=True)
        if drop_process.returncode != 0:
            raise ToolError(f"Failed to drop database: {drop_process.stderr}\nSTDOUT: {drop_process.stdout}")
        return {
            'status': 'success',
            'database_name': database_name,
            'message': f"Database '{database_name}' dropped successfully."
        }
    except Exception as e:
        error_msg = f"Error dropping MongoDB database: {str(e)}"
        await ctx.error(error_msg)
        raise ToolError(error_msg)

# Tool 4: Create Collection (single or multiple, comma-separated input)
@mongodb_mcp.tool
async def create_collection(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_names: str
) -> Dict[str, Any]:
    """
    Create one or more collections in a MongoDB database using mongosh.
    Provide collection_names as a comma-separated string (e.g., 'col1' or 'col1,col2,col3').
    """
    # Split and strip whitespace from each name
    names = [name.strip() for name in collection_names.split(',') if name.strip()]
    if not names:
        raise ToolError("No valid collection names provided.")
    results = []
    for name in names:
        try:
            await ctx.info(f"Creating collection '{name}' in database '{database_name}'...")
            create_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--eval', f'db.createCollection("{name}")'
            ], capture_output=True, text=True)
            if create_process.returncode != 0:
                raise ToolError(f"Failed to create collection: {create_process.stderr}\nSTDOUT: {create_process.stdout}")
            results.append({'collection_name': name, 'status': 'success'})
        except Exception as e:
            results.append({'collection_name': name, 'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to create {len(names)} collection(s)."
    }

# Tool 5: Read Collection (run arbitrary query on a single collection, with collection name check)
@mongodb_mcp.tool
async def read_collection(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    query: str
) -> Dict[str, Any]:
    """
    Run an arbitrary MongoDB read query (e.g., find, aggregate, etc.) on a single collection.
    Checks that the collection_name matches the collection referenced in the query (e.g., db.collection_name).
    """
    import re
    # Try to extract the collection name from the query (e.g., db.collection.find(...))
    match = re.match(r"db\.([a-zA-Z0-9_]+)\.", query.strip())
    if not match:
        return {
            'status': 'error',
            'message': 'Could not parse collection name from query. Please use the format db.<collection>.<operation>()'
        }
    query_collection = match.group(1)
    if query_collection != collection_name:
        return {
            'status': 'error',
            'message': f"collection_name ('{collection_name}') does not match collection referenced in query ('{query_collection}')."
        }
    try:
        await ctx.info(f"Running read query on collection '{collection_name}' in database '{database_name}': {query}")
        proc = subprocess.run([
            'docker', 'exec', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--quiet', '--eval', f'JSON.stringify({query})'
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Query failed: {proc.stderr}\nSTDOUT: {proc.stdout}"
            }
        try:
            result = json.loads(proc.stdout.strip())
        except Exception:
            result = proc.stdout.strip()
        return {
            'status': 'success',
            'message': f"Query executed successfully.",
            'result': result
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Query is wrong, cannot perform: {str(e)}"
        }

# Tool 6: Update Collection (run arbitrary query on a single collection, with collection name check)
@mongodb_mcp.tool
async def update_collection(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    query: str
) -> Dict[str, Any]:
    """
    Run an arbitrary MongoDB query (e.g., rename, index, etc.) on a single collection.
    Checks that the collection_name matches the collection referenced in the query (e.g., db.collection_name).
    """
    import re
    # Try to extract the collection name from the query (e.g., db.oldCollection.something)
    match = re.match(r"db\.([a-zA-Z0-9_]+)\.", query.strip())
    if not match:
        return {
            'status': 'error',
            'message': 'Could not parse collection name from query. Please use the format db.<collection>.<operation>()'
        }
    query_collection = match.group(1)
    if query_collection != collection_name:
        return {
            'status': 'error',
            'message': f"collection_name ('{collection_name}') does not match collection referenced in query ('{query_collection}')."
        }
    try:
        await ctx.info(f"Running query on collection '{collection_name}' in database '{database_name}': {query}")
        proc = subprocess.run([
            'docker', 'exec', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--eval', query
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Query failed: {proc.stderr}\nSTDOUT: {proc.stdout}"
            }
        return {
            'status': 'success',
            'message': f"Query executed successfully.",
            'stdout': proc.stdout.strip()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Query is wrong, cannot perform: {str(e)}"
        }

# Tool 7: Delete Collection (single or multiple, comma-separated input)
@mongodb_mcp.tool
async def delete_collection(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_names: str
) -> Dict[str, Any]:
    """
    Drop one or more collections from a MongoDB database using mongosh.
    Provide collection_names as a comma-separated string (e.g., 'col1' or 'col1,col2,col3').
    """
    # Split and strip whitespace from each name
    names = [name.strip() for name in collection_names.split(',') if name.strip()]
    if not names:
        raise ToolError("No valid collection names provided.")
    results = []
    for name in names:
        try:
            await ctx.info(f"Dropping collection '{name}' in database '{database_name}'...")
            drop_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--eval', f'db.{name}.drop()'
            ], capture_output=True, text=True)
            if drop_process.returncode != 0:
                raise ToolError(f"Failed to drop collection: {drop_process.stderr}\nSTDOUT: {drop_process.stdout}")
            results.append({'collection_name': name, 'status': 'success'})
        except Exception as e:
            results.append({'collection_name': name, 'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to delete {len(names)} collection(s)."
    }

# Tool 8: Create Document (single, with collection name check in query)
@mongodb_mcp.tool
async def create_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    query: str
) -> Dict[str, Any]:
    """
    Run an arbitrary MongoDB insert query (e.g., insertOne, insertMany) on a single collection.
    Checks that the collection_name matches the collection referenced in the query (e.g., db.collection_name).
    """
    import re
    match = re.match(r"db\.([a-zA-Z0-9_]+)\.", query.strip())
    if not match:
        return {
            'status': 'error',
            'message': 'Could not parse collection name from query. Please use the format db.<collection>.<operation>()'
        }
    query_collection = match.group(1)
    if query_collection != collection_name:
        return {
            'status': 'error',
            'message': f"collection_name ('{collection_name}') does not match collection referenced in query ('{query_collection}')."
        }
    try:
        await ctx.info(f"Running insert query on collection '{collection_name}' in database '{database_name}': {query}")
        proc = subprocess.run([
            'docker', 'exec', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--eval', query
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Query failed: {proc.stderr}\nSTDOUT: {proc.stdout}"
            }
        return {
            'status': 'success',
            'message': f"Insert query executed successfully.",
            'stdout': proc.stdout.strip()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Query is wrong, cannot perform: {str(e)}"
        }

# Tool 9: Read Document (single, with collection name check in query)
@mongodb_mcp.tool
async def read_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    query: str
) -> Dict[str, Any]:
    """
    Run an arbitrary MongoDB read query (e.g., findOne, find, aggregate) on a single collection.
    Checks that the collection_name matches the collection referenced in the query (e.g., db.collection_name).
    """
    import re
    match = re.match(r"db\.([a-zA-Z0-9_]+)\.", query.strip())
    if not match:
        return {
            'status': 'error',
            'message': 'Could not parse collection name from query. Please use the format db.<collection>.<operation>()'
        }
    query_collection = match.group(1)
    if query_collection != collection_name:
        return {
            'status': 'error',
            'message': f"collection_name ('{collection_name}') does not match collection referenced in query ('{query_collection}')."
        }
    try:
        await ctx.info(f"Running read query on collection '{collection_name}' in database '{database_name}': {query}")
        proc = subprocess.run([
            'docker', 'exec', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--quiet', '--eval', f'JSON.stringify({query})'
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Query failed: {proc.stderr}\nSTDOUT: {proc.stdout}"
            }
        try:
            result = json.loads(proc.stdout.strip())
        except Exception:
            result = proc.stdout.strip()
        return {
            'status': 'success',
            'message': f"Query executed successfully.",
            'result': result
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Query is wrong, cannot perform: {str(e)}"
        }

# Tool 10: Update Document (single, with collection name check in query)
@mongodb_mcp.tool
async def update_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    query: str
) -> Dict[str, Any]:
    """
    Run an arbitrary MongoDB update query (e.g., updateOne, updateMany) on a single collection.
    Checks that the collection_name matches the collection referenced in the query (e.g., db.collection_name).
    """
    import re
    match = re.match(r"db\.([a-zA-Z0-9_]+)\.", query.strip())
    if not match:
        return {
            'status': 'error',
            'message': 'Could not parse collection name from query. Please use the format db.<collection>.<operation>()'
        }
    query_collection = match.group(1)
    if query_collection != collection_name:
        return {
            'status': 'error',
            'message': f"collection_name ('{collection_name}') does not match collection referenced in query ('{query_collection}')."
        }
    try:
        await ctx.info(f"Running update query on collection '{collection_name}' in database '{database_name}': {query}")
        proc = subprocess.run([
            'docker', 'exec', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--eval', query
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Query failed: {proc.stderr}\nSTDOUT: {proc.stdout}"
            }
        return {
            'status': 'success',
            'message': f"Update query executed successfully.",
            'stdout': proc.stdout.strip()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Query is wrong, cannot perform: {str(e)}"
        }

# Tool 11: Delete Document (single, with collection name check in query)
@mongodb_mcp.tool
async def delete_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    query: str
) -> Dict[str, Any]:
    """
    Run an arbitrary MongoDB delete query (e.g., deleteOne, deleteMany) on a single collection.
    Checks that the collection_name matches the collection referenced in the query (e.g., db.collection_name).
    """
    import re
    match = re.match(r"db\.([a-zA-Z0-9_]+)\.", query.strip())
    if not match:
        return {
            'status': 'error',
            'message': 'Could not parse collection name from query. Please use the format db.<collection>.<operation>()'
        }
    query_collection = match.group(1)
    if query_collection != collection_name:
        return {
            'status': 'error',
            'message': f"collection_name ('{collection_name}') does not match collection referenced in query ('{query_collection}')."
        }
    try:
        await ctx.info(f"Running delete query on collection '{collection_name}' in database '{database_name}': {query}")
        proc = subprocess.run([
            'docker', 'exec', sh_mongo_container_name,
            'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
            '--eval', query
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                'status': 'error',
                'message': f"Query failed: {proc.stderr}\nSTDOUT: {proc.stdout}"
            }
        return {
            'status': 'success',
            'message': f"Delete query executed successfully.",
            'stdout': proc.stdout.strip()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Query is wrong, cannot perform: {str(e)}"
        }

if __name__ == "__main__":
    print("🔧 Starting MongoDB Evaluator MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server will be available at: http://127.0.0.1:8006/mongodb/mcp")
    print("\nPress Ctrl+C to stop the server")

    mongodb_mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8006,
        path="/mongodb/mcp",
        log_level="info"
    )