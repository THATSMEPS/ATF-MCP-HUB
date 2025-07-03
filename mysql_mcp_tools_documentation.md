# MySQL MCP Server - Tools Documentation

## Overview

The MySQL MCP Server provides tools for creating and managing MySQL database environments in Docker containers for query evaluation and testing purposes. This server is designed for automated testing, contest evaluation, and database query validation.

**Server Details:**

- **Name**: MySQL Evaluator MCP Server
- **Transport**: Streamable HTTP
- **Default URL**: `http://127.0.0.1:8003/mysql/mcp`
- **Port**: 8003
- **Path**: `/mysql/mcp`

## Available Tools

### 1. `create_mysql_docker_environment`

**Function**: Creates a MySQL Docker container for query evaluation

**Description**: Sets up a fresh MySQL Docker container with predefined user credentials and configuration. This is the first step in creating a MySQL environment for testing or evaluation purposes.

**Parameters**:

- `mysql_port` (int, optional): Port to expose MySQL on (default: 3306)

**Returns**:

```json
{
  "status": "success",
  "container_id": "mysql-evaluator-1704067200",
  "container_name": "mysql-evaluator-1704067200",
  "port": 3306,
  "connection_info": {
    "host": "localhost",
    "port": 3306,
    "user": "evaluator",
    "password": "evaluatorpass"
  }
}
```

**Use Case**: Initial setup for MySQL testing environment

---

### 2. `create_database`

**Function**: Creates a database in an existing MySQL container

**Description**: Creates a new database within an already running MySQL container. This allows for multiple databases to be created in the same container for different tests or purposes.

**Parameters**:

- `container_id` (string, required): MySQL container ID from create_mysql_docker_environment
- `database_name` (string, required): Name of the database to create

**Returns**:

```json
{
  "status": "success",
  "database_name": "contest_db",
  "container_id": "mysql-evaluator-1704067200",
  "message": "Database contest_db created successfully"
}
```

**Use Case**: Create specific databases for different contest problems or test scenarios

---

### 3. `setup_contest_database`

**Function**: Sets up database schema and initial data

**Description**: Executes a series of SQL queries to create tables, indexes, and insert initial data into a specified database. This is used to prepare the database environment for testing specific scenarios.

**Parameters**:

- `container_id` (string, required): MySQL container ID
- `database_name` (string, required): Name of the database to setup
- `setup_queries` (array of strings, required): List of SQL queries to execute for setup

**Returns**:

```json
{
  "status": "success",
  "database_name": "contest_db",
  "queries_executed": 4,
  "message": "Database contest_db setup completed"
}
```

**Use Case**: Initialize database with tables and test data for contest problems or specific test scenarios

---

### 4. `evaluate_mysql_query`

**Function**: Executes and evaluates SQL queries against the database

**Description**: Runs a user-provided SQL query against the specified database and optionally compares the result with expected output. This is the core evaluation tool for testing SQL query correctness.

**Parameters**:

- `container_id` (string, required): MySQL container ID
- `database_name` (string, required): Name of the database to query
- `user_query` (string, required): SQL query to execute
- `expected_result` (array, optional): Expected query result for comparison
- `timeout_seconds` (int, optional): Query timeout in seconds (default: 30)

**Returns**:

```json
{
  "status": "success",
  "query": "SELECT * FROM users",
  "database": "contest_db",
  "result": [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"}
  ],
  "correct": true,
  "comparison": {
    "expected": [...],
    "actual": [...],
    "match": true
  },
  "execution_time": null
}
```

**Error Response**:

```json
{
  "status": "error",
  "error": "Table 'contest_db.nonexistent' doesn't exist",
  "query": "SELECT * FROM nonexistent",
  "database": "contest_db",
  "correct": false
}
```

**Use Case**: Execute and validate SQL queries for contest evaluation or testing

---

### 5. `cleanup_mysql_environment`

**Function**: Cleans up and removes the MySQL Docker container

**Description**: Stops and removes the MySQL Docker container to free up system resources. This should be called when the evaluation session is complete.

