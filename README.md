# 🛠️ ATF MCP Hub

**ATF = Automated Tool Framework**

A powerful collection of development tools packaged as MCP (Model Context Protocol) servers that help you build, test, and deploy applications with ease.

## 🤔 What is ATF?

**ATF (Automated Tool Framework)** is a suite of specialized development tools designed to automate common programming tasks like:
- Building and running code in containers
- Managing dependencies across different languages
- Processing images and data
- Querying databases
- Cloning and analyzing Git repositories

## 🔌 What is MCP?

**MCP (Model Context Protocol)** is a standardized way for AI assistants to interact with external tools and services. Think of it as a bridge that lets AI models use real development tools safely and effectively.

Each tool in this hub is packaged as an MCP server, making them accessible to AI assistants like Claude, ChatGPT, or other MCP-compatible clients.

## 🛠️ Available Tools

This hub includes 9 powerful MCP servers:

### 🐳 **Docker MCP** (`docker_mcp.py`)
- Build Docker images from code
- Run containers with custom configurations
- Execute commands inside containers
- Monitor container status and logs

### 📦 **Dependencies MCP** (`dependencies_mcp.py`)
- Install packages for Python, Node.js, Ruby, etc.
- Manage virtual environments
- Resolve dependency conflicts
- Generate dependency files (requirements.txt, package.json)

### 🔄 **Git Clone MCP** (`git_clone_mcp.py`)
- Clone GitHub repositories
- Analyze repository structure
- Extract project information

### 🖼️ **Image Processing MCP** (`image_processing_mcp.py`)
- Process and manipulate images
- Apply filters and transformations
- Generate image analysis reports

### 🗄️ **MySQL Query MCP** (`mysql_query_mcp.py`)
- Connect to MySQL databases
- Execute queries and transactions
- Generate database reports

### 🍃 **MongoDB MCP** (`mongodb_mcp.py`)
- Connect to MongoDB databases
- Perform CRUD operations
- Query document collections

### 🚀 **FastAPI MCP** (`fastapi_mcp.py`)
- Create and manage FastAPI applications
- Handle HTTP endpoints
- Manage API documentation

### ⚛️ **React Contest MCP** (`react_contest_mcp.py`)
- Build React applications
- Manage component structures
- Handle frontend workflows

### 🟢 **Node.js MCP** (`nodejs_mcp.py`)
- Run Node.js applications
- Manage npm packages
- Execute JavaScript code

## 📁 Project Structure

```
atf-mcp-hub/
├── main_mcp.py                    # 🚀 Main server entry point
├── docker_mcp.py                  # 🐳 Docker container management
├── dependencies_mcp.py            # 📦 Package dependency tools
├── git_clone_mcp.py              # 🔄 Git repository tools
├── image_processing_mcp.py        # 🖼️ Image processing tools
├── mysql_query_mcp.py            # 🗄️ MySQL database tools
├── mongodb_mcp.py                # 🍃 MongoDB database tools
├── fastapi_mcp.py                # 🚀 FastAPI web framework tools
├── react_contest_mcp.py          # ⚛️ React application tools
├── nodejs_mcp.py                 # 🟢 Node.js runtime tools
├── pyproject.toml                 # 📋 Project dependencies & config
├── sample_problems/               # 📂 Example input files
├── image_contest_runs/           # 📂 Image processing outputs
└── README.md                     # 📖 This documentation
```

## 🚀 Quick Start

### Step 1: Clone the Repository

```powershell
git clone https://github.com/THATSMEPS/ATF-MCP-HUB.git
cd ATF-MCP-HUB
```

### Step 2: Check Python Version

Make sure you have Python 3.13 or higher installed:

```powershell
python --version
```

