# 📘 Product Requirements Document (PRD)

## Product Name

**Lola**

> “Forge your own AI Decision Support System.”

---

## 1. Overview

**Lola** is a web application that enables users to **create their own AI Decision Support Systems (DSS)** — functional, chat-based tools that analyze and reason over user-provided documents.

Users upload files (PDFs, DOCX, TXT, Markdown, or YouTube URLs) to instantly generate a **custom RAG-powered agent**.  
Each agent (“Professional”) can process information, recall key details, and assist decision-making through a **chat interface** with contextual memory and citations.

Lola focuses on functionality, accuracy, and reasoning — not personality.  
Each “Professional” is a domain-specific expert built purely from user data.

---

## 2. Goals & Objectives

| Goal                                                        | Description                                                                   |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 🎯 **Empower users to build their own AI decision systems** | Users can create domain-specific assistants by uploading their own materials. |
| ⚙️ **No-code setup**                                        | Upload → Index → Chat. No technical configuration required.                   |
| 💬 **Chat-first interface**                                 | Natural, conversational queries with contextual reasoning.                    |
| 💾 **Cloud-based storage**                                  | All embeddings, documents, and metadata are securely stored in the cloud.     |
| 🧠 **Support multiple AI Professionals**                    | Users can create, manage, and chat with multiple independent assistants.      |
| 📚 **Source-aware reasoning**                               | Each answer cites its sources transparently, increasing reliability.          |

---

## 3. Target Users

**Primary Audience:** 🎓 **Students and Learners**

| Segment       | Description                                                            | Example Use Case                                                     |
| ------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Students      | Build custom assistants for study material                             | “Summarize and quiz me on all uploaded biology chapters.”            |
| Researchers   | Build research companions                                              | “Compare two uploaded psychology papers and summarize the findings.” |
| Self-learners | Combine YouTube transcripts, PDFs, and notes into one knowledge system | “Explain concepts across all my uploaded resources.”                 |

---

## 4. Key Features

### 🧩 4.1 Core Features

| Feature                           | Description                                                                                            |
| --------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Document Upload & Parsing**     | Users upload PDFs, DOCX, TXT, or Markdown. Text is extracted locally (no cost) and sent for embedding. |
| **YouTube Transcript Extraction** | Extract and index transcript text from YouTube URLs.                                                   |
| **Vector Embedding Engine**       | Uses **OpenAI embedding models** (`text-embedding-3-small` / `3-large`) for document vectorization.    |
| **Vector Store (Cloud)**          | Store embeddings and metadata in a **cloud FAISS/ChromaDB** instance.                                  |
| **AI Professional Creation**      | Each Professional = isolated RAG pipeline with its own indexed dataset.                                |
| **Chat Interface (RAG-powered)**  | Real-time chat interface with streaming answers and chat memory.                                       |
| **Multi-query Reasoning**         | Parallel querying across sources for richer, more comprehensive responses.                             |
| **Citations**                     | Every answer includes citations (e.g., _“Source: Clean Code, Page 32”_).                               |
| **Session Memory**                | Chat remembers previous turns for better multi-turn reasoning.                                         |
| **Re-trainable Professionals**    | Users can upload new data anytime to expand an existing professional’s knowledge.                      |

---

### 💬 4.2 Future Features

| Feature                          | Description                                                    |
| -------------------------------- | -------------------------------------------------------------- |
| **Cloud Integrations**           | Google Drive, Notion, Slack, GitHub (Phase 2).                 |
| **Codebase Ingestion**           | Upload code repositories for “Developer AI Professionals.”     |
| **AI Model Selector**            | Allow users to choose LLM backend (GPT-4o, GPT-4o-mini, etc.). |
| **Professional Comparison View** | Compare responses from multiple professionals side-by-side.    |
| **Auto-Summarization**           | Auto-generate summaries and tags for uploaded files.           |
| **Team Collaboration Mode**      | Multi-user shared knowledge bases (post-hackathon feature).    |

---

## 5. User Flow

### 👤 Step 1: Sign Up / Login

- Email or Google authentication.
- Minimal onboarding: just “Create your first Professional.”

