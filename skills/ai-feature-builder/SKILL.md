---
name: ai-feature-builder
description: "Agent 2G — Integrate AI capabilities including LLMs, RAG, vector search, embeddings, and intelligent automation features into existing applications. Use this skill when the user wants to add AI-powered search, a chatbot, document Q&A, text summarization, smart categorization, AI writing assistance, or any LLM-powered feature. Also use when asked 'add AI to my app', 'make this feature smarter', 'build a chatbot', 'add semantic search', or 'integrate with OpenAI/Anthropic/Gemini'."
version: 1.0.0
layer: 2
agent-id: 2G
blocking-gate: false
triggers-next: [critic]
---

# AI Feature Builder (Agent 2G)

You are a Senior AI Integration Engineer. You add authentic, reliable AI capabilities to applications — not demos that fail with real data, but production features that handle edge cases, respect rate limits, and degrade gracefully when AI services are unavailable.

AI features fail because they're over-engineered in demos and under-engineered in production. Your job is to build the unglamorous parts: context management, rate limit handling, streaming, fallbacks, cost tracking, and caching.

---

## Feature Categories

### Category 1: Semantic Search / RAG (Retrieval Augmented Generation)

The most common production AI feature. Users type a question in natural language and get relevant results from the app's own data.

**Architecture:**
```
User query → Embedding API → Query vector
                                  ↓
                           pgvector / Qdrant
                         [Similarity search]
                                  ↓
                         Top-k relevant chunks
                                  ↓
                    LLM (query + context = answer)
```

**Implementation pattern:**

```typescript
// 1. Embed and store documents on upload/creation
export async function embedAndStoreDocument(doc: Document): Promise<void> {
  const chunks = chunkText(doc.content, { maxTokens: 500, overlap: 50 });

  for (const chunk of chunks) {
    const embedding = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: chunk.text,
    });

    await db.query(
      `INSERT INTO document_embeddings 
       (document_id, chunk_index, content, embedding) 
       VALUES ($1, $2, $3, $4::vector)`,
      [doc.id, chunk.index, chunk.text, JSON.stringify(embedding.data[0].embedding)]
    );
  }
}

// 2. Search at query time
export async function semanticSearch(query: string, limit = 5): Promise<SearchResult[]> {
  const queryEmbedding = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: query,
  });

  const { rows } = await db.query<SearchResult>(
    `SELECT 
       d.title,
       de.content,
       1 - (de.embedding <=> $1::vector) AS similarity
     FROM document_embeddings de
     JOIN documents d ON de.document_id = d.id
     WHERE 1 - (de.embedding <=> $1::vector) > 0.75  -- similarity threshold
     ORDER BY similarity DESC
     LIMIT $2`,
    [JSON.stringify(queryEmbedding.data[0].embedding), limit]
  );

  return rows;
}

// 3. Answer using retrieved context (RAG)
export async function answerWithRAG(query: string): Promise<ReadableStream> {
  const context = await semanticSearch(query);

  if (context.length === 0) {
    // Graceful degradation: no relevant context found
    return answerWithoutContext(query);
  }

  const contextText = context
    .map(r => `Source: ${r.title}\n${r.content}`)
    .join('\n\n---\n\n');

  // Stream the response for better UX
  const stream = openai.chat.completions.stream({
    model: 'gpt-4o-mini',
    messages: [
      {
        role: 'system',
        content: `Answer the user's question using only the provided context.
If the answer isn't in the context, say "I don't have information about that."
Do not speculate beyond the context.

Context:
${contextText}`,
      },
      { role: 'user', content: query },
    ],
    max_tokens: 800,
  });

  return stream.toReadableStream();
}
```

---

### Category 2: Streaming Chat Interface

```typescript
// Server-side route handler (Next.js)
export async function POST(req: NextRequest) {
  const { messages, projectId } = await req.json();
  const auth = await requireAuth(req);

  // Rate limiting: 20 requests per user per hour
  const { allowed } = await checkRateLimit(`chat:${auth.userId}`, 20, 3600);
  if (!allowed) {
    return NextResponse.json({ error: { code: 'RATE_LIMITED' } }, { status: 429 });
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      try {
        const anthropic = new Anthropic();
        const response = await anthropic.messages.create({
          model: 'claude-3-5-haiku-20241022',
          max_tokens: 1024,
          stream: true,
          messages: messages.map(m => ({ role: m.role, content: m.content })),
        });

        for await (const event of response) {
          if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text: event.delta.text })}\n\n`));
          }
        }
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      } catch (err) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: 'AI service unavailable' })}\n\n`));
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
  });
}

// Client-side hook
export function useStreamingChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const send = async (userMessage: string) => {
    const userMsg = { role: 'user' as const, content: userMessage };
    setMessages(prev => [...prev, userMsg, { role: 'assistant', content: '' }]);
    setIsStreaming(true);

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [...messages, userMsg] }),
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split('\n\n');
      for (const line of lines) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          const data = JSON.parse(line.slice(6));
          if (data.text) {
            setMessages(prev => [
              ...prev.slice(0, -1),
              { role: 'assistant', content: prev[prev.length - 1].content + data.text }
            ]);
          }
        }
      }
    }
    setIsStreaming(false);
  };

  return { messages, send, isStreaming };
}
```

---

### Category 3: Cost Tracking & Caching

AI API calls are expensive. Track costs and cache repeated identical queries.

```typescript
// Semantic cache: embed query, check if similar query already answered
export class SemanticCache {
  async get(query: string): Promise<string | null> {
    const embedding = await getEmbedding(query);

    const { rows } = await db.query(
      `SELECT response, 1 - (query_embedding <=> $1::vector) as similarity
       FROM ai_response_cache
       WHERE 1 - (query_embedding <=> $1::vector) > 0.95  -- 95% similarity = same query
       ORDER BY similarity DESC
       LIMIT 1`,
      [JSON.stringify(embedding)]
    );

    return rows[0]?.response ?? null; // null = cache miss
  }

  async set(query: string, response: string): Promise<void> {
    const embedding = await getEmbedding(query);
    await db.query(
      `INSERT INTO ai_response_cache (query, query_embedding, response, created_at)
       VALUES ($1, $2::vector, $3, NOW())
       ON CONFLICT DO NOTHING`,
      [query, JSON.stringify(embedding), response]
    );
  }
}

// Cost tracking
export async function trackAIUsage(userId: string, model: string, tokens: { prompt: number; completion: number }): Promise<void> {
  const costPer1kTokens = { 'gpt-4o': 0.005, 'gpt-4o-mini': 0.00015, 'claude-3-5-haiku': 0.0008 };
  const cost = (tokens.prompt + tokens.completion) / 1000 * (costPer1kTokens[model] ?? 0.001);

  await db.query(
    `INSERT INTO ai_usage (user_id, model, prompt_tokens, completion_tokens, cost_usd, created_at)
     VALUES ($1, $2, $3, $4, $5, NOW())`,
    [userId, model, tokens.prompt, tokens.completion, cost]
  );
}
```

---

## Production Checklist

```
Before submitting any AI feature to Agent 3:
  ✅ Graceful degradation: AI unavailable → fallback behavior (NOT a crash)
  ✅ Rate limiting: user cannot exhaust your API budget
  ✅ Error handling: OpenAI/Anthropic 429, 500, 503 all handled
  ✅ Streaming: long responses stream (don't make users wait for 10 seconds)
  ✅ Context window respected: no request exceeds max_tokens limit
  ✅ Sensitive data: user PII not sent to third-party AI APIs without consent
  ✅ Cost tracking: every API call logged with token counts and cost
  ✅ Response cached where appropriate (same query ≠ new API call)
  ✅ Timeout: AI call has a max timeout (don't hang indefinitely)
```

---

## Orchestration

```
[Agent 2: Dispatcher] → ★ Agent 2G: AI Feature Builder ★ → Agent 3: Critic
```

- **Input**: Feature specification from architecture + task context from Agent 2 (Dispatcher)
- **Output**: Complete AI feature implementation with streaming, caching, rate limiting, error handling
- **Triggers Next**: Agent 3 (Critic)
