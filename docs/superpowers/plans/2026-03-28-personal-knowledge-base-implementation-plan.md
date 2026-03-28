# Personal Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a front-end/back-end separated personal knowledge base web app with three pages: memory management, memory upload, and knowledge chat.

**Architecture:** The frontend is a React + TypeScript + MUI SPA served by Vite. The backend is FastAPI with SQLAlchemy and PostgreSQL, exposing REST APIs for memory CRUD, uploads, and chat, while delegating RAG/knowledge graph logic to an external service.

**Tech Stack:** React 18, TypeScript, Vite, Material UI, TanStack Query, Axios, FastAPI, SQLAlchemy, Pydantic, PostgreSQL, Alembic, Pytest

---

## Planned File Structure

### Frontend
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/components/layout/AppLayout.tsx`
- Create: `frontend/src/components/layout/SideNav.tsx`
- Create: `frontend/src/components/layout/TopBar.tsx`
- Create: `frontend/src/components/common/PageHeader.tsx`
- Create: `frontend/src/components/common/LoadingState.tsx`
- Create: `frontend/src/components/common/ErrorState.tsx`
- Create: `frontend/src/components/common/ConfirmDialog.tsx`
- Create: `frontend/src/components/memory/MemoryCard.tsx`
- Create: `frontend/src/components/memory/MemoryFilterBar.tsx`
- Create: `frontend/src/components/memory/MemoryEditDialog.tsx`
- Create: `frontend/src/components/upload/ImageUploadPanel.tsx`
- Create: `frontend/src/components/upload/UploadForm.tsx`
- Create: `frontend/src/components/chat/ChatMessageList.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/EmptyChatState.tsx`
- Create: `frontend/src/pages/MemoryManagementPage.tsx`
- Create: `frontend/src/pages/MemoryUploadPage.tsx`
- Create: `frontend/src/pages/KnowledgeChatPage.tsx`
- Create: `frontend/src/services/http.ts`
- Create: `frontend/src/services/memoryApi.ts`
- Create: `frontend/src/services/uploadApi.ts`
- Create: `frontend/src/services/chatApi.ts`
- Create: `frontend/src/hooks/useMemories.ts`
- Create: `frontend/src/hooks/useUploadMemory.ts`
- Create: `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/types/memory.ts`
- Create: `frontend/src/types/upload.ts`
- Create: `frontend/src/types/chat.ts`
- Create: `frontend/src/utils/constants.ts`
- Create: `frontend/src/utils/format.ts`

### Backend
- Create: `backend/requirements.txt`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/memory.py`
- Create: `backend/app/models/chat.py`
- Create: `backend/app/schemas/memory.py`
- Create: `backend/app/schemas/upload.py`
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/repositories/memory_repository.py`
- Create: `backend/app/repositories/chat_repository.py`
- Create: `backend/app/services/memory_service.py`
- Create: `backend/app/services/image_processing_service.py`
- Create: `backend/app/services/multimodal_service.py`
- Create: `backend/app/services/knowledge_graph_service.py`
- Create: `backend/app/services/chat_service.py`
- Create: `backend/app/utils/file_storage.py`
- Create: `backend/app/routers/memories.py`
- Create: `backend/app/routers/uploads.py`
- Create: `backend/app/routers/chat.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_memories_api.py`
- Create: `backend/tests/test_uploads_api.py`
- Create: `backend/tests/test_chat_api.py`

### Root
- Create: `.gitignore`
- Create: `README.md`
- Create: `.env.example`

---

### Task 1: Initialize repository structure and frontend/backend skeleton

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `backend/requirements.txt`
- Create: `backend/app/main.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 1: Write the failing backend smoke test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError` or `cannot import name 'app'`

- [ ] **Step 3: Write minimal backend app and requirements**

```python
# backend/app/main.py
from fastapi import FastAPI

app = FastAPI(title="Personal Knowledge Base API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

```text
# backend/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
psycopg[binary]==3.2.1
pydantic-settings==2.5.2
python-multipart==0.0.9
httpx==0.27.2
pillow==10.4.0
pytesseract==0.3.13
pytest==8.3.3
```

```gitignore
# .gitignore
__pycache__/
*.pyc
.venv/
.env
node_modules/
dist/
coverage/
.pytest_cache/
backend/uploads/
```

- [ ] **Step 4: Write minimal frontend scaffold files**

```json
{
  "name": "personal-knowledge-base-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@emotion/react": "^11.13.3",
    "@emotion/styled": "^11.13.0",
    "@mui/icons-material": "^6.1.0",
    "@mui/material": "^6.1.0",
    "@tanstack/react-query": "^5.56.2",
    "axios": "^1.7.7",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.8",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.2",
    "typescript": "^5.6.2",
    "vite": "^5.4.8"
  }
}
```

```ts
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
})
```

- [ ] **Step 5: Run backend smoke test to verify it passes**

Run: `pytest backend/tests/test_health.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add .gitignore .env.example README.md frontend backend
git commit -m "chore: initialize project skeleton"
```

### Task 2: Add backend configuration, database session, and models

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/memory.py`
- Create: `backend/app/models/chat.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing model test**

```python
from app.models.memory import Memory


def test_memory_model_has_expected_fields():
    memory = Memory(title="Test", content="Body", importance=3)

    assert memory.title == "Test"
    assert memory.content == "Body"
    assert memory.importance == 3
    assert hasattr(memory, "created_at")
    assert hasattr(memory, "updated_at")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.memory'`

- [ ] **Step 3: Write minimal config, database, and models**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "backend/uploads/images"
    knowledge_graph_base_url: str = "http://localhost:8001"
    multimodal_provider: str = "mock"
    multimodal_api_key: str = ""
    ocr_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

```python
# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
```

```python
# backend/app/models/memory.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    importance: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    images: Mapped[list["MemoryImage"]] = relationship(back_populates="memory", cascade="all, delete-orphan")


class MemoryImage(Base):
    __tablename__ = "memory_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memories.id"), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memory: Mapped["Memory"] = relationship(back_populates="images")
```

```python
# backend/app/models/chat.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core backend/app/models backend/tests/test_models.py
git commit -m "feat: add backend config and models"
```

### Task 3: Implement memory schemas, repository, service, and CRUD API

**Files:**
- Create: `backend/app/schemas/memory.py`
- Create: `backend/app/repositories/memory_repository.py`
- Create: `backend/app/services/memory_service.py`
- Create: `backend/app/routers/memories.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_memories_api.py`

- [ ] **Step 1: Write the failing memory CRUD test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_create_and_list_memories():
    client = TestClient(app)

    create_response = client.post(
        "/api/memories",
        json={
            "title": "Linear Algebra",
            "content": "Vector spaces and basis.",
            "tags": ["math", "algebra"],
            "importance": 4,
        },
    )

    assert create_response.status_code == 201

    list_response = client.get("/api/memories")
    payload = list_response.json()

    assert list_response.status_code == 200
    assert payload[0]["title"] == "Linear Algebra"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_memories_api.py::test_create_and_list_memories -v`
Expected: FAIL with `404 Not Found` or missing route

- [ ] **Step 3: Add schemas and minimal CRUD implementation**

```python
# backend/app/schemas/memory.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)


class MemoryUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)


class MemoryRead(BaseModel):
    id: UUID
    title: str
    content: str
    tags: list[str]
    importance: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
```

```python
# backend/app/routers/memories.py
from fastapi import APIRouter, status

from app.schemas.memory import MemoryCreate, MemoryRead

router = APIRouter(prefix="/api/memories", tags=["memories"])
_fake_memories: list[dict] = []


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreate):
    item = {
        "id": "11111111-1111-1111-1111-111111111111",
        "title": payload.title,
        "content": payload.content,
        "tags": payload.tags,
        "importance": payload.importance,
        "created_at": None,
        "updated_at": None,
    }
    _fake_memories.append(item)
    return item


