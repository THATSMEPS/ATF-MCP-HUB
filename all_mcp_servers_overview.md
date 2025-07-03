# ATF Tools MCP Servers Overview

## Main Server Configuration

**ATF Tools Main Server** - Unified MCP server hosting multiple specialized tools

- **URL**: `http://127.0.0.1:8000/tools/mcp`
- **Port**: 8000
- **Transport**: Streamable HTTP

## Available MCP Servers

### 1. **Docker MCP** (`/tools/docker`)

Container management tools for building, running, and managing Docker containers and images

- `build_docker_image()` - Build Docker images from Dockerfiles
- `run_docker_container()` - Run containers with custom configurations
- `manage_container_lifecycle()` - Manage container lifecycle (start, stop, remove)
- `execute_container_command()` - Execute commands inside running containers
- `monitor_container_status()` - Monitor container status and logs

### 2. **Dependencies MCP** (`/tools/dependencies`)

Package and dependency management for various programming languages and environments

- `install_packages()` - Install packages for Python (pip), Node.js (npm), Ruby (gem), etc.
- `manage_virtual_environments()` - Manage virtual environments and package isolation
- `resolve_dependencies()` - Resolve dependency conflicts and version compatibility
- `generate_manifests()` - Generate and update dependency manifests (requirements.txt, package.json)
- `support_package_managers()` - Support for multiple package managers and language ecosystems

### 3. **MySQL Query MCP** (`/tools/mysql_query`)

MySQL database evaluation with Docker containers for SQL query testing and validation

- `create_mysql_docker_environment()` - Create MySQL Docker environments with custom configurations
- `create_database()` - Create and manage databases within containers
- `setup_contest_database()` - Setup database schemas and initial data from SQL scripts
- `evaluate_mysql_query()` - Execute and evaluate SQL queries with result comparison
- `cleanup_mysql_environment()` - Cleanup resources and container management

### 4. **MongoDB Query MCP** (`/tools/mongodb_query`)

MongoDB database operations and query evaluation for NoSQL database testing

- `create_mongodb_environment()` - Create MongoDB Docker environments for testing
- `manage_collections()` - Manage MongoDB databases and collections
- `execute_queries()` - Execute MongoDB queries and aggregation pipelines
- `validate_results()` - Validate query results against expected outputs
- `handle_json_operations()` - Handle JSON document operations and data manipulation

## Common Use Cases

- **Contest Evaluation**: Use MySQL/MongoDB MCP for database query testing, Dependencies MCP for environment setup
- **CI/CD Pipelines**: Git Clone MCP for source retrieval, Docker MCP for containerized builds and testing
- **Development Environment**: Dependencies MCP for package management, Docker MCP for consistent environments
- **Automated Testing**: All servers work together to create isolated, reproducible testing environments
- **Code Assessment**: Git Clone + Dependencies + Database MCPs for comprehensive code evaluation workflows

## Quick Start

1. Start main server: `python main_mcp.py`
2. Access individual tools via their endpoints
3. Use streamable HTTP transport for MCP client integration
4. Each tool maintains isolated environments and automatic cleanup

Each server provides specialized tools for automated testing, contest evaluation, and development workflows in the ATF (Automated Testing Framework) ecosystem.
