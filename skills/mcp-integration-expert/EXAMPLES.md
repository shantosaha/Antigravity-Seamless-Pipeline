# MCP Integration Examples

Comprehensive collection of practical MCP integration examples across multiple languages and use cases.

## Table of Contents

1. [Basic MCP Servers](#basic-mcp-servers)
2. [Advanced MCP Servers](#advanced-mcp-servers)
3. [MCP Clients](#mcp-clients)
4. [LLM Integration](#llm-integration)
5. [Real-World Use Cases](#real-world-use-cases)
6. [Testing](#testing)
7. [Security Patterns](#security-patterns)
8. [Advanced Workflows](#advanced-workflows)

---

## Basic MCP Servers

### Example 1: Simple Weather Server (Python)

```python
#!/usr/bin/env python3
"""
Simple weather MCP server demonstrating basic tool implementation.
"""
from fastmcp import FastMCP
from fastmcp.transports.stdio import serve_stdio
import asyncio
from typing import Dict

mcp = FastMCP(
    name="Weather MCP Server",
    version="1.0.0"
)

@mcp.tool()
def get_weather(location: str) -> Dict:
    """
    Gets current weather for a location.

    Args:
        location: City name or coordinates

    Returns:
        Weather data dictionary
    """
    # In production, this would call a real weather API
    return {
        "temperature": 72.5,
        "conditions": "Sunny",
        "location": location,
        "humidity": 45,
        "wind_speed": 8.5
    }

@mcp.tool()
def get_forecast(location: str, days: int = 3) -> Dict:
    """
    Gets weather forecast for multiple days.

    Args:
        location: City name
        days: Number of days to forecast (1-7)

    Returns:
        Forecast data dictionary
    """
    if days < 1 or days > 7:
        raise ValueError("Days must be between 1 and 7")

    forecast = []
    for i in range(days):
        forecast.append({
            "day": i + 1,
            "temperature": 70 + i * 2,
            "conditions": "Partly Cloudy" if i % 2 == 0 else "Sunny"
        })

    return {
        "location": location,
        "forecast": forecast
    }

if __name__ == "__main__":
    asyncio.run(serve_stdio(mcp))
```

**Usage in Claude Code**:
```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/path/to/weather_server.py"]
    }
  }
}
```

### Example 2: Simple Calculator Server (TypeScript)

```typescript
/**
 * Simple calculator MCP server demonstrating TypeScript implementation.
 */
import { FastMCP } from '@modelcontextprotocol/typescript-sdk';
import { serve_stdio } from '@modelcontextprotocol/typescript-sdk/transports/stdio';

const mcp = new FastMCP({
    name: "Calculator MCP Server",
    version: "1.0.0"
});

mcp.tool("add", {
    description: "Add two numbers",
    parameters: {
        a: { type: "number", required: true, description: "First number" },
        b: { type: "number", required: true, description: "Second number" }
    }
}, async (params) => {
    return {
        operation: "addition",
        result: params.a + params.b,
        expression: `${params.a} + ${params.b} = ${params.a + params.b}`
    };
});

mcp.tool("multiply", {
    description: "Multiply two numbers",
    parameters: {
        a: { type: "number", required: true },
        b: { type: "number", required: true }
    }
}, async (params) => {
    return {
        operation: "multiplication",
        result: params.a * params.b,
        expression: `${params.a} × ${params.b} = ${params.a * params.b}`
    };
});

mcp.tool("calculate", {
    description: "Evaluate a mathematical expression",
    parameters: {
        expression: { type: "string", required: true }
    }
}, async (params) => {
    try {
        // Security: Use a safe eval method in production
        const result = eval(params.expression);
        return {
            expression: params.expression,
            result: result
        };
    } catch (error) {
        return {
            error: "Invalid expression",
            message: error.message
        };
    }
});

serve_stdio(mcp);
```

### Example 3: File System Server (Java)

```java
/**
 * File system MCP server demonstrating Java implementation.
 */
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpToolDefinition;
import io.modelcontextprotocol.server.transport.StdioServerTransport;
import io.modelcontextprotocol.server.tool.ToolExecutionContext;
import io.modelcontextprotocol.server.tool.ToolResponse;
import java.nio.file.*;
import java.io.IOException;
import java.util.stream.Collectors;

public class FileSystemMcpServer {
    private static final String SAFE_DIRECTORY = "/safe/workspace";

    public static void main(String[] args) throws Exception {
        McpServer server = McpServer.builder()
            .name("FileSystem MCP Server")
            .version("1.0.0")
            .build();

        // List files in directory
        server.registerTool(McpToolDefinition.builder("listFiles")
            .description("List files in a directory")
            .parameter("path", String.class)
            .execute((ToolExecutionContext ctx) -> {
                String path = ctx.getParameter("path", String.class);
                Path dirPath = validatePath(path);

                try {
                    String files = Files.list(dirPath)
                        .map(Path::getFileName)
                        .map(Path::toString)
                        .collect(Collectors.joining("\n"));

                    return ToolResponse.content(files);
                } catch (IOException e) {
                    return ToolResponse.error("Failed to list files: " + e.getMessage());
                }
            })
            .build());

        // Read file
        server.registerTool(McpToolDefinition.builder("readFile")
            .description("Read contents of a file")
            .parameter("filepath", String.class)
            .execute((ToolExecutionContext ctx) -> {
                String filepath = ctx.getParameter("filepath", String.class);
                Path filePath = validatePath(filepath);

                try {
                    String content = Files.readString(filePath);
                    return ToolResponse.content(content);
                } catch (IOException e) {
                    return ToolResponse.error("Failed to read file: " + e.getMessage());
                }
            })
            .build());

        try (StdioServerTransport transport = new StdioServerTransport()) {
            server.connect(transport);
            System.err.println("FileSystem MCP Server started");
            Thread.currentThread().join();
        }
    }

    private static Path validatePath(String path) throws SecurityException {
        Path normalized = Paths.get(SAFE_DIRECTORY, path).normalize();
        if (!normalized.startsWith(SAFE_DIRECTORY)) {
            throw new SecurityException("Access denied: Path outside safe directory");
        }
        return normalized;
    }
}
```

---

## Advanced MCP Servers

### Example 4: Database Query Server with Connection Pool (Python)

```python
"""
Advanced database MCP server with connection pooling and transactions.
"""
from fastmcp import FastMCP
from fastmcp.transports.stdio import serve_stdio
import asyncio
import asyncpg
from typing import Dict, List, Optional
import os

mcp = FastMCP("Database Server", version="1.0.0")

# Connection pool
pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            min_size=2,
            max_size=10
        )
    return pool

@mcp.tool()
async def query(sql: str, params: Optional[List] = None) -> Dict:
    """
    Execute a read-only SQL query.

    Args:
        sql: SELECT query to execute
        params: Query parameters (optional)

    Returns:
        Query results as list of dictionaries
    """
    # Security: Only allow SELECT
    if not sql.strip().upper().startswith("SELECT"):
        return {
            "error": "Only SELECT queries are allowed",
            "error_type": "security_violation"
        }

    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            rows = await connection.fetch(sql, *(params or []))
            return {
                "success": True,
                "rows": [dict(row) for row in rows],
                "count": len(rows)
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

@mcp.tool()
async def get_table_schema(table_name: str) -> Dict:
    """Get schema information for a table."""
    sql = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
    """

    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            rows = await connection.fetch(sql, table_name)
            return {
                "success": True,
                "table": table_name,
                "columns": [dict(row) for row in rows]
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
async def execute_transaction(queries: List[Dict]) -> Dict:
    """
    Execute multiple queries in a transaction.

    Args:
        queries: List of {sql, params} dictionaries

    Returns:
        Transaction results
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                results = []
                for query in queries:
                    sql = query["sql"]
                    params = query.get("params", [])
                    result = await connection.fetch(sql, *params)
                    results.append({
                        "sql": sql,
                        "affected_rows": len(result)
                    })

                return {
                    "success": True,
                    "results": results,
                    "committed": True
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rolled_back": True
        }

if __name__ == "__main__":
    asyncio.run(serve_stdio(mcp))
```

### Example 5: REST API Wrapper Server (TypeScript)

```typescript
/**
 * REST API wrapper MCP server with caching and rate limiting.
 */
import { FastMCP } from '@modelcontextprotocol/typescript-sdk';
import { serve_stdio } from '@modelcontextprotocol/typescript-sdk/transports/stdio';
import axios from 'axios';
import NodeCache from 'node-cache';
import rateLimit from 'express-rate-limit';

const mcp = new FastMCP({
    name: "API Wrapper Server",
    version: "1.0.0"
});

// Cache with 5-minute TTL
const cache = new NodeCache({ stdTTL: 300 });

// Rate limiter: 10 requests per minute
const rateLimiter = new Map();

function checkRateLimit(clientId: string): boolean {
    const now = Date.now();
    const clientRequests = rateLimiter.get(clientId) || [];

    // Remove requests older than 1 minute
    const recentRequests = clientRequests.filter(
        (time: number) => now - time < 60000
    );

    if (recentRequests.length >= 10) {
        return false;
    }

    recentRequests.push(now);
    rateLimiter.set(clientId, recentRequests);
    return true;
}

mcp.tool("fetchAPI", {
    description: "Fetch data from a REST API with caching",
    parameters: {
        url: { type: "string", required: true },
        method: { type: "string", required: false, default: "GET" },
        headers: { type: "object", required: false },
        body: { type: "object", required: false },
        useCache: { type: "boolean", required: false, default: true }
    }
}, async (params, context) => {
    const clientId = context.clientId || "default";

    // Check rate limit
    if (!checkRateLimit(clientId)) {
        return {
            success: false,
            error: "Rate limit exceeded",
            retryAfter: 60
        };
    }

    // Security: Only allow HTTPS
    if (!params.url.startsWith("https://")) {
        return {
            success: false,
            error: "Only HTTPS URLs are allowed"
        };
    }

    const cacheKey = `${params.method}:${params.url}`;

    // Check cache
    if (params.useCache) {
        const cached = cache.get(cacheKey);
        if (cached) {
            return {
                success: true,
                data: cached,
                cached: true
            };
        }
    }

    try {
        const response = await axios({
            method: params.method,
            url: params.url,
            headers: params.headers,
            data: params.body,
            timeout: 5000
        });

        // Cache successful GET requests
        if (params.method === "GET" && params.useCache) {
            cache.set(cacheKey, response.data);
        }

        return {
            success: true,
            data: response.data,
            status: response.status,
            cached: false
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
            status: error.response?.status
        };
    }
});

serve_stdio(mcp);
```

---

## MCP Clients

### Example 6: Python MCP Client with Tool Discovery

```python
"""
Python MCP client demonstrating tool discovery and execution.
"""
from mcp.client import stdio_client, ClientSession
import asyncio
from typing import List, Dict

class MCPClientWrapper:
    def __init__(self, server_command: str, server_args: List[str]):
        self.server_params = {
            "command": server_command,
            "args": server_args
        }
        self.tools = []

    async def connect_and_discover(self):
        """Connect to server and discover available tools."""
        async with stdio_client(self.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()

                # Discover tools
                self.tools = await session.list_tools()
                print(f"Discovered {len(self.tools)} tools:")
                for tool in self.tools:
                    print(f"  - {tool.name}: {tool.description}")

                return session

    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call a tool by name with given arguments."""
        async with stdio_client(self.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()

                result = await session.call_tool(tool_name, arguments=arguments)
                return result

    async def run_workflow(self, workflow: List[Dict]):
        """
        Execute a workflow of tool calls.

        Args:
            workflow: List of {tool, args} dictionaries
        """
        results = []
        async with stdio_client(self.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()

                for step in workflow:
                    print(f"Executing: {step['tool']}")
                    result = await session.call_tool(
                        step["tool"],
                        arguments=step.get("args", {})
                    )
                    results.append({
                        "tool": step["tool"],
                        "result": result
                    })
                    print(f"  Result: {result}")

                return results

async def main():
    # Create client
    client = MCPClientWrapper("python", ["weather_server.py"])

    # Discover tools
    await client.connect_and_discover()

    # Call a single tool
    weather = await client.call_tool("get_weather", {"location": "Seattle"})
    print(f"\nWeather: {weather}")

    # Run a workflow
    workflow = [
        {"tool": "get_weather", "args": {"location": "Seattle"}},
        {"tool": "get_weather", "args": {"location": "Portland"}},
        {"tool": "get_forecast", "args": {"location": "Seattle", "days": 3}}
    ]
    results = await client.run_workflow(workflow)
    print(f"\nWorkflow results: {results}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 7: TypeScript MCP Client Class

```typescript
/**
 * TypeScript MCP client with comprehensive error handling.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";

interface ToolCall {
    name: string;
    arguments: any;
}

interface ToolResult {
    success: boolean;
    data?: any;
    error?: string;
}

class MCPClient {
    private client: Client;
    private transport: Transport | null = null;
    private connected: boolean = false;

    constructor() {
        this.client = new Client({
            name: "typescript-mcp-client",
            version: "1.0.0"
        }, {
            capabilities: {
                prompts: {},
                resources: {},
                tools: {}
            }
        });
    }

    async connect(serverCommand: string, serverArgs: string[]): Promise<void> {
        this.transport = new StdioClientTransport({
            command: serverCommand,
            args: serverArgs
        });

        await this.client.connect(this.transport);
        this.connected = true;
        console.log("Connected to MCP server");
    }

    async disconnect(): Promise<void> {
        if (this.transport) {
            await this.transport.close();
            this.connected = false;
            console.log("Disconnected from MCP server");
        }
    }

    async listTools(): Promise<any[]> {
        if (!this.connected) {
            throw new Error("Client not connected");
        }

        const tools = await this.client.listTools();
        return tools;
    }

    async callTool(toolCall: ToolCall): Promise<ToolResult> {
        if (!this.connected) {
            throw new Error("Client not connected");
        }

        try {
            const result = await this.client.callTool({
                name: toolCall.name,
                arguments: toolCall.arguments
            });

            return {
                success: true,
                data: result
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async executeParallel(toolCalls: ToolCall[]): Promise<ToolResult[]> {
        const promises = toolCalls.map(call => this.callTool(call));
        return await Promise.all(promises);
    }

    async executeSequential(toolCalls: ToolCall[]): Promise<ToolResult[]> {
        const results: ToolResult[] = [];

        for (const call of toolCalls) {
            const result = await this.callTool(call);
            results.push(result);

            // Stop on first error
            if (!result.success) {
                break;
            }
        }

        return results;
    }
}

// Usage
async function main() {
    const client = new MCPClient();

    try {
        await client.connect("python", ["weather_server.py"]);

        const tools = await client.listTools();
        console.log("Available tools:", tools);

        const result = await client.callTool({
            name: "get_weather",
            arguments: { location: "Seattle" }
        });
        console.log("Result:", result);

    } finally {
        await client.disconnect();
    }
}
```

---

## LLM Integration

### Example 8: OpenAI + MCP Integration (TypeScript)

```typescript
/**
 * Complete OpenAI + MCP integration demonstrating full workflow.
 */
import OpenAI from "openai";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { z } from "zod";

class OpenAIMCPIntegration {
    private openai: OpenAI;
    private mcpClient: Client;
    private chatHistory: OpenAI.Chat.ChatCompletionMessageParam[] = [];

    constructor(openaiApiKey: string) {
        this.openai = new OpenAI({ apiKey: openaiApiKey });

        this.mcpClient = new Client({
            name: "openai-mcp-client",
            version: "1.0.0"
        }, {
            capabilities: { tools: {} }
        });
    }

    async connectToMCPServer(command: string, args: string[]) {
        const transport = new StdioClientTransport({ command, args });
        await this.mcpClient.connect(transport);
    }

    mcpToolToOpenAITool(tool: any): OpenAI.Chat.ChatCompletionTool {
        return {
            type: "function" as const,
            function: {
                name: tool.name,
                description: tool.description,
                parameters: {
                    type: "object",
                    properties: tool.input_schema.properties,
                    required: tool.input_schema.required || [],
                },
            },
        };
    }

    async processUserMessage(userMessage: string): Promise<string> {
        // Add user message to history
        this.chatHistory.push({
            role: "user",
            content: userMessage
        });

        // Get MCP tools and convert to OpenAI format
        const mcpTools = await this.mcpClient.listTools();
        const openaiTools = mcpTools.map(t => this.mcpToolToOpenAITool(t));

        // Call OpenAI
        let response = await this.openai.chat.completions.create({
            model: "gpt-4",
            messages: this.chatHistory,
            tools: openaiTools,
        });

        let assistantMessage = response.choices[0].message;

        // Handle tool calls
        while (assistantMessage.tool_calls) {
            // Add assistant message to history
            this.chatHistory.push(assistantMessage);

            // Execute all tool calls
            for (const toolCall of assistantMessage.tool_calls) {
                console.log(`Calling MCP tool: ${toolCall.function.name}`);

                const result = await this.mcpClient.callTool({
                    name: toolCall.function.name,
                    arguments: JSON.parse(toolCall.function.arguments),
                });

                // Add tool result to history
                this.chatHistory.push({
                    role: "tool",
                    tool_call_id: toolCall.id,
                    content: JSON.stringify(result)
                });
            }

            // Get next response from OpenAI
            response = await this.openai.chat.completions.create({
                model: "gpt-4",
                messages: this.chatHistory,
                tools: openaiTools,
            });

            assistantMessage = response.choices[0].message;
        }

        // Add final assistant message to history
        this.chatHistory.push(assistantMessage);

        return assistantMessage.content || "No response";
    }
}

// Usage
async function main() {
    const integration = new OpenAIMCPIntegration(process.env.OPENAI_API_KEY!);

    await integration.connectToMCPServer("python", ["weather_server.py"]);

    const response1 = await integration.processUserMessage(
        "What's the weather in Seattle?"
    );
    console.log("Assistant:", response1);

    const response2 = await integration.processUserMessage(
        "What about Portland?"
    );
    console.log("Assistant:", response2);
}

main();
```

### Example 9: Azure OpenAI + MCP Integration (C#)

```csharp
/**
 * Azure OpenAI + MCP integration in C#.
 */
using Azure.AI.Inference;
using Azure;
using ModelContextProtocol.Client;
using ModelContextProtocol.Protocol.Transport;
using System.Text.Json;

public class AzureOpenAIMCPIntegration
{
    private readonly ChatCompletionsClient azureClient;
    private readonly IClient mcpClient;
    private readonly List<ChatRequestMessage> chatHistory;

    public AzureOpenAIMCPIntegration(string endpoint, string token)
    {
        azureClient = new ChatCompletionsClient(
            new Uri(endpoint),
            new AzureKeyCredential(token)
        );

        chatHistory = new List<ChatRequestMessage>
        {
            new ChatRequestSystemMessage("You are a helpful assistant with access to tools.")
        };
    }

    public async Task ConnectToMCPServer(string command, string[] args)
    {
        var transport = new StdioClientTransport(new()
        {
            Name = "MCP Server",
            Command = command,
            Arguments = args
        });

        mcpClient = await McpClientFactory.CreateAsync(transport);
    }

    private ChatCompletionsToolDefinition ConvertMCPToAzureTool(
        string name,
        string description,
        JsonElement schema)
    {
        var functionDefinition = new FunctionDefinition(name)
        {
            Description = description,
            Parameters = BinaryData.FromObjectAsJson(new
            {
                Type = "object",
                Properties = schema
            })
        };

        return new ChatCompletionsToolDefinition(functionDefinition);
    }

    public async Task<string> ProcessUserMessage(string userMessage)
    {
        chatHistory.Add(new ChatRequestUserMessage(userMessage));

        // Get MCP tools
        var mcpTools = await mcpClient.ListToolsAsync();
        var toolDefinitions = new List<ChatCompletionsToolDefinition>();

        foreach (var tool in mcpTools)
        {
            JsonElement propertiesElement;
            tool.JsonSchema.TryGetProperty("properties", out propertiesElement);

            var toolDef = ConvertMCPToAzureTool(
                tool.Name,
                tool.Description,
                propertiesElement
            );
            toolDefinitions.Add(toolDef);
        }

        // Call Azure OpenAI
        var response = await azureClient.CompleteAsync(
            chatHistory,
            new ChatCompletionsOptions { Tools = toolDefinitions }
        );

        var choice = response.Value.Choices[0];

        // Handle tool calls
        while (choice.FinishReason == CompletionsFinishReason.ToolCalls)
        {
            chatHistory.Add(new ChatRequestAssistantMessage(choice.Message));

            foreach (var toolCall in choice.Message.ToolCalls)
            {
                Console.WriteLine($"Calling MCP tool: {toolCall.Name}");

                var args = JsonSerializer.Deserialize<Dictionary<string, object>>(
                    toolCall.Arguments
                );

                var result = await mcpClient.CallToolAsync(toolCall.Name, args);

                chatHistory.Add(new ChatRequestToolMessage(
                    JsonSerializer.Serialize(result),
                    toolCall.Id
                ));
            }

            response = await azureClient.CompleteAsync(
                chatHistory,
                new ChatCompletionsOptions { Tools = toolDefinitions }
            );

            choice = response.Value.Choices[0];
        }

        chatHistory.Add(new ChatRequestAssistantMessage(choice.Message.Content));
        return choice.Message.Content;
    }
}

// Usage
var integration = new AzureOpenAIMCPIntegration(
    "https://models.inference.ai.azure.com",
    Environment.GetEnvironmentVariable("GITHUB_TOKEN")
);

await integration.ConnectToMCPServer("python", new[] { "weather_server.py" });

var response = await integration.ProcessUserMessage("What's the weather in Seattle?");
Console.WriteLine($"Assistant: {response}");
```

---

## Real-World Use Cases

### Example 10: Internal Documentation Server

```python
"""
Internal documentation MCP server with search and access control.
"""
from fastmcp import FastMCP
from fastmcp.transports.stdio import serve_stdio
import asyncio
import os
from pathlib import Path
from typing import List, Dict
import whoosh
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser

mcp = FastMCP("Internal Docs Server", version="1.0.0")

DOCS_DIR = "/company/documentation"
INDEX_DIR = "/tmp/docs_index"

# Initialize search index
schema = Schema(
    path=ID(stored=True),
    title=TEXT(stored=True),
    content=TEXT
)

@mcp.resource("docs://{path}")
def get_document(path: str) -> str:
    """
    Retrieve a document by path.

    Args:
        path: Relative path to document

    Returns:
        Document content
    """
    filepath = Path(DOCS_DIR) / path
    filepath = filepath.resolve()

    # Security: Ensure within DOCS_DIR
    if not str(filepath).startswith(DOCS_DIR):
        return "Error: Access denied"

    if not filepath.exists():
        return f"Error: Document not found: {path}"

    with open(filepath, 'r') as f:
        return f.read()

@mcp.tool()
def search_docs(query: str, limit: int = 10) -> List[Dict]:
    """
    Search documentation using full-text search.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of matching documents
    """
    try:
        ix = open_dir(INDEX_DIR)
        with ix.searcher() as searcher:
            query_parser = QueryParser("content", ix.schema)
            q = query_parser.parse(query)
            results = searcher.search(q, limit=limit)

            return [
                {
                    "path": result["path"],
                    "title": result["title"],
                    "score": result.score
                }
                for result in results
            ]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def list_categories() -> List[str]:
    """List all documentation categories."""
    categories = []
    for item in Path(DOCS_DIR).iterdir():
        if item.is_dir():
            categories.append(item.name)
    return sorted(categories)

@mcp.tool()
def get_toc(category: str) -> Dict:
    """
    Get table of contents for a category.

    Args:
        category: Documentation category

    Returns:
        Hierarchical table of contents
    """
    category_path = Path(DOCS_DIR) / category

    if not category_path.exists():
        return {"error": f"Category not found: {category}"}

    toc = {}
    for filepath in category_path.rglob("*.md"):
        relative = filepath.relative_to(category_path)
        toc[str(relative)] = {
            "path": str(filepath.relative_to(DOCS_DIR)),
            "size": filepath.stat().st_size,
            "modified": filepath.stat().st_mtime
        }

    return {"category": category, "documents": toc}

if __name__ == "__main__":
    asyncio.run(serve_stdio(mcp))
```

### Example 11: CI/CD Integration Server

```typescript
/**
 * CI/CD integration MCP server connecting GitHub, Linear, and deployment.
 */
import { FastMCP } from '@modelcontextprotocol/typescript-sdk';
import { serve_stdio } from '@modelcontextprotocol/typescript-sdk/transports/stdio';
import { Octokit } from '@octokit/rest';
import { LinearClient } from '@linear/sdk';
import axios from 'axios';

const mcp = new FastMCP({
    name: "CI/CD Integration Server",
    version: "1.0.0"
});

const github = new Octokit({ auth: process.env.GITHUB_TOKEN });
const linear = new LinearClient({ apiKey: process.env.LINEAR_API_KEY });

mcp.tool("createReleasePR", {
    description: "Create a release PR with Linear issue tracking",
    parameters: {
        owner: { type: "string", required: true },
        repo: { type: "string", required: true },
        version: { type: "string", required: true },
        changes: { type: "array", items: { type: "string" } }
    }
}, async (params) => {
    try {
        // 1. Create Linear issue for release
        const issue = await linear.issueCreate({
            teamId: process.env.LINEAR_TEAM_ID!,
            title: `Release ${params.version}`,
            description: `Release version ${params.version}\n\nChanges:\n${params.changes.join('\n')}`,
            labels: ["release"]
        });

        // 2. Create GitHub PR
        const pr = await github.pulls.create({
            owner: params.owner,
            repo: params.repo,
            title: `Release ${params.version}`,
            head: `release/${params.version}`,
            base: "main",
            body: `# Release ${params.version}\n\nLinear Issue: ${issue.issue?.url}\n\n## Changes\n${params.changes.map(c => `- ${c}`).join('\n')}`
        });

        // 3. Link PR to Linear issue
        await linear.attachmentCreate({
            issueId: issue.issue!.id,
            title: `PR #${pr.data.number}`,
            url: pr.data.html_url
        });

        return {
            success: true,
            pr: {
                number: pr.data.number,
                url: pr.data.html_url
            },
            linear_issue: {
                id: issue.issue!.id,
                url: issue.issue!.url
            }
        };
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
});

mcp.tool("deployToStaging", {
    description: "Deploy a version to staging environment",
    parameters: {
        version: { type: "string", required: true },
        environment: { type: "string", required: false, default: "staging" }
    }
}, async (params) => {
    try {
        // Trigger deployment webhook
        const response = await axios.post(
            process.env.DEPLOY_WEBHOOK_URL!,
            {
                version: params.version,
                environment: params.environment
            },
            {
                headers: {
                    'Authorization': `Bearer ${process.env.DEPLOY_TOKEN}`
                }
            }
        );

        return {
            success: true,
            deployment_id: response.data.id,
            status_url: response.data.status_url
        };
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
});

serve_stdio(mcp);
```

---

## Testing

### Example 12: MCP Server Integration Tests (Python)

```python
"""
Comprehensive integration tests for MCP server.
"""
import pytest
import asyncio
from mcp.server import McpServer
from mcp.client import McpClient
from unittest.mock import Mock, patch

@pytest.fixture
async def test_server():
    """Start a test MCP server."""
    server = McpServer()

    # Register test tools
    @server.tool("add")
    async def add(a: int, b: int) -> int:
        return a + b

    @server.tool("greet")
    async def greet(name: str) -> str:
        return f"Hello, {name}!"

    await server.start(port=5555)
    yield server
    await server.stop()

@pytest.fixture
async def test_client(test_server):
    """Create a test MCP client."""
    client = McpClient("http://localhost:5555")
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_tool_discovery(test_client):
    """Test tool discovery."""
    tools = await test_client.discover_tools()

    assert len(tools) == 2
    assert "add" in [t.name for t in tools]
    assert "greet" in [t.name for t in tools]

@pytest.mark.asyncio
async def test_tool_execution(test_client):
    """Test tool execution."""
    result = await test_client.execute_tool("add", {"a": 5, "b": 7})

    assert result.status_code == 200
    assert result.content[0].text == "12"

@pytest.mark.asyncio
async def test_tool_with_invalid_params(test_client):
    """Test tool with invalid parameters."""
    with pytest.raises(ValueError):
        await test_client.execute_tool("add", {"a": "not a number", "b": 7})

@pytest.mark.asyncio
async def test_parallel_tool_calls(test_client):
    """Test parallel tool execution."""
    tasks = [
        test_client.execute_tool("add", {"a": i, "b": i * 2})
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(r.status_code == 200 for r in results)

@pytest.mark.asyncio
async def test_tool_error_handling(test_client):
    """Test error handling."""
    with pytest.raises(Exception) as exc_info:
        await test_client.execute_tool("nonexistent_tool", {})

    assert "Tool not found" in str(exc_info.value)
```

---

## Security Patterns

### Example 13: Secure MCP Server with Authentication

```python
"""
MCP server with comprehensive security measures.
"""
from fastmcp import FastMCP
from fastmcp.transports.stdio import serve_stdio
import asyncio
import os
import hmac
import hashlib
from collections import defaultdict
import time
from typing import Dict, Optional
import re

mcp = FastMCP("Secure Server", version="1.0.0")

# Security configurations
API_KEY = os.getenv("MCP_API_KEY")
ALLOWED_PATHS = ["/safe/workspace", "/public/docs"]
RATE_LIMIT = 10  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Track requests for rate limiting
request_tracker: Dict[str, list] = defaultdict(list)

@mcp.middleware
async def authenticate(request, call_next):
    """Verify API key authentication."""
    provided_key = request.headers.get("X-API-Key")

    if not provided_key:
        raise PermissionError("API key required")

    # Constant-time comparison to prevent timing attacks
    expected_key = API_KEY.encode()
    provided_key_encoded = provided_key.encode()

    if not hmac.compare_digest(expected_key, provided_key_encoded):
        raise PermissionError("Invalid API key")

    return await call_next(request)

@mcp.middleware
async def rate_limit(request, call_next):
    """Enforce rate limiting per client."""
    client_id = request.client_id or "unknown"
    now = time.time()

    # Clean old requests
    request_tracker[client_id] = [
        req_time for req_time in request_tracker[client_id]
        if now - req_time < RATE_LIMIT_WINDOW
    ]

    # Check rate limit
    if len(request_tracker[client_id]) >= RATE_LIMIT:
        raise Exception(
            f"Rate limit exceeded. Max {RATE_LIMIT} requests per {RATE_LIMIT_WINDOW}s"
        )

    request_tracker[client_id].append(now)
    return await call_next(request)

def validate_path(filepath: str) -> str:
    """Validate and normalize file paths."""
    import os.path

    # Normalize path
    normalized = os.path.normpath(filepath)

    # Check if within allowed paths
    allowed = any(
        normalized.startswith(allowed_path)
        for allowed_path in ALLOWED_PATHS
    )

    if not allowed:
        raise SecurityError(f"Access denied: {filepath}")

    return normalized

def sanitize_input(value: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[^\w\s\-./]', '', value)
    return sanitized

@mcp.tool()
async def read_file(filepath: str) -> Dict:
    """
    Read a file with security validation.

    Args:
        filepath: Path to file

    Returns:
        File content or error
    """
    try:
        validated_path = validate_path(filepath)

        with open(validated_path, 'r') as f:
            content = f.read()

        return {
            "success": True,
            "content": content,
            "path": validated_path
        }

    except SecurityError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "security_violation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

@mcp.tool()
async def execute_query(query: str) -> Dict:
    """
    Execute a database query with security validation.

    Args:
        query: SQL query (SELECT only)

    Returns:
        Query results or error
    """
    # Security: Only allow SELECT
    sanitized_query = query.strip().upper()
    if not sanitized_query.startswith("SELECT"):
        return {
            "success": False,
            "error": "Only SELECT queries allowed",
            "error_type": "security_violation"
        }

    # Security: Block dangerous keywords
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "EXEC"]
    if any(keyword in sanitized_query for keyword in dangerous_keywords):
        return {
            "success": False,
            "error": "Query contains forbidden keywords",
            "error_type": "security_violation"
        }

    try:
        # Execute query (implementation depends on your database)
        # results = database.execute(query)

        return {
            "success": True,
            "results": []  # Placeholder
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

class SecurityError(Exception):
    pass

if __name__ == "__main__":
    asyncio.run(serve_stdio(mcp))
```

---

## Advanced Workflows

### Example 14: Chain of Tools Workflow

```python
"""
Advanced workflow pattern: Chain of tools with context passing.
"""
from typing import List, Dict, Any
from mcp.client import stdio_client, ClientSession
import asyncio

class ChainWorkflow:
    def __init__(self, mcp_client):
        self.client = mcp_client

    async def execute(self, tools_chain: List[Dict], initial_input: Dict) -> Dict:
        """
        Execute a chain of tools where output flows into next tool.

        Args:
            tools_chain: List of {tool, input_mapping} dictionaries
            initial_input: Initial input data

        Returns:
            Final result with all intermediate results
        """
        current_data = initial_input
        all_results = {"initial_input": initial_input}

        for step in tools_chain:
            tool_name = step["tool"]
            input_mapping = step.get("input_mapping", {})

            # Map current data to tool inputs
            tool_args = {}
            for param, source in input_mapping.items():
                if source.startswith("$"):
                    # Reference to previous result
                    tool_args[param] = current_data.get(source[1:])
                else:
                    # Static value
                    tool_args[param] = source

            print(f"Executing: {tool_name} with {tool_args}")

            # Execute tool
            result = await self.client.call_tool(tool_name, arguments=tool_args)

            # Store result
            all_results[tool_name] = result

            # Update current data for next step
            if isinstance(result, dict):
                current_data.update(result)
            else:
                current_data["result"] = result

        return {
            "success": True,
            "final_result": current_data,
            "all_results": all_results
        }

# Usage example
async def main():
    server_params = {
        "command": "python",
        "args": ["data_processing_server.py"]
    }

    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            workflow = ChainWorkflow(session)

            # Define workflow
            data_pipeline = [
                {
                    "tool": "fetch_data",
                    "input_mapping": {
                        "source": "sales_database",
                        "table": "transactions"
                    }
                },
                {
                    "tool": "clean_data",
                    "input_mapping": {
                        "data": "$raw_data"  # Reference previous result
                    }
                },
                {
                    "tool": "analyze_data",
                    "input_mapping": {
                        "data": "$cleaned_data",
                        "metrics": ["revenue", "count", "avg_value"]
                    }
                },
                {
                    "tool": "generate_report",
                    "input_mapping": {
                        "analysis": "$analysis_results",
                        "format": "markdown"
                    }
                }
            ]

            result = await workflow.execute(
                data_pipeline,
                {"start_date": "2025-01-01", "end_date": "2025-01-31"}
            )

            print("Final result:", result)

asyncio.run(main())
```

---

## Summary

This examples collection demonstrates:

- **Basic Servers**: Simple weather, calculator, and file system servers
- **Advanced Servers**: Database with connection pooling, API wrapper with caching
- **Clients**: Python and TypeScript clients with comprehensive features
- **LLM Integration**: OpenAI and Azure OpenAI integration patterns
- **Real-World**: Documentation server, CI/CD integration
- **Testing**: Comprehensive integration test suite
- **Security**: Authentication, rate limiting, input validation
- **Workflows**: Chain of tools, parallel execution

All examples follow MCP best practices and include proper error handling, security measures, and documentation.
