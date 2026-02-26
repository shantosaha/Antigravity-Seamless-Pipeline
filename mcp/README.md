# MCP Servers Setup Guide

## Official MCP Servers

### Filesystem
```bash
npx @modelcontextprotocol/server-filesystem /path/to/allowed/directory
```

### GitHub
```bash
export GITHUB_TOKEN=your_token
npx @modelcontextprotocol/server-github
```

### HTTP Fetch
```bash
npx @modelcontextprotocol/server-fetch
```

### SQLite
```bash
npx @modelcontextprotocol/server-sqlite /path/to/database.db
```

### PostgreSQL
```bash
export POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:port/db
npx @modelcontextprotocol/server-postgres
```

## Configuration

Edit `mcp/servers.yaml` to configure which servers are active.

## Custom MCP Servers

To create custom MCP servers, see the MCP documentation:
https://github.com/modelcontextprotocol/servers
