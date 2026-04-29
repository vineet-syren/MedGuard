# Proofline

Proofline is migrating from a single static HTML/FastAPI prototype into a Nuxt + FastAPI architecture.

## Architecture Call

Nuxt is the best fit for the product frontend, marketing site, console shell, SSR, and lightweight BFF/server routes.

FastAPI + Pydantic is the better fit for agentic AI backend services because the product needs streaming, schema-first agent outputs, RAG retrieval, MCP tool contracts, auditability, and multi-agent orchestration.

So the chosen stack is:

- `Nuxt`: frontend, public website, console, server-side BFF proxy routes.
- `FastAPI`: AI service boundary.
- `Pydantic`: request/response schemas, agent plans, RAG documents, MCP tool contracts.

## Run

Backend:

```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
npm install
npm run dev
```

The Nuxt app expects the FastAPI backend at `http://127.0.0.1:8000`. Override with:

```bash
AI_API_BASE=http://127.0.0.1:8000 npm run dev
```

