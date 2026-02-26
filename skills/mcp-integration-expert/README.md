# MCP Integration Expert

**Expert guidance for researching, documenting, and integrating Model Context Protocol (MCP) servers and tools.**

## Overview

The **MCP Integration Expert** skill provides comprehensive knowledge for working with the Model Context Protocol (MCP), an open standard introduced by Anthropic in November 2024 that standardizes how AI applications and Large Language Models (LLMs) integrate with external data sources, tools, and systems.

Think of MCP as a "USB-C port for AI" - providing a universal, standardized interface for connecting AI models to diverse data sources and tools.

## What You'll Learn

This skill covers:

- **MCP Architecture**: Understanding the client-server model and protocol primitives
- **Server Implementation**: Building custom MCP servers in Python, TypeScript, C#, Java, and Rust
- **Client Integration**: Connecting MCP clients to servers and calling tools
- **Claude Code Integration**: Configuring and using MCP servers in Claude Code
- **LLM Integration**: Integrating MCP with OpenAI, Azure OpenAI, and other LLMs
- **Security Best Practices**: Implementing authentication, validation, and rate limiting
- **Advanced Patterns**: Chain of tools, parallel execution, context-aware selection
- **Research Workflow**: Using Context7 to research MCP documentation and examples
- **Troubleshooting**: Diagnosing and fixing common MCP integration issues

## Quick Start

### 1. Install MCP SDK

**Python**:
```bash
pip install modelcontextprotocol
pip install fastmcp  # For easier server creation
```

**TypeScript**:
```bash
npm install @modelcontextprotocol/sdk
```

**C#**:
```bash
dotnet add package ModelContextProtocol
```

### 2. Create Your First MCP Server

**Python (FastMCP)**:
```python
from fastmcp import FastMCP
from fastmcp.transports.stdio import serve_stdio
import asyncio

mcp = FastMCP("My First Server", version="1.0.0")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    asyncio.run(serve_stdio(mcp))
```

**TypeScript**:
```typescript
import { FastMCP } from '@modelcontextprotocol/typescript-sdk';
import { serve_stdio } from '@modelcontextprotocol/typescript-sdk/transports/stdio';

const mcp = new FastMCP({
    name: "My First Server",
    version: "1.0.0"
});

mcp.tool("greet", {
    description: "Greet someone by name",
    parameters: {
        name: { type: "string", required: true }
    }
}, async (params) => {
    return `Hello, ${params.name}!`;
});

serve_stdio(mcp);
```

### 3. Configure in Claude Code

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "my-first-server": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

Restart Claude Code, and your tools will be available!

## MCP Core Concepts

### Three Core Primitives

1. **Resources**: Expose data sources (files, databases, APIs)
   ```python
   @mcp.resource("docs://{path}")
   def get_doc(path: str) -> str:
       return read_documentation(path)
   ```

2. **Tools**: Enable actions and operations
   ```python
   @mcp.tool()
   def calculate(operation: str, a: float, b: float) -> float:
       return perform_calculation(operation, a, b)
   ```

3. **Prompts**: Provide reusable prompt templates
   ```python
   @mcp.prompt("code-review")
   def code_review_prompt(language: str, code: str):
       return f"Review this {language} code:\n{code}"
   ```

### Client-Server Architecture

```
┌─────────────────┐
│   MCP Client    │  (Claude Code, ChatGPT, Custom App)
│  (AI App/LLM)   │
└────────┬────────┘
         │ MCP Protocol (stdio, HTTP/SSE)
         │
┌────────┴────────┐
│   MCP Server    │  (Linear, GitHub, Custom Server)
│  (Tools/Data)   │
└─────────────────┘
```

## Popular MCP Servers (2025)

