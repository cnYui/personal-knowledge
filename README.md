# Personal Knowledge Base

A full-stack personal knowledge base application for managing learning notes, uploading text and images, and chatting with an AI assistant backed by a knowledge graph and RAG system.

## Features

- Memory management page for browsing, editing, filtering, and deleting memories
- Memory upload page for submitting text notes and related images
- Knowledge chat page for asking questions against stored learning memories
- FastAPI backend with memory CRUD, upload, and chat APIs
- Image pipeline stub for OCR and multimodal description generation

## Project Structure

```text
frontend/   React + TypeScript + Material UI application
backend/    FastAPI application and tests
docs/       Design and implementation documents
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` by default.

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend runs on `http://localhost:8000` by default.

## Environment Variables

Copy `.env.example` to `.env` and adjust values as needed.

Key variables:

- `VITE_API_BASE_URL`
- `DATABASE_URL`
- `UPLOAD_DIR`
- `OCR_ENABLED`
- `MULTIMODAL_PROVIDER`
- `MULTIMODAL_API_KEY`
- `KNOWLEDGE_GRAPH_BASE_URL`

## Test

```bash
python -m pytest backend/tests -v
```

## Build Frontend

```bash
cd frontend
npm run build
```
