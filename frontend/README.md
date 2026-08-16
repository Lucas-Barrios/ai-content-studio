# AI Content Studio — Frontend

Production Next.js frontend for the Python AI content generation backend.

## Folder Structure

```txt
frontend/
├── app/
│   ├── api/
│   │   ├── chat/route.ts       # Vercel AI SDK-compatible text streaming proxy
│   │   ├── generate/route.ts   # Typed generation proxy to Python API
│   │   └── upload/route.ts     # Multipart upload proxy
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── app-shell.tsx
│   ├── content/
│   │   ├── chat-panel.tsx
│   │   ├── content-workbench.tsx
│   │   ├── file-upload.tsx
│   │   ├── history-panel.tsx
│   │   ├── input-panel.tsx
│   │   └── results-panel.tsx
│   └── ui/                    # shadcn/ui-compatible primitives
├── lib/
│   ├── api-client.ts           # Browser API client
│   ├── constants.ts
│   ├── hooks/use-content-session.ts
│   ├── types.ts
│   └── utils.ts
└── public/
```

## Backend Contract

Set the backend URL in `.env.local`:

```bash
PYTHON_API_BASE_URL=http://localhost:8000
```

Expected backend endpoints:

- `POST /generate`
  - Request: JSON matching `GenerateRequest` in `lib/types.ts`
  - Response can be one of:
    - `{ "content": "...", "sources": [...] }`
    - `{ "output": "...", "file_meta": [...] }`
    - `{ "result": "...", "fileMeta": [...] }`

- `POST /upload`
  - Request: `multipart/form-data` with `files`
  - Response: `UploadedFile[]` or `{ "files": UploadedFile[] }`

- `POST /chat/stream`
  - Request: Vercel AI SDK chat body
  - Response: streaming `text/plain`

- `POST /chat`
  - Non-streaming fallback. Response can include `content`, `message`, or `output`.

## Run Locally

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

## Production Notes

- The browser calls only local Next.js API routes.
- Next.js API routes proxy to the Python backend using server-side `PYTHON_API_BASE_URL`.
- The chat panel uses `@ai-sdk/react` with text streaming.
- Generation history is stored in browser `localStorage`.
- shadcn/ui-style primitives are checked into `components/ui` for repeatable builds.
