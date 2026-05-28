"""
Render.com startup script.
Spusti MCP server v streamable-http mode na PORT z env.
"""
import os
import sys
from pathlib import Path

# Nastav environment
os.environ["MCP_TRANSPORT"] = "streamable-http"
port = os.environ.get("PORT", "10000")
os.environ["MCP_PORT"] = port

# Pridaj mcp_server do Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp_server"))

# Import MCP server a spustenie
from server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))