# DSS Knowledge Base

**AI-Powered Knowledge Base with RAG, Web Scraping, and GitHub Integration**

A comprehensive knowledge management system that enables users to build custom AI assistants by ingesting documents, web content, and code repositories. Features RAG-powered chat, document summarization, and MCP server integration for AI coding assistants.

---

## 1. Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.12)
- **Vector Database**: ChromaDB
- **Relational Database**: PostgreSQL
- **AI/ML**:
  - OpenAI API (GPT-4o, GPT-4o-mini for chat)
  - OpenAI Embeddings (text-embedding-3-small)
- **Web Scraping**: Crawl4AI (with Playwright/Chromium)
- **MCP Server**: FastMCP (Model Context Protocol)
- **Containerization**: Docker & Docker Compose
- **Package Management**: uv (ultra-fast Python package installer)

### Frontend
- **Framework**: Next.js 14 (TypeScript)
- **UI Components**: Radix UI + shadcn/ui
- **Styling**: Tailwind CSS
- **State Management**: React Hooks
- **File Upload**: React Dropzone
- **PDF Processing**: pdfjs-dist

### Infrastructure
- **Database**: PostgreSQL 15 (via Supabase or standalone)
- **Vector Store**: ChromaDB (self-hosted or cloud)
- **Deployment**: Docker containers with docker-compose
- **Environment**: Python 3.12-slim base image

---

## 2. Features

### Core Knowledge Base Features

#### Document Management
- **File Upload**: Support for PDF, DOCX, TXT, Markdown files
- **Document Parsing**: Automatic text extraction and chunking
- **Vector Embeddings**: OpenAI embeddings for semantic search
- **Collection Management**: Create, list, query, and manage ChromaDB collections
- **File Statistics**: Track files and records per collection

#### RAG-Powered Chat
- **Semantic Search**: Query collections with natural language
- **Context-Aware Responses**: Retrieves relevant chunks based on query
- **Citations**: Every response includes source citations
- **Session Memory**: Multi-turn conversations with context retention
- **Configurable RAG**: Adjustable similarity thresholds, result counts, and context tokens
- **Model Selection**: Support for GPT-4o and GPT-4o-mini

#### Document Summarization
- **Hierarchical Summarization**: Efficient batch processing (25 chunks → summaries → final summary)
- **Cost-Effective**: ~22-23 LLM calls for 500 chunks
- **PostgreSQL Storage**: Summaries stored for fast retrieval
- **Auto-Summarization**: Optional automatic summarization on document upload
- **Summary Retrieval**: Query stored summaries for documents

### Web Scraping Features

#### Intelligent Web Crawling
- **Three Crawling Strategies**:
  1. **Sitemap Crawling**: Parse sitemap.xml and crawl all URLs in parallel
  2. **Text File Crawling**: Directly retrieve .txt/markdown files (e.g., llms.txt)
  3. **Recursive Internal Links**: Follow internal links recursively up to max_depth
- **Auto-Detection**: Automatically selects best strategy based on URL
- **Smart Chunking**: Preserves code blocks, respects paragraph boundaries
- **Batch Embeddings**: Efficient embedding generation with retry logic
- **Memory Management**: Adaptive dispatcher prevents memory issues
- **Progress Logging**: Detailed logging for monitoring scraping progress

### GitHub Repository Scraping

#### Code Repository Ingestion
- **Repository Cloning**: Clone GitHub repositories using git
- **File Processing**: Extract code and documentation files
- **Language Support**: Process multiple programming languages (Python, JavaScript, TypeScript, Java, Go, Rust, etc.)
- **Smart Filtering**: Include/exclude patterns for file selection
- **Context Preservation**: Maintains file paths and structure in metadata
- **Chunking**: Intelligent code chunking with language-aware splitting
- **Progress Tracking**: Step-by-step logging of scraping process

### MCP Server Integration

#### AI Assistant Tools (for Cursor, Claude Desktop, etc.)
- **Collection Tools**:
  - `list_collections`: List all ChromaDB collections
  - `get_collection_info`: Get collection metadata and stats
  - `query_collection`: Search collections with RAG
