"""
NaraTask AI - Web Scraping Tool
Fetch and extract content from web pages.
"""

import httpx
from bs4 import BeautifulSoup
from .registry import registry


@registry.tool(
    name="web_scrape",
    description="Ambil dan ekstrak konten teks dari halaman web. Berguna untuk membaca artikel atau dokumentasi.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL halaman web yang akan di-scrape"
            },
            "max_chars": {
                "type": "integer",
                "description": "Maksimal karakter yang dikembalikan (default: 5000)",
                "default": 5000
            }
        },
        "required": ["url"]
    }
)
async def web_scrape(url: str, max_chars: int = 5000) -> str:
    """
    Scrape content from a web page.

    Args:
        url: URL to scrape
        max_chars: Maximum characters to return

    Returns:
        Extracted text content
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NaraTaskAI/1.0)"
            }
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "lxml")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get text content
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        # Truncate if too long
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[... konten dipotong, total {len(text)} karakter]"

        return f"Konten dari {url}:\n\n{text}"

    except httpx.HTTPStatusError as e:
        return f"Error HTTP {e.response.status_code}: Gagal mengakses {url}"
    except Exception as e:
        return f"Error saat scraping: {str(e)}"


@registry.tool(
    name="web_extract_links",
    description="Ekstrak semua link dari halaman web.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL halaman web"
            },
            "filter_text": {
                "type": "string",
                "description": "Filter link yang mengandung teks tertentu (opsional)"
            }
        },
        "required": ["url"]
    }
)
async def web_extract_links(url: str, filter_text: str = None) -> str:
    """
    Extract links from a web page.

    Args:
        url: URL to extract links from
        filter_text: Optional text filter for links

    Returns:
        List of links
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True)

            # Apply filter if specified
            if filter_text and filter_text.lower() not in text.lower():
                continue

            # Make relative URLs absolute
            if href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(url, href)

            if href.startswith("http"):
                links.append({"url": href, "text": text or "[No text]"})

        if not links:
            return f"Tidak ditemukan link di {url}" + (f" dengan filter '{filter_text}'" if filter_text else "")

        formatted = f"Link dari {url}:\n\n"
        for i, link in enumerate(links[:50], 1):  # Limit to 50 links
            formatted += f"{i}. {link['text']}\n   {link['url']}\n"

        if len(links) > 50:
            formatted += f"\n... dan {len(links) - 50} link lainnya"

        return formatted

    except Exception as e:
        return f"Error saat ekstrak link: {str(e)}"