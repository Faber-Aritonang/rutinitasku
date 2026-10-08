"""
Tests for Web Search and Web Scrape Tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest.mock import MagicMock

from tools.registry import ToolRegistry


@pytest.fixture
def registry():
    """Create fresh registry for testing."""
    return ToolRegistry()


def test_web_search_registered():
    """Test web_search tool is registered."""
    from tools.web_search import web_search
    from tools.registry import registry

    assert registry.has_tool("web_search")
    assert registry.has_tool("web_news")


def test_web_scrape_registered():
    """Test web_scrape tool is registered."""
    from tools.web_scrape import web_scrape
    from tools.registry import registry

    assert registry.has_tool("web_scrape")
    assert registry.has_tool("web_extract_links")


def test_web_search_tool_definition():
    """Test web_search tool definition format."""
    from tools.registry import registry

    definitions = registry.get_tool_definitions()
    web_search_def = next((d for d in definitions if d["name"] == "web_search"), None)

    assert web_search_def is not None
    assert "query" in web_search_def["input_schema"]["properties"]
    assert "query" in web_search_def["input_schema"]["required"]


@pytest.mark.asyncio
async def test_web_scrape_mock():
    """Test web scraping with mocked HTTP response."""
    from tools.web_scrape import web_scrape

    mock_response = MagicMock()
    mock_response.text = "<html><body><h1>Test Page</h1><p>Content here</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("tools.web_scrape.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client

        result = await web_scrape("https://example.com")
        assert "Test Page" in result or "example.com" in result