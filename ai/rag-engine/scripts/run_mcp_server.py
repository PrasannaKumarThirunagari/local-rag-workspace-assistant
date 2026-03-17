"""Run the RAG MCP server (stdio transport for Cursor/IDE integration)."""
import sys
from pathlib import Path

# Ensure project root is on path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))

from ai_rag.mcp_server.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
