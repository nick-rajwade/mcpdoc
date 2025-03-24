"""MCP Llms-txt server for docs."""

from urllib.parse import urlparse

import httpx
from markdownify import markdownify
from mcp.server.fastmcp import FastMCP
from typing_extensions import NotRequired, TypedDict


class DocSource(TypedDict):
    """A source of documentation for a library or a package."""

    name: NotRequired[str]
    """Name of the documentation source (optional)."""

    llms_txt: str
    """URL to the llms.txt file or documentation source."""

    description: NotRequired[str]
    """Description of the documentation source (optional)."""


def extract_domain(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: Full URL

    Returns:
        Domain with scheme and trailing slash (e.g., https://example.com/)
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def create_server(
    doc_source: list[DocSource],
    *,
    follow_redirects: bool = False,
    timeout: float = 10,
    settings: dict | None = None,
    allowed_domains: list[str] | None = None,
) -> FastMCP:
    """Create the server and generate documentation retrieval tools.

    Args:
        doc_source: List of documentation sources to make available
        follow_redirects: Whether to follow HTTP redirects when fetching docs
        timeout: HTTP request timeout in seconds
        settings: Additional settings to pass to FastMCP
        allowed_domains: Additional domains to allow fetching from.
            Use ['*'] to allow all domains
            The domain hosting the llms.txt file is always appended to the list
            of allowed domains.

    Returns:
        A FastMCP server instance configured with documentation tools
    """
    server = FastMCP(
        name="llms-txt",
        instructions=(
            "Use the list doc sources tool to see available documentation "
            "sources. Once you have a source, use fetch docs to get the "
            "documentation"
        ),
        **settings,
    )
    httpx_client = httpx.AsyncClient(follow_redirects=follow_redirects, timeout=timeout)

    @server.tool()
    def list_doc_sources() -> str:
        """List all available documentation sources.

        This is the first tool you should call in the documentation workflow.
        It provides URLs to llms.txt files that the user has made available.

        Returns:
            A string containing a formatted list of documentation sources with their URLs
        """
        content = ""
        for entry in doc_source:
            name = entry.get("name", "") or extract_domain(entry["llms_txt"])
            content += f"{name}\n"
            content += "URL: " + entry["llms_txt"] + "\n\n"
        return content

    # Parse the domain names in the llms.txt URLs
    domains = set(extract_domain(entry["llms_txt"]) for entry in doc_source)

    # Add additional allowed domains if specified
    if allowed_domains:
        if "*" in allowed_domains:
            domains = {"*"}  # Special marker for allowing all domains
        else:
            domains.update(allowed_domains)

    @server.tool()
    async def fetch_docs(url: str) -> str:
        """Fetch and parse documentation from a given URL.

        Use this tool after list_doc_sources to:
        1. First fetch the llms.txt file from a documentation source
        2. Analyze the URLs listed in the llms.txt file
        3. Then fetch specific documentation pages relevant to the user's question

        Args:
            url: The URL to fetch documentation from. Must be from an allowed domain.

        Returns:
            The fetched documentation content converted to markdown, or an error message
            if the request fails or the URL is not from an allowed domain.
        """
        nonlocal domains
        if "*" not in domains and not any(url.startswith(domain) for domain in domains):
            return (
                "Error: URL not allowed. Must start with one of the following domains: "
                + ", ".join(domains)
            )

        try:
            response = await httpx_client.get(url, timeout=timeout)
            response.raise_for_status()
            return markdownify(response.text)
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            return f"Encountered an HTTP error with code {e.response.status_code}"

    return server
