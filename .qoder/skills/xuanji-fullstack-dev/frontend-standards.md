# Frontend Standards

## TypeScript Configuration

Use strict mode with these key compiler options:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

## ESLint Configuration

Extend from recommended configs:

```js
// .eslintrc.cjs
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-type-checked',
    'prettier',  // Must be last to override formatting rules
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    project: true,
    tsconfigRootDir: __dirname,
  },
  rules: {
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/consistent-type-imports': 'error',
    'no-console': ['warn', { allow: ['warn', 'error'] }],
  },
}
```

## Prettier Configuration

```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

Use `prettier-plugin-tailwindcss` to auto-sort Tailwind classes.

## Vite Configuration

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

## Tailwind CSS

Use `tailwind.config.ts` with type-safe config:

```ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { /* custom brand colors */ },
      },
    },
  },
  plugins: [],
} satisfies Config
```

### Tailwind Conventions

- Use utility classes directly; avoid `@apply` except in base layer resets
- Responsive: mobile-first (`sm:`, `md:`, `lg:`)
- Dark mode: use `dark:` variant with class strategy
- Component patterns: extract to React components, not CSS abstractions

## Component Conventions

### File Naming

- Components: `PascalCase.tsx` (e.g., `ChatPanel.tsx`)
- Hooks: `camelCase.ts` prefixed with `use` (e.g., `useChatHistory.ts`)
- Utils: `camelCase.ts` (e.g., `formatDate.ts`)
- Types: `camelCase.ts` or co-located in component file
- Constants: `UPPER_SNAKE_CASE` for values, `camelCase.ts` for files

### Component Structure

```tsx
// 1. Type imports
import type { ChatMessage } from '@/types/chat'

// 2. Value imports
import { useState } from 'react'
import { formatDate } from '@/utils/formatDate'

// 3. Props interface (if needed)
interface ChatBubbleProps {
  message: ChatMessage
  onRetry?: () => void
}

// 4. Component (named export preferred)
export function ChatBubble({ message, onRetry }: ChatBubbleProps) {
  // hooks first
  const [expanded, setExpanded] = useState(false)

  // handlers
  const handleClick = () => setExpanded(!expanded)

  // render
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      {/* ... */}
    </div>
  )
}
```

## API Client Pattern

Use a centralized request utility with `fetch` or `axios`:

```ts
// src/api/client.ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
```

## State Management

For simple state, use React Context + `useReducer`. For complex state, use Zustand:

```ts
// src/stores/chatStore.ts
import { create } from 'zustand'

interface ChatState {
  messages: ChatMessage[]
  addMessage: (msg: ChatMessage) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  clearMessages: () => set({ messages: [] }),
}))
```

## Package Scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext .ts,.tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext .ts,.tsx --fix",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,css}\"",
    "typecheck": "tsc --noEmit"
  }
}
```