If you need to install Python, download it from [python.org](https://python.org/downloads/).

### Step 3: Create a Virtual Environment

**Why use a virtual environment?** It keeps your project dependencies isolated from other Python projects on your system.

```powershell
# Create virtual environment
python -m venv .venv

# Activate it (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# If you get execution policy errors, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

You should see `(.venv)` at the beginning of your command prompt when activated.

### Step 4: Install Dependencies

This project uses `pyproject.toml` instead of `requirements.txt` for modern Python dependency management:

```powershell
# Install the project and all dependencies
pip install -e .
```

**Alternative method** if the above doesn't work:
```powershell
# Install dependencies directly
pip install fastmcp mysql-connector-python pymongo requests opencv-python numpy matplotlib pillow scikit-image playwright
```

## 🏃‍♂️ Running the Tools

### Method 1: Start All MCP Servers (Recommended)

```powershell
# Make sure your virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Start the main server
python main_mcp.py
```

This will start all MCP tools and display URLs like:
```
🚀 ATF Tools Main Server running at: http://127.0.0.1:8000/tools/mcp
🐳 Docker tools: http://127.0.0.1:8000/tools/docker
📦 Dependencies tools: http://127.0.0.1:8000/tools/dependencies
🔄 Git tools: http://127.0.0.1:8000/tools/git_clone
... and more
```

### Method 2: Run Individual Tools

You can also run individual MCP servers separately:

```powershell
# Run just the Docker tools
python docker_mcp.py

# Run just the image processing tools  
python image_processing_mcp.py

# Run just the database tools
python mysql_query_mcp.py
```

## 🔍 Using MCP Inspector

MCP Inspector is a web-based tool for testing and debugging your MCP servers.

### Option 1: Online Inspector

1. Go to [MCP Inspector](https://mcp-inspector.vercel.app/) in your browser
2. Enter your server URL: `http://127.0.0.1:8000/tools/mcp`
3. Click "Connect" to start testing your tools

### Option 2: Local Inspector

```powershell
# Install MCP Inspector globally (requires Node.js)
npm install -g @modelcontextprotocol/inspector

# Run inspector (with your server running)
mcp-inspector
```

### Option 3: Manual Testing

You can test endpoints directly in your browser or with tools like Postman:

- Main server: http://127.0.0.1:8000/tools/mcp
- Docker tools: http://127.0.0.1:8000/tools/docker  
- Dependencies: http://127.0.0.1:8000/tools/dependencies
- All other tools follow the same pattern

## 🧪 Testing Your Setup

### Quick Health Check

```powershell
# Test if Python can import the modules
python -c "import docker_mcp; print('✅ Docker MCP loaded')"
python -c "import dependencies_mcp; print('✅ Dependencies MCP loaded')"
python -c "import main_mcp; print('✅ Main server ready')"
```

### Manual Testing

Once your server is running, visit these URLs in your browser:
- **Main Dashboard**: http://127.0.0.1:8000/tools/mcp
- **Individual Tools**: http://127.0.0.1:8000/tools/[tool-name]

### Automated Testing

Add test scripts using Python's testing frameworks:

```powershell
# Install testing tools
pip install pytest

# Create and run tests
pytest tests/
```

## 🐛 Troubleshooting

### Common Issues and Solutions

**Problem**: `ModuleNotFoundError` when running servers
```powershell
# Solution: Make sure virtual environment is activated and dependencies installed
.\.venv\Scripts\Activate.ps1
pip install -e .
```

**Problem**: Port 8000 already in use
```powershell
# Solution: Find and kill the process using port 8000
netstat -ano | findstr :8000
# Then kill the process ID shown
taskkill /PID <process_id> /F
```

**Problem**: PowerShell execution policy errors
```powershell
# Solution: Set execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Problem**: `pip install -e .` fails
```powershell
# Solution: Install dependencies manually
pip install fastmcp mysql-connector-python pymongo requests opencv-python numpy matplotlib pillow scikit-image playwright
```

### Development and Debugging

#### Using Python's Inspector

```python
# Add this to any MCP file for debugging
import inspect

# See all functions in a module
print(inspect.getmembers(docker_mcp))

# Get function signature  
print(inspect.signature(some_function))

# Debug with VS Code
import pdb; pdb.set_trace()  # Add breakpoint
```

#### Checking Server Status

```powershell
# Check if servers are responding
curl http://127.0.0.1:8000/tools/mcp
# or in Python
python -c "import requests; print(requests.get('http://127.0.0.1:8000/tools/mcp').status_code)"
```

## 🔧 Customization and Extension

### Adding New MCP Tools

1. **Create a new MCP file**: `my_tool_mcp.py`
2. **Follow the pattern** from existing tools:
   ```python
   from fastmcp import FastMCP
   
   my_tool_mcp = FastMCP(name="My Tool")
   
   @my_tool_mcp.tool()
   def my_function():
       """Description of what this tool does"""
       return "Result"
   ```
3. **Add to main server** in `main_mcp.py`:
   ```python
   from my_tool_mcp import my_tool_mcp
   main_mcp.mount("my_tool", my_tool_mcp)
   ```

### Modifying Existing Tools

All MCP tools are in separate files, making them easy to modify:
- Docker operations: `docker_mcp.py`
- Package management: `dependencies_mcp.py`
- Database queries: `mysql_query_mcp.py` and `mongodb_mcp.py`
- Image processing: `image_processing_mcp.py`

## 📦 Dependencies Overview

This project uses modern Python packaging with `pyproject.toml`. Key dependencies include:

### Core MCP Framework
- `fastmcp>=2.8.1` - FastMCP framework for building MCP servers

### Database Connectors  
- `mysql-connector-python>=9.3.0` - MySQL database connectivity
- `pymongo>=4.13.2` - MongoDB database connectivity

### Image Processing
- `opencv-python` - Computer vision and image processing
- `numpy` - Numerical computing
- `matplotlib` - Plotting and visualization
- `pillow` - Image manipulation
- `scikit-image` - Advanced image processing

### Web and Automation
- `requests>=2.32.4` - HTTP requests
- `playwright` - Web automation and testing

### Development Tools
All tools run in containerized environments for safety and isolation.

## 🎯 Use Cases

### For Developers
- **Automated Testing**: Use Docker MCP to run tests in clean environments
- **Dependency Management**: Analyze and manage project dependencies
- **Database Operations**: Query and manage databases without manual setup
- **Image Processing**: Process screenshots, logos, and graphics programmatically

### For AI Integration
- **MCP Client**: Connect AI assistants to real development tools
- **Safe Execution**: All operations run in isolated containers
- **Standardized Interface**: Consistent API across all tools

### For Teams
- **Shared Tools**: Centralized development utilities
- **Consistent Environment**: Same tools across different machines
- **Easy Extension**: Add custom tools following established patterns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-tool`
3. Add your MCP tool following existing patterns
4. Test thoroughly with MCP Inspector
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/THATSMEPS/ATF-MCP-HUB/issues)
- **Discussions**: [GitHub Discussions](https://github.com/THATSMEPS/ATF-MCP-HUB/discussions)
- **Documentation**: Check `all_mcp_servers_overview.md` for detailed tool documentation

---

**🌟 Star this repo if you find it useful!**

*Made with ❤️ by the ATF community*