**Parameters**:

- `container_id` (string, required): MySQL container ID to cleanup

**Returns**:

```json
{
  "status": "success",
  "message": "Container mysql-evaluator-1704067200 cleaned up successfully"
}
```

**Use Case**: Clean up resources after completing evaluations or tests

---

## Typical Workflow

### 1. Environment Setup

```
create_mysql_docker_environment(mysql_port=3307)
↓
create_database(container_id, "contest_db")
↓
setup_contest_database(container_id, "contest_db", setup_queries)
```

### 2. Query Evaluation

```
evaluate_mysql_query(container_id, "contest_db", user_query, expected_result)
```

### 3. Cleanup

```
cleanup_mysql_environment(container_id)
```

## Client Integration Examples

### Python Client Example

```python
import requests

class MySQLMCPClient:
    def __init__(self, base_url="http://127.0.0.1:8003/mysql/mcp"):
        self.base_url = base_url

    def create_environment(self, port=3306):
        return self._call_tool("create_mysql_docker_environment", {
            "mysql_port": port
        })

    def create_database(self, container_id, db_name):
        return self._call_tool("create_database", {
            "container_id": container_id,
            "database_name": db_name
        })

    def setup_database(self, container_id, db_name, queries):
        return self._call_tool("setup_contest_database", {
            "container_id": container_id,
            "database_name": db_name,
            "setup_queries": queries
        })

    def evaluate_query(self, container_id, db_name, query, expected=None):
        return self._call_tool("evaluate_mysql_query", {
            "container_id": container_id,
            "database_name": db_name,
            "user_query": query,
            "expected_result": expected
        })

    def cleanup(self, container_id):
        return self._call_tool("cleanup_mysql_environment", {
            "container_id": container_id
        })

    def _call_tool(self, tool_name, params):
        # Implementation depends on MCP client library
        pass
```

### JavaScript/Node.js Client Example

```javascript
class MySQLMCPClient {
  constructor(baseUrl = "http://127.0.0.1:8003/mysql/mcp") {
    this.baseUrl = baseUrl;
  }

  async createEnvironment(port = 3306) {
    return this.callTool("create_mysql_docker_environment", {
      mysql_port: port,
    });
  }

  async createDatabase(containerId, dbName) {
    return this.callTool("create_database", {
      container_id: containerId,
      database_name: dbName,
    });
  }

  async setupDatabase(containerId, dbName, queries) {
    return this.callTool("setup_contest_database", {
      container_id: containerId,
      database_name: dbName,
      setup_queries: queries,
    });
  }

  async evaluateQuery(containerId, dbName, query, expected = null) {
    return this.callTool("evaluate_mysql_query", {
      container_id: containerId,
      database_name: dbName,
      user_query: query,
      expected_result: expected,
    });
  }

  async cleanup(containerId) {
    return this.callTool("cleanup_mysql_environment", {
      container_id: containerId,
    });
  }

  async callTool(toolName, params) {
    // Implementation depends on MCP client library
  }
}
```

## Error Handling

All tools may return error responses with the following structure:

```json
{
  "status": "error",
  "error": "Error description",
  "message": "Additional error details"
}
```

Common error scenarios:

- Docker not available or container creation fails
- Database connection issues
- SQL syntax errors in queries
- Timeout on long-running queries
- Container not found during operations

## Security Considerations

- The MySQL container uses default credentials (evaluator/evaluatorpass)
- Containers are isolated and temporary
- No persistent data storage (containers are removed after use)
- Suitable for testing/evaluation environments only
- Not recommended for production use

## Performance Notes

- Container startup time: 10-30 seconds
- Query timeout: 30 seconds (configurable)
- Memory usage: Depends on MySQL container and data size
- Cleanup is automatic but should be called explicitly for immediate resource cleanup

## Dependencies

- Docker must be installed and running
- MySQL Docker image will be pulled automatically
- Network access to Docker daemon required
- Sufficient system resources for MySQL container