### ⚙️ Step 2: Create a Professional

- Name it (e.g., _“Data Science Advisor”_).
- Choose LLM backend (e.g., GPT-4o or GPT-4o-mini).
- Create workspace (cloud namespace).

### 📂 Step 3: Upload Files

- Drag-and-drop local PDFs, DOCX, TXT, or MD files.
- (Optional) Paste YouTube URLs for transcript extraction.
- Backend automatically:
  1. Extracts raw text
  2. Cleans & chunks
  3. Generates embeddings
  4. Stores vectors and metadata in the cloud

### 💬 Step 4: Chat

- Ask questions in chatbox.
- Model retrieves relevant context → responds → cites sources.
- Multi-turn memory retained across the chat session.

### 🧠 Step 5: Manage Professionals

- View all professionals in dashboard.
- Add or delete uploaded files.
- Re-embed to refresh knowledge base.

---

## 6. Technical Architecture

### 🧱 Backend

| Component      | Technology                                    |
| -------------- | --------------------------------------------- |
| Core Runtime   | **Python (FastAPI)**                          |
| RAG Pipeline   | **LangChain / LlamaIndex**                    |
| Embeddings     | **OpenAI Embeddings API**                     |
| Vector Store   | **FAISS / ChromaDB (Cloud)**                  |
| File Storage   | **AWS S3 or Supabase**                        |
| Auth           | **JWT or Clerk**                              |
| Database       | **PostgreSQL (User, Professional, Metadata)** |
| Session Memory | **Redis or Supabase Realtime**                |

---

### 💻 Frontend

| Component         | Technology                                |
| ----------------- | ----------------------------------------- |
| Framework         | **Next.js (TypeScript)**                  |
| UI                | **Tailwind + ShadCN/UI**                  |
| State             | **Zustand**                               |
| Realtime Chat     | **WebSockets / Server-Sent Events (SSE)** |
| File Upload       | **React Dropzone or UploadThing**         |
| Citations Display | Inline footnote-style references          |

---

### 🚀 Deployment

| Environment                   | Description                                                 |
| ----------------------------- | ----------------------------------------------------------- |
| **MVP**                       | Frontend on **Vercel**, backend on **Render** or **Fly.io** |
| **Scale**                     | AWS ECS or GCP Cloud Run with managed Postgres              |
| **Enterprise / Private Mode** | Docker image for self-hosted environments                   |

---

## 7. Monetization & Launch Plan

| Tier                      | Features                                               | Price  |
| ------------------------- | ------------------------------------------------------ | ------ |
| **Free (Hackathon MVP)**  | 1 Professional, 5 file uploads, GPT-4o-mini backend    | **$0** |
| _(Future)_ **Pro**        | Multiple professionals, more storage, faster inference | TBD    |
| _(Future)_ **Enterprise** | Private deployment, team workspaces                    | Custom |

---

## 8. Success Metrics (Hackathon Phase)

| Metric             | Target                                        |
| ------------------ | --------------------------------------------- |
| ⏱️ Setup Time      | < 3 minutes from upload → first chat          |
| ⚡ Query Latency   | < 4 seconds average response time             |
| 💬 Chat Retention  | ≥ 3 messages per session                      |
| 📚 Average Uploads | ≥ 5 documents per user                        |
| 💡 User Goal       | Build and use a personalized DSS successfully |

---

## 9. Risks & Mitigation

| Risk                          | Mitigation                                               |
| ----------------------------- | -------------------------------------------------------- |
| **Embedding API cost spikes** | Use `text-embedding-3-small` + batch processing          |
| **Slow queries**              | Cache retrieval results with FAISS local indexes         |
| **Data privacy**              | Encrypt file storage and restrict vector access per user |
| **LLM hallucinations**        | Require source citations in all responses                |
| **Memory bloat**              | Trim session history while preserving semantic context   |

---

## 10. Example Demo

**User creates:** “Cognitive Science Assistant”  
**Uploads:** 3 PDFs (Neuroscience basics, Decision Theory, Human Behavior), plus a YouTube lecture transcript.