**Official MCP Servers** (https://github.com/modelcontextprotocol):
- **Linear**: Project management and issue tracking
- **GitHub**: Repository management and automation
- **Playwright**: Browser automation and visual testing
- **Postgres**: Database queries and operations
- **Google Drive**: File storage and retrieval
- **Slack**: Team communication
- **Stripe**: Payment processing
- **Puppeteer**: Web scraping

**Claude Code Built-in**:
- **Context7**: Library documentation retrieval
- **Linear**: Project management (pre-configured)
- **Playwright**: Browser automation (pre-configured)

## Real-World Use Cases

### 1. Development Workflow Automation

```json
{
  "mcpServers": {
    "linear": { "command": "npx", "args": ["-y", "@linear/mcp-server"] },
    "github": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"] },
    "playwright": { "command": "npx", "args": ["-y", "@playwright/mcp-server"] }
  }
}
```

**Workflow**: "Create a Linear issue, generate code, commit to GitHub, run tests with Playwright"

### 2. Internal Documentation Access

Create a custom MCP server to access your company's internal documentation:

```python
@mcp.resource("internal-docs://{path}")
def get_internal_doc(path: str) -> str:
    return read_from_confluence(path)

@mcp.tool()
def search_docs(query: str) -> list:
    return search_internal_knowledge_base(query)
```

### 3. Database Operations

```python
@mcp.tool()
def run_query(sql: str) -> dict:
    """Execute a read-only SQL query"""
    # Validate query is SELECT only
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries allowed")

    return execute_query(sql)
```

## Security & Best Practices

### 1. Input Validation

Always validate and sanitize inputs:
```python
@mcp.tool()
def read_file(filepath: str) -> str:
    import os
    filepath = os.path.normpath(filepath)

    # Prevent path traversal
    allowed_dir = "/safe/directory"
    if not filepath.startswith(allowed_dir):
        raise ValueError("Access denied")

    return open(filepath).read()
```

### 2. Authentication

Protect your MCP servers:
```python
@mcp.middleware
async def authenticate(request, call_next):
    api_key = request.headers.get("X-API-Key")
    if api_key != os.getenv("MCP_API_KEY"):
        raise PermissionError("Invalid API key")
    return await call_next(request)
```

### 3. Error Handling

Return structured errors:
```python
@mcp.tool()
def safe_operation(param: str) -> dict:
    try:
        result = perform_operation(param)
        return {"success": True, "data": result}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
```

## Research Workflow with Context7

When building MCP integrations, use Context7 to research:

```bash
# 1. Find MCP documentation
/ctx7 model context protocol

# 2. Research specific SDK
/ctx7 modelcontextprotocol python-sdk

# 3. Find examples
/ctx7 mcp-for-beginners
```

**Top Context7 Sources**:
- **microsoft/mcp-for-beginners** (Trust: 9.9, 30K+ snippets)
- **modelcontextprotocol/python-sdk** (Trust: 7.8)
- **modelcontextprotocol/typescript-sdk** (Trust: 7.8)

## Major Platform Adoptions (2025)

- **OpenAI** (March 2025): MCP in ChatGPT Desktop, Agents SDK
- **Google** (April 2025): MCP in Gemini models, Data Commons server
- **Microsoft** (2025): MCP in Copilot Studio, Azure OpenAI
- **Anthropic**: Native MCP in Claude Code

## File Structure

```
mcp-integration-expert/
├── SKILL.md           # Complete skill documentation (this file)
├── README.md          # Quick start and overview
└── EXAMPLES.md        # Detailed code examples
```

## Next Steps

1. **Read SKILL.md**: Comprehensive guide to MCP integration
2. **Try Examples**: See EXAMPLES.md for practical implementations
3. **Build Your Server**: Start with a simple tool, expand gradually
4. **Configure Claude Code**: Add your server to `claude_desktop_config.json`
5. **Research**: Use `/ctx7` to explore MCP documentation

## Resources

**Official Documentation**:
- MCP Specification: https://modelcontextprotocol.io/specification
- MCP GitHub: https://github.com/modelcontextprotocol
- Anthropic MCP Announcement: https://www.anthropic.com/news/model-context-protocol

**Learning**:
- Microsoft MCP for Beginners: https://github.com/microsoft/mcp-for-beginners
- MCP Server Examples: https://github.com/modelcontextprotocol (servers directory)

**SDKs**:
- Python: https://github.com/modelcontextprotocol/python-sdk
- TypeScript: https://github.com/modelcontextprotocol/typescript-sdk
- C#: https://github.com/modelcontextprotocol/csharp-sdk
- Java: https://github.com/modelcontextprotocol/java-sdk

## Support

For issues or questions:
- Check SKILL.md troubleshooting section
- Review EXAMPLES.md for reference implementations
- Consult official MCP documentation
- Use Context7 for latest research: `/ctx7 model context protocol`

---

**Skill Version**: 1.0.0
**Last Updated**: 2025-10-18
**Maintained By**: MCP Integration Expert Skill