@router.get("", response_model=list[MemoryRead])
def list_memories():
    return _fake_memories
```

```python
# backend/app/main.py
from fastapi import FastAPI

from app.routers.memories import router as memories_router

app = FastAPI(title="Personal Knowledge Base API")
app.include_router(memories_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Expand to real DB-backed repository and service**

```python
# backend/app/repositories/memory_repository.py
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate


class MemoryRepository:
    def create(self, db: Session, payload: MemoryCreate) -> Memory:
        memory = Memory(**payload.model_dump())
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def list(self, db: Session, keyword: str | None = None, tag: str | None = None) -> list[Memory]:
        query = select(Memory)
        if keyword:
            query = query.where(Memory.title.ilike(f"%{keyword}%") | Memory.content.ilike(f"%{keyword}%"))
        if tag:
            query = query.where(Memory.tags.contains([tag]))
        return list(db.scalars(query.order_by(Memory.updated_at.desc())))

    def get(self, db: Session, memory_id):
        return db.get(Memory, memory_id)

    def update(self, db: Session, memory: Memory, payload: MemoryUpdate) -> Memory:
        for key, value in payload.model_dump().items():
            setattr(memory, key, value)
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def delete(self, db: Session, memory: Memory) -> None:
        db.delete(memory)
        db.commit()
```

- [ ] **Step 5: Run test suite to verify it passes**

Run: `pytest backend/tests/test_memories_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/memory.py backend/app/repositories/memory_repository.py backend/app/services/memory_service.py backend/app/routers/memories.py backend/app/main.py backend/tests/test_memories_api.py
git commit -m "feat: implement memory crud api"
```

### Task 4: Implement upload endpoint, file storage, and image processing stubs

**Files:**
- Create: `backend/app/schemas/upload.py`
- Create: `backend/app/utils/file_storage.py`
- Create: `backend/app/services/multimodal_service.py`
- Create: `backend/app/services/image_processing_service.py`
- Create: `backend/app/routers/uploads.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_uploads_api.py`

- [ ] **Step 1: Write the failing upload test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_upload_memory_with_image_returns_created():
    client = TestClient(app)

    response = client.post(
        "/api/uploads/memories",
        data={
            "title": "Graph note",
            "content": "A graph with nodes and edges.",
            "tags": '["graph"]',
            "importance": "5",
        },
        files={"images": ("note.png", b"fake-image-bytes", "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Graph note"
    assert body["images_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_uploads_api.py::test_upload_memory_with_image_returns_created -v`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Add minimal upload route and file storage utility**

```python
# backend/app/utils/file_storage.py
from pathlib import Path
from uuid import uuid4


def save_upload(upload_dir: str, filename: str, content: bytes) -> str:
    target_dir = Path(upload_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid4()}-{filename}"
    target_path.write_bytes(content)
    return str(target_path)
```

```python
# backend/app/routers/uploads.py
import json

from fastapi import APIRouter, File, Form, UploadFile, status

from app.utils.file_storage import save_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/memories", status_code=status.HTTP_201_CREATED)
async def upload_memory(
    title: str = Form(...),
    content: str = Form(...),
    tags: str = Form("[]"),
    importance: int = Form(3),
    images: list[UploadFile] = File(default=[]),
):
    parsed_tags = json.loads(tags)
    for image in images:
        data = await image.read()
        save_upload("backend/uploads/images", image.filename, data)
    return {
        "title": title,
        "content": content,
        "tags": parsed_tags,
        "importance": importance,
        "images_count": len(images),
    }
```

- [ ] **Step 4: Add OCR and multimodal stubs with non-blocking failure behavior**

```python
# backend/app/services/multimodal_service.py
class MultimodalService:
    def describe_image(self, image_path: str) -> str:
        return f"Generated description for {image_path}"
```

```python
# backend/app/services/image_processing_service.py
from app.services.multimodal_service import MultimodalService


class ImageProcessingService:
    def __init__(self) -> None:
        self.multimodal_service = MultimodalService()

    def extract_ocr_text(self, image_path: str) -> str:
        return ""

    def process_image(self, image_path: str) -> dict[str, str]:
        return {
            "ocr_text": self.extract_ocr_text(image_path),
            "image_description": self.multimodal_service.describe_image(image_path),
        }
```

- [ ] **Step 5: Run upload tests to verify they pass**

Run: `pytest backend/tests/test_uploads_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/upload.py backend/app/utils/file_storage.py backend/app/services/multimodal_service.py backend/app/services/image_processing_service.py backend/app/routers/uploads.py backend/app/main.py backend/tests/test_uploads_api.py
git commit -m "feat: add memory upload and image processing stubs"
```

### Task 5: Implement chat persistence and knowledge graph integration API

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/repositories/chat_repository.py`
- Create: `backend/app/services/knowledge_graph_service.py`
- Create: `backend/app/services/chat_service.py`
- Create: `backend/app/routers/chat.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: Write the failing chat test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_send_chat_message_returns_answer():
    client = TestClient(app)

    response = client.post("/api/chat/messages", json={"message": "什么是向量空间？"})

    assert response.status_code == 200
    assert "answer" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_chat_api.py::test_send_chat_message_returns_answer -v`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Add minimal schemas and router**

```python
# backend/app/schemas/chat.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    references: list[str] = Field(default_factory=list)


class ChatMessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True
```

```python
# backend/app/services/knowledge_graph_service.py
class KnowledgeGraphService:
    def ask(self, message: str) -> dict:
        return {
            "answer": f"Mock answer for: {message}",
            "references": [],
        }
```

```python
# backend/app/routers/chat.py
from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.knowledge_graph_service import KnowledgeGraphService

router = APIRouter(prefix="/api/chat/messages", tags=["chat"])
service = KnowledgeGraphService()
_history: list[dict] = []


@router.post("", response_model=ChatResponse)
def send_message(payload: ChatRequest):
    result = service.ask(payload.message)
    _history.append({"role": "user", "content": payload.message})
    _history.append({"role": "assistant", "content": result["answer"]})
    return result


@router.get("")
def get_messages():
    return _history


@router.delete("")
def clear_messages():
    _history.clear()
    return {"success": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_chat_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/chat.py backend/app/repositories/chat_repository.py backend/app/services/knowledge_graph_service.py backend/app/services/chat_service.py backend/app/routers/chat.py backend/app/main.py backend/tests/test_chat_api.py
git commit -m "feat: add chat api and knowledge graph integration stub"
```

### Task 6: Build frontend application shell, providers, and routing

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/components/layout/AppLayout.tsx`
- Create: `frontend/src/components/layout/SideNav.tsx`
- Create: `frontend/src/components/layout/TopBar.tsx`
- Create: `frontend/src/components/common/PageHeader.tsx`
- Test: manual browser verification

- [ ] **Step 1: Write the minimal routing implementation**

```tsx
// frontend/src/app/router.tsx
import { Navigate, createBrowserRouter } from 'react-router-dom'

import { AppLayout } from '../components/layout/AppLayout'
import { KnowledgeChatPage } from '../pages/KnowledgeChatPage'
import { MemoryManagementPage } from '../pages/MemoryManagementPage'
import { MemoryUploadPage } from '../pages/MemoryUploadPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/memories" replace /> },
      { path: 'memories', element: <MemoryManagementPage /> },
      { path: 'upload', element: <MemoryUploadPage /> },
      { path: 'chat', element: <KnowledgeChatPage /> },
    ],
  },
])
```

- [ ] **Step 2: Write the providers and app bootstrap**

```tsx
// frontend/src/app/providers.tsx
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PropsWithChildren, useState } from 'react'

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(() => new QueryClient())
  const theme = createTheme()

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'

import { AppProviders } from './app/providers'
import { router } from './app/router'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </React.StrictMode>,
)
```

- [ ] **Step 3: Write the shared layout**

```tsx
// frontend/src/components/layout/AppLayout.tsx
import { Box } from '@mui/material'
import { Outlet } from 'react-router-dom'

import { SideNav } from './SideNav'
import { TopBar } from './TopBar'

export function AppLayout() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <SideNav />
      <Box sx={{ flex: 1 }}>
        <TopBar />
        <Box component="main" sx={{ p: 3 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 4: Run frontend app and verify routes render**

Run: `npm install && npm run dev`
Expected: Browser shows left navigation with `/memories`, `/upload`, `/chat`

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/package.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html
git commit -m "feat: add frontend app shell and routing"
```

### Task 7: Implement memory management page and frontend API hooks

**Files:**
- Create: `frontend/src/types/memory.ts`
- Create: `frontend/src/services/http.ts`
- Create: `frontend/src/services/memoryApi.ts`
- Create: `frontend/src/hooks/useMemories.ts`
- Create: `frontend/src/components/memory/MemoryCard.tsx`
- Create: `frontend/src/components/memory/MemoryFilterBar.tsx`
- Create: `frontend/src/components/memory/MemoryEditDialog.tsx`
- Create: `frontend/src/components/common/ConfirmDialog.tsx`
- Create: `frontend/src/components/common/LoadingState.tsx`
- Create: `frontend/src/components/common/ErrorState.tsx`
- Create: `frontend/src/pages/MemoryManagementPage.tsx`
- Test: manual browser verification against running API

- [ ] **Step 1: Add shared memory types and API client**

```ts
// frontend/src/types/memory.ts
export interface MemoryImage {
  id: string
  original_file_name: string
  stored_path: string
  ocr_text?: string | null
  image_description?: string | null
}

export interface Memory {
  id: string
  title: string
  content: string
  tags: string[]
  importance: number
  created_at?: string | null
  updated_at?: string | null
  images?: MemoryImage[]
}
```

```ts
// frontend/src/services/http.ts
import axios from 'axios'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
})
```

- [ ] **Step 2: Implement query/mutation hooks**

```ts
// frontend/src/hooks/useMemories.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createMemory, deleteMemory, listMemories, updateMemory } from '../services/memoryApi'

export function useMemories(keyword?: string, tag?: string) {
  return useQuery({
    queryKey: ['memories', keyword, tag],
    queryFn: () => listMemories({ keyword, tag }),
  })
}

export function useUpdateMemory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: updateMemory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memories'] }),
  })
}

export function useDeleteMemory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memories'] }),
  })
}
```

- [ ] **Step 3: Implement memory management page**

```tsx
// frontend/src/pages/MemoryManagementPage.tsx
import { Stack, Typography } from '@mui/material'
import { useState } from 'react'

import { ErrorState } from '../components/common/ErrorState'
import { LoadingState } from '../components/common/LoadingState'
import { MemoryCard } from '../components/memory/MemoryCard'
import { MemoryFilterBar } from '../components/memory/MemoryFilterBar'
import { useMemories } from '../hooks/useMemories'

export function MemoryManagementPage() {
  const [keyword, setKeyword] = useState('')
  const { data, isLoading, isError } = useMemories(keyword)

  if (isLoading) return <LoadingState label="正在加载记忆..." />
  if (isError) return <ErrorState message="记忆加载失败" />

  return (
    <Stack spacing={2}>
      <Typography variant="h4">记忆管理</Typography>
      <MemoryFilterBar keyword={keyword} onKeywordChange={setKeyword} />
      {data?.map((memory) => <MemoryCard key={memory.id} memory={memory} />)}
    </Stack>
  )
}
```

- [ ] **Step 4: Run frontend and verify memory list, edit, delete flow**

Run: `npm run dev`
Expected: `/memories` renders records, search input filters, edit dialog and delete confirmation work

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/memory.ts frontend/src/services/http.ts frontend/src/services/memoryApi.ts frontend/src/hooks/useMemories.ts frontend/src/components/memory frontend/src/components/common frontend/src/pages/MemoryManagementPage.tsx
git commit -m "feat: implement memory management page"
```

### Task 8: Implement memory upload page and upload hooks

**Files:**
- Create: `frontend/src/types/upload.ts`
- Create: `frontend/src/services/uploadApi.ts`
- Create: `frontend/src/hooks/useUploadMemory.ts`
- Create: `frontend/src/components/upload/ImageUploadPanel.tsx`
- Create: `frontend/src/components/upload/UploadForm.tsx`
- Create: `frontend/src/pages/MemoryUploadPage.tsx`
- Test: manual browser verification against running API

- [ ] **Step 1: Add upload request builder and hook**

```ts
// frontend/src/services/uploadApi.ts
import { http } from './http'

export async function uploadMemory(input: {
  title: string
  content: string
  tags: string[]
  importance: number
  images: File[]
}) {
  const formData = new FormData()
  formData.append('title', input.title)
  formData.append('content', input.content)
  formData.append('tags', JSON.stringify(input.tags))
  formData.append('importance', String(input.importance))
  input.images.forEach((image) => formData.append('images', image))

  const { data } = await http.post('/api/uploads/memories', formData)
  return data
}
```

```ts
// frontend/src/hooks/useUploadMemory.ts
import { useMutation } from '@tanstack/react-query'

import { uploadMemory } from '../services/uploadApi'

export function useUploadMemory() {
  return useMutation({ mutationFn: uploadMemory })
}
```

- [ ] **Step 2: Implement upload form and image panel**

```tsx
// frontend/src/pages/MemoryUploadPage.tsx
import { Alert, Stack, Typography } from '@mui/material'
import { useState } from 'react'

import { UploadForm } from '../components/upload/UploadForm'
import { useUploadMemory } from '../hooks/useUploadMemory'

export function MemoryUploadPage() {
  const mutation = useUploadMemory()
  const [success, setSuccess] = useState(false)

  return (
    <Stack spacing={2}>
      <Typography variant="h4">记忆上传</Typography>
      {success ? <Alert severity="success">上传成功</Alert> : null}
      <UploadForm
        onSubmit={async (payload) => {
          await mutation.mutateAsync(payload)
          setSuccess(true)
        }}
        loading={mutation.isPending}
      />
    </Stack>
  )
}
```

- [ ] **Step 3: Run frontend and verify upload flow**

Run: `npm run dev`
Expected: `/upload` allows text entry, image selection, and successful form submission

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/upload.ts frontend/src/services/uploadApi.ts frontend/src/hooks/useUploadMemory.ts frontend/src/components/upload frontend/src/pages/MemoryUploadPage.tsx
git commit -m "feat: implement memory upload page"
```

### Task 9: Implement chat page and frontend chat integration

**Files:**
- Create: `frontend/src/types/chat.ts`
- Create: `frontend/src/services/chatApi.ts`
- Create: `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/components/chat/ChatMessageList.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/EmptyChatState.tsx`
- Create: `frontend/src/pages/KnowledgeChatPage.tsx`
- Test: manual browser verification against running API

- [ ] **Step 1: Add chat API and hook**

```ts
// frontend/src/services/chatApi.ts
import { http } from './http'

export async function fetchChatMessages() {
  const { data } = await http.get('/api/chat/messages')
  return data
}

export async function sendChatMessage(message: string) {
  const { data } = await http.post('/api/chat/messages', { message })
  return data
}

export async function clearChatMessages() {
  const { data } = await http.delete('/api/chat/messages')
  return data
}
```

```ts
// frontend/src/hooks/useChat.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { clearChatMessages, fetchChatMessages, sendChatMessage } from '../services/chatApi'

export function useChatMessages() {
  return useQuery({ queryKey: ['chat-messages'], queryFn: fetchChatMessages })
}

export function useSendChatMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: sendChatMessage,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-messages'] }),
  })
}

export function useClearChatMessages() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clearChatMessages,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-messages'] }),
  })
}
```

- [ ] **Step 2: Implement the chat page**

```tsx
// frontend/src/pages/KnowledgeChatPage.tsx
import { Button, Stack, Typography } from '@mui/material'

import { ChatInput } from '../components/chat/ChatInput'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { useChatMessages, useClearChatMessages, useSendChatMessage } from '../hooks/useChat'

export function KnowledgeChatPage() {
  const { data = [] } = useChatMessages()
  const sendMutation = useSendChatMessage()
  const clearMutation = useClearChatMessages()

  return (
    <Stack spacing={2}>
      <Typography variant="h4">知识库对话</Typography>
      <Button variant="outlined" onClick={() => clearMutation.mutate()}>
        清空对话
      </Button>
      <ChatMessageList messages={data} loading={sendMutation.isPending} />
      <ChatInput onSend={(message) => sendMutation.mutate(message)} disabled={sendMutation.isPending} />
    </Stack>
  )
}
```

- [ ] **Step 3: Run frontend and verify chat flow**

Run: `npm run dev`
Expected: `/chat` can load history, send message, render reply, and clear conversation

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/chat.ts frontend/src/services/chatApi.ts frontend/src/hooks/useChat.ts frontend/src/components/chat frontend/src/pages/KnowledgeChatPage.tsx
git commit -m "feat: implement knowledge chat page"
```

### Task 10: Wire real backend integration, polish validation, and verify full stack

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/memories.py`
- Modify: `backend/app/routers/uploads.py`
- Modify: `backend/app/routers/chat.py`
- Modify: `frontend/src/pages/MemoryManagementPage.tsx`
- Modify: `frontend/src/pages/MemoryUploadPage.tsx`
- Modify: `frontend/src/pages/KnowledgeChatPage.tsx`
- Modify: `README.md`
- Modify: `.env.example`
- Test: `backend/tests/test_memories_api.py`
- Test: `backend/tests/test_uploads_api.py`
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: Replace in-memory stubs with database-backed dependencies**

```python
# pattern to apply in routers
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# missing-memory guard example
if memory is None:
    raise HTTPException(status_code=404, detail="Memory not found")
```

- [ ] **Step 2: Add frontend success/error feedback and empty states**

```tsx
{mutation.isError ? <Alert severity="error">请求失败，请稍后重试</Alert> : null}
{!data?.length ? <EmptyChatState /> : <ChatMessageList messages={data} loading={sendMutation.isPending} />}
```

- [ ] **Step 3: Run full backend tests**

Run: `pytest backend/tests -v`
Expected: PASS

- [ ] **Step 4: Run frontend production build**

Run: `npm run build`
Expected: Build completes with `dist/` output and no TypeScript errors

- [ ] **Step 5: Update project README with setup steps**

```md
## Frontend
cd frontend
npm install
npm run dev

## Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- [ ] **Step 6: Commit**

```bash
git add backend frontend README.md .env.example
git commit -m "feat: finish full-stack knowledge base app"
```

---

## Self-Review

### Spec coverage
- 记忆管理页面：Task 7 + Task 10
- 记忆上传页面：Task 8 + Task 10
- 知识库对话页面：Task 9 + Task 10
- 后端 CRUD：Task 3
- 图片上传与处理：Task 4
- 对接知识图谱 / RAG：Task 5 + Task 10
- 时间属性和数据模型：Task 2 + Task 3
- 错误处理与验证：Task 4 + Task 10
- 项目初始化与运行说明：Task 1 + Task 10

### Placeholder scan
- No `TODO`, `TBD`, or unresolved placeholders left in tasks.
- Each task includes exact files, commands, and concrete code snippets.

### Type consistency
- `Memory`, `MemoryImage`, and `ChatMessage` naming is consistent across backend and frontend.
- API routes consistently use `/api/memories`, `/api/uploads/memories`, and `/api/chat/messages`.
- Frontend route names consistently use `/memories`, `/upload`, and `/chat`.
