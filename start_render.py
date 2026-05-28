"""
Render.com startup script.
Spusti MCP server v streamable-http mode.
Render pouziva PORT env variable.
"""
import os
import sys

# Nastav transport na HTTP
os.environ["MCP_TRANSPORT"] = "streamable-http"

# Render.com prideluje PORT dynamicky
port = os.environ.get("PORT", "10000")
os.environ["MCP_PORT"] = port

# Spusti MCP server
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.join(os.path.dirname(__file__), "mcp_server"))

exec(open("server.py").read())