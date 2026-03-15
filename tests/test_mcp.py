import pytest
from mcp.server import Server


def test_mcp_server_instantiation():
    """Verify MCP server can be created."""
    from mcp.server import Server
    server = Server("sentinelnet-test")
    assert server is not None