- **Chat Tools**:
  - `rag_chat`: Chat with RAG context from collections
  - `generate_chat_title`: Auto-generate conversation titles
- **Configuration Tools**:
  - `get_rag_config`: Get current RAG settings
  - `update_rag_config`: Update RAG parameters
- **Document Tools**:
  - `summarize_document`: Generate hierarchical document summaries
  - `get_document_summary`: Retrieve stored summaries
- **Scraping Tools**:
  - `scrape_web_documentation`: Scrape and ingest web docs
  - `scrape_github_repo`: Scrape and ingest GitHub repositories

### API Endpoints

#### Collections
- `GET /collections` - List all collections
- `POST /collections` - Create new collection
- `GET /collections/{name}` - Get collection info
- `GET /collections/{name}/files` - Get file statistics
- `POST /collections/{name}/upsert` - Upload and index documents
- `POST /collections/{name}/upsert-and-summarize` - Upload with auto-summarization
- `POST /collections/{name}/query` - Query collection with RAG
- `DELETE /collections/{name}/delete` - Delete records by filename

#### Chat
- `POST /chat` - RAG-powered chat endpoint
- `POST /chat/generate-title` - Generate conversation title

#### Configuration
- `GET /rag/config` - Get RAG configuration
- `PUT /rag/config` - Update RAG configuration

#### Health
- `GET /health` - Basic health check
- `GET /health/chroma` - ChromaDB connection check
- `GET /health/chroma/env` - ChromaDB configuration diagnostics

---

## 3. Use Cases

### For Students & Learners
- **Study Assistant**: Upload lecture notes, textbooks, and research papers to create a personalized study assistant
- **Research Companion**: Build a knowledge base from multiple sources and ask questions across all materials
- **Exam Preparation**: Query your uploaded materials to test understanding and get explanations

### For Developers
- **Codebase Documentation**: Scrape GitHub repositories to create searchable documentation of your codebase
- **API Documentation**: Ingest API docs from websites to have instant access while coding
- **Project Knowledge Base**: Combine code, docs, and design decisions into one queryable system
- **IDE Integration**: Use MCP server with Cursor/Claude Desktop to query knowledge base while coding

### For Researchers
- **Literature Review**: Upload multiple research papers and query across them for insights
- **Data Analysis**: Create knowledge bases from research datasets and documentation
- **Collaboration**: Share knowledge bases with team members for collaborative research

### For Content Creators
- **Content Research**: Scrape relevant websites and documentation to build reference knowledge bases
- **Fact-Checking**: Upload source materials and verify information quickly
- **Content Planning**: Query knowledge bases to find relevant information for content creation

### For Businesses
- **Internal Documentation**: Create searchable knowledge bases from company wikis, docs, and training materials
- **Customer Support**: Build knowledge bases from support documentation for faster responses
- **Onboarding**: New employees can query company knowledge bases to learn faster
- **Compliance**: Maintain searchable archives of policies, procedures, and regulations

### For Technical Teams
- **Architecture Documentation**: Scrape technical documentation sites and combine with internal docs
- **Troubleshooting**: Query knowledge bases for solutions to common problems
- **Best Practices**: Maintain searchable repositories of coding standards and best practices
- **Integration Guides**: Ingest API documentation from multiple sources for easy reference

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Setup
1. Clone the repository
2. Create `.env` file with your OpenAI API key
3. Run `docker-compose up` in the `backend` directory
4. Access the frontend at `http://localhost:3000`
5. Start uploading documents or scraping web content!

---

## Architecture Highlights

- **Dual Interface**: FastAPI REST API for frontend + MCP Server for AI assistants
- **Scalable**: Docker-based deployment with separate services
- **Efficient**: Batch processing, smart chunking, and cost-effective summarization
- **Extensible**: Easy to add new scraping sources and integrations
- **Production-Ready**: Comprehensive error handling, logging, and health checks

