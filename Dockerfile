# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Install uv (Python package/dependency manager)
RUN pip install --upgrade pip && pip install uv

# Set workdir
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies using uv
RUN uv pip install --system --no-cache-dir .

# Expose the port the MCP server will run on
EXPOSE 8082

# Default command to start the MCP server
CMD ["uvx", "--from", "mcpdoc", "mcpdoc", "--urls", "LangGraph:https://langchain-ai.github.io/langgraph/llms.txt", "LangChain:https://python.langchain.com/llms.txt", "Docker:https://docs.docker.com/llms.txt", "LangFlow:https://www.langflow.org/.well-known/llms.txt", "HandBook:https://handbook.exemplar.dev/llms-full.txt", "--transport", "sse", "--port", "8082", "--host", "0.0.0.0"]
