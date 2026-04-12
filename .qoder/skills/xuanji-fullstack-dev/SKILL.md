---
name: xuanji-fullstack-dev
description: XuanJi project full-stack development standards covering frontend (TypeScript, Vite, Tailwind CSS, ESLint, Prettier), backend (Python 3.11, Conda, FastAPI, MySQL 8.0+, SQLAlchemy, Pymysql), AI integration (Ollama local LLM, online LLM API), and engineering practices (.env management, linting, formatting, environment isolation). Use when writing, reviewing, or scaffolding any code in this project, or when the user asks about project conventions, tech stack, or architecture decisions.
---

# XuanJi Full-Stack Development Standards

## Project Architecture Overview

```
XuanJi/
├── frontend/                # Vite + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── api/             # API client & request utils
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page-level components
│   │   ├── hooks/           # Custom hooks
│   │   ├── stores/          # State management
│   │   ├── types/           # TypeScript type definitions
│   │   ├── utils/           # Utility functions
│   │   └── main.ts          # Entry point
│   ├── .eslintrc.cjs        # ESLint config
│   ├── .prettierrc          # Prettier config
│   ├── tailwind.config.ts   # Tailwind config
│   ├── tsconfig.json        # TypeScript config
│   ├── vite.config.ts       # Vite config
│   └── package.json
├── backend/                 # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/             # Route handlers
│   │   │   └── v1/          # API v1 endpoints
│   │   ├── core/            # Config, security, dependencies
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   ├── ai/              # LLM integration layer
│   │   │   ├── ollama.py    # Ollama local model client
│   │   │   └── online.py    # Online LLM API client
│   │   └── main.py          # FastAPI app entry
│   ├── migrations/          # Alembic database migrations
│   ├── tests/               # pytest tests
│   ├── environment.yml      # Conda environment definition
│   └── .env.example         # Environment variable template
└── .env                     # Sensitive config (git-ignored)
```

## Tech Stack Quick Reference

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend Runtime | TypeScript | 5.x (strict mode) |
| Frontend Build | Vite | 5.x+ |
| Frontend Styling | Tailwind CSS | 3.x+ |
| Frontend Lint | ESLint + Prettier | Latest |
| Backend Runtime | Python | 3.11 |
| Backend Framework | FastAPI | 0.100+ |
| Backend ORM | SQLAlchemy | 2.0+ |
| DB Driver | PyMySQL | Latest |
| Database | MySQL | 8.0+ |
| Environment | Conda | Latest |
| AI Local | Ollama | Latest |
| AI Online | OpenAI-compatible API | - |

## Core Rules

### 1. TypeScript Strict Mode

All frontend code uses `strict: true` in tsconfig.json. No `any` types unless explicitly justified. Prefer interfaces over type aliases for object shapes.

### 2. Python Type Hints

All backend code uses type hints. Pydantic models for request/response validation. SQLAlchemy 2.0 style mapped columns.

### 3. Environment Variables

**Never hardcode** secrets, API keys, DB credentials, or model endpoints. Use `.env` file with `pydantic-settings` (backend) or `import.meta.env` (frontend).

Required `.env` variables:
```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=xuanji

# AI - Ollama
OLLAMA_BASE_URL=http://localhost:11434

# AI - Online LLM
LLM_API_KEY=
LLM_API_BASE_URL=
LLM_MODEL_NAME=

# App
SECRET_KEY=
CORS_ORIGINS=http://localhost:5173
```

### 4. Conda Environment

Backend Python environment managed via Conda. Always use `environment.yml`:
```yaml
name: xuanji
channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
    - fastapi
    - uvicorn[standard]
    - sqlalchemy>=2.0
    - pymysql
    - pydantic-settings
    - alembic
    - httpx
    - python-dotenv
```

Activate before any backend work: `conda activate xuanji`

### 5. ESLint + Prettier

Frontend uses ESLint for code quality and Prettier for formatting. They must not conflict. Run before commit:
```bash
cd frontend && npm run lint && npm run format:check
```

### 6. API Design

RESTful endpoints under `/api/v1/`. Use Pydantic schemas for all request/response models. Return consistent JSON structure:
```json
{ "code": 200, "message": "success", "data": {} }
```

### 7. Database Conventions

- Table names: snake_case, plural (e.g., `users`, `chat_sessions`)
- Primary key: `id` (auto-increment BigInt)
- Timestamps: `created_at`, `updated_at` (server-default UTC)
- Soft delete: `deleted_at` nullable timestamp where applicable
- Use Alembic for all schema migrations, never manual DDL

### 8. AI Integration Pattern

All LLM calls go through the `app/ai/` module. Use a unified interface:
```python
from app.ai.ollama import OllamaClient
from app.ai.online import OnlineLLMClient

# Both implement the same base interface
class BaseLLMClient:
    async def chat(self, messages: list[dict], **kwargs) -> str: ...
    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncIterator[str]: ...
```

Ollama for local development/testing. Online API for production or when higher capability is needed. Selection via env var `LLM_PROVIDER=ollama|online`.

## Detailed Standards

- For frontend conventions, see [frontend-standards.md](frontend-standards.md)
- For backend conventions, see [backend-standards.md](backend-standards.md)
- For AI integration details, see [ai-integration.md](ai-integration.md)
