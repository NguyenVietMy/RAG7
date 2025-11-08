# Backend Integration Setup

This guide explains how to connect the Next.js frontend to the FastAPI backend.

## Environment Variables

Create a `.env.local` file in the `app/` directory with:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

For production, update this to your backend URL.

## Usage

The API client is available at `src/lib/api-client.ts`. Import and use it:

```typescript
import { apiClient } from "@/lib/api-client";

// Health check
const health = await apiClient.healthChroma();

// Create a collection
await apiClient.createCollection("my-collection");

// Upsert documents
await apiClient.upsert("my-collection", {
  ids: ["doc1", "doc2"],
  documents: ["Text 1", "Text 2"],
});

// Query
const results = await apiClient.query("my-collection", {
  query_texts: ["What is this about?"],
  n_results: 5,
});
```

## CORS Configuration

The backend allows requests from:

- `http://localhost:3000` (default Next.js dev port)
- `http://localhost:3001` (alternative port)

To add more origins, edit `backend/main.py` and update the `allow_origins` list in the CORS middleware.

## Running the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`.
