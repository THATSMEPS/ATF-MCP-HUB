import subprocess
import time
import json
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

mcp = FastMCP(name="MongoDB Evaluator MCP Server")


# Tool 1: Create MongoDB Docker Container (only needs port)

@mcp.tool
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
@mcp.tool
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
@mcp.tool
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
@mcp.tool
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

# Tool 5: Read Collection (single or multiple)
@mcp.tool
async def read_collection(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str = None,
    collection_names: list = None
) -> Dict[str, Any]:
    """
    Read all documents from one or more collections in a MongoDB database using mongosh.
    Provide either collection_name (str) or collection_names (list of str).
    """
    results = []
    names = []
    if collection_names:
        names = collection_names
    elif collection_name:
        names = [collection_name]
    else:
        raise ToolError("No collection_name or collection_names provided.")
    for name in names:
        try:
            await ctx.info(f"Reading all documents from collection '{name}' in database '{database_name}'...")
            read_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--quiet', '--eval', f'JSON.stringify(db.{name}.find().toArray())'
            ], capture_output=True, text=True)
            if read_process.returncode != 0:
                raise ToolError(f"Failed to read collection: {read_process.stderr}\nSTDOUT: {read_process.stdout}")
            try:
                docs = json.loads(read_process.stdout.strip())
            except Exception:
                docs = read_process.stdout.strip()
            results.append({'collection_name': name, 'status': 'success', 'documents': docs})
        except Exception as e:
            results.append({'collection_name': name, 'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to read {len(names)} collection(s)."
    }

# Tool 6: Update Collection (single or multiple)
@mcp.tool
async def update_collection(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str = None,
    collection_names: list = None,
    filter_query: str = '{}',
    update_query: str = '{}'
) -> Dict[str, Any]:
    """
    Update documents in one or more collections using mongosh. filter_query and update_query should be JSON strings.
    Provide either collection_name (str) or collection_names (list of str).
    """
    results = []
    names = []
    if collection_names:
        names = collection_names
    elif collection_name:
        names = [collection_name]
    else:
        raise ToolError("No collection_name or collection_names provided.")
    for name in names:
        try:
            await ctx.info(f"Updating documents in collection '{name}' in database '{database_name}'...")
            update_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--quiet', '--eval', f'db.{name}.updateMany({filter_query}, {update_query})'
            ], capture_output=True, text=True)
            if update_process.returncode != 0:
                raise ToolError(f"Failed to update collection: {update_process.stderr}\nSTDOUT: {update_process.stdout}")
            results.append({'collection_name': name, 'status': 'success'})
        except Exception as e:
            results.append({'collection_name': name, 'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to update {len(names)} collection(s)."
    }

# Tool 7: Delete Collection (single or multiple)
@mcp.tool
async def delete_collection(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str = None,
    collection_names: list = None
) -> Dict[str, Any]:
    """
    Drop one or more collections from a MongoDB database using mongosh.
    Provide either collection_name (str) or collection_names (list of str).
    """
    results = []
    names = []
    if collection_names:
        names = collection_names
    elif collection_name:
        names = [collection_name]
    else:
        raise ToolError("No collection_name or collection_names provided.")
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

# Tool 8: Create Document (single or multiple)
@mcp.tool
async def create_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    document: str = None,
    documents: list = None
) -> Dict[str, Any]:
    """
    Insert one or more documents into a collection. document should be a JSON string, documents a list of JSON strings.
    """
    docs = []
    if documents:
        docs = documents
    elif document:
        docs = [document]
    else:
        raise ToolError("No document or documents provided.")
    results = []
    for doc in docs:
        try:
            await ctx.info(f"Inserting document into collection '{collection_name}' in database '{database_name}'...")
            insert_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--quiet', '--eval', f'db.{collection_name}.insertOne({doc})'
            ], capture_output=True, text=True)
            if insert_process.returncode != 0:
                raise ToolError(f"Failed to insert document: {insert_process.stderr}\nSTDOUT: {insert_process.stdout}")
            results.append({'status': 'success'})
        except Exception as e:
            results.append({'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to insert {len(docs)} document(s)."
    }

# Tool 9: Read Document (single or multiple)
@mcp.tool
async def read_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    filter_query: str = '{}',
    filter_queries: list = None
) -> Dict[str, Any]:
    """
    Read one or more documents from a collection. filter_query should be a JSON string, filter_queries a list of JSON strings.
    """
    queries = []
    if filter_queries:
        queries = filter_queries
    elif filter_query:
        queries = [filter_query]
    else:
        raise ToolError("No filter_query or filter_queries provided.")
    results = []
    for q in queries:
        try:
            await ctx.info(f"Reading document from collection '{collection_name}' in database '{database_name}'...")
            read_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--quiet', '--eval', f'JSON.stringify(db.{collection_name}.findOne({q}))'
            ], capture_output=True, text=True)
            if read_process.returncode != 0:
                raise ToolError(f"Failed to read document: {read_process.stderr}\nSTDOUT: {read_process.stdout}")
            try:
                doc = json.loads(read_process.stdout.strip())
            except Exception:
                doc = read_process.stdout.strip()
            results.append({'status': 'success', 'document': doc})
        except Exception as e:
            results.append({'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to read {len(queries)} document(s)."
    }

# Tool 10: Update Document (single or multiple)
@mcp.tool
async def update_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    filter_query: str = '{}',
    update_query: str = '{}',
    filter_queries: list = None,
    update_queries: list = None
) -> Dict[str, Any]:
    """
    Update one or more documents in a collection. filter_query and update_query should be JSON strings. If lists are provided, they must be the same length.
    """
    filters = []
    updates = []
    if filter_queries and update_queries and len(filter_queries) == len(update_queries):
        filters = filter_queries
        updates = update_queries
    elif filter_query and update_query:
        filters = [filter_query]
        updates = [update_query]
    else:
        raise ToolError("No valid filter/update queries provided.")
    results = []
    for f, u in zip(filters, updates):
        try:
            await ctx.info(f"Updating document in collection '{collection_name}' in database '{database_name}'...")
            update_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--quiet', '--eval', f'db.{collection_name}.updateOne({f}, {u})'
            ], capture_output=True, text=True)
            if update_process.returncode != 0:
                raise ToolError(f"Failed to update document: {update_process.stderr}\nSTDOUT: {update_process.stdout}")
            results.append({'status': 'success'})
        except Exception as e:
            results.append({'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to update {len(filters)} document(s)."
    }

# Tool 11: Delete Document (single or multiple)
@mcp.tool
async def delete_document(
    ctx: Context,
    db_mongo_container_name: str,
    sh_mongo_container_name: str,
    database_name: str,
    collection_name: str,
    filter_query: str = '{}',
    filter_queries: list = None
) -> Dict[str, Any]:
    """
    Delete one or more documents from a collection. filter_query should be a JSON string, filter_queries a list of JSON strings.
    """
    queries = []
    if filter_queries:
        queries = filter_queries
    elif filter_query:
        queries = [filter_query]
    else:
        raise ToolError("No filter_query or filter_queries provided.")
    results = []
    for q in queries:
        try:
            await ctx.info(f"Deleting document from collection '{collection_name}' in database '{database_name}'...")
            delete_process = subprocess.run([
                'docker', 'exec', sh_mongo_container_name,
                'mongosh', f'mongodb://{db_mongo_container_name}:27017/{database_name}',
                '--quiet', '--eval', f'db.{collection_name}.deleteOne({q})'
            ], capture_output=True, text=True)
            if delete_process.returncode != 0:
                raise ToolError(f"Failed to delete document: {delete_process.stderr}\nSTDOUT: {delete_process.stdout}")
            results.append({'status': 'success'})
        except Exception as e:
            results.append({'status': 'error', 'error': str(e)})
    return {
        'results': results,
        'message': f"Attempted to delete {len(queries)} document(s)."
    }

if __name__ == "__main__":
    print("🔧 Starting MongoDB Evaluator MCP Server...")
    print("📡 Transport: Streamable HTTP")
    print("🌐 Server will be available at: http://127.0.0.1:8004/mongodb/mcp")
    print("\nPress Ctrl+C to stop the server")

    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8004,
        path="/mongodb/mcp",
        log_level="info"
    )