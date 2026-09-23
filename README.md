# Smart Campus Companion

> Unified AI-powered campus support platform — chatbot, tickets, navigation, and admin panel.

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + Vite + Tailwind CSS v3 |
| **Backend** | FastAPI (Python) |
| **LLM** | DeepSeek API (OpenAI-compatible) |
| **Vector DB** | ChromaDB |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Real-time** | Native WebSockets |
| **Navigation** | Panoee iframe embed |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY

# Run the server (auto-creates DB and seeds data on first run)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at **http://localhost:5173**

## 👥 Demo Accounts

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **Student** | student@campus.edu | student123 | Chat, My Tickets, Campus Map |
| **Agent** | agent@campus.edu | agent123 | Live Queue, Ticket Claims & Replies |
| **Admin** | admin@campus.edu | admin123 | KB Management, Nav Nodes, Agent Accounts, Analytics |

## 🧪 Testing & Verification

The project includes automated test suites covering classification, API contracts, and real-time WebSockets:

```bash
cd backend

# 1. Intent Classifier Accuracy Test (62 queries, >=85% threshold)
python tests/test_classifier.py

# 2. End-to-End API Smoke Test
python tests/test_smoke.py

# 3. Native WebSocket Integration Test
python tests/test_ws.py
```

## 🏛️ Architecture

```
Student Web App → Chat Service (DeepSeek + RAG) → ChromaDB
                → Ticket Service → Native WebSocket → Agent Dashboard
                → Navigation Service (Panoee) → Admin Panel
```

## 🎯 Key Features

1. **AI Chatbot** — RAG-powered FAQ answering grounded in knowledge base entries with a graceful LLM failure fallback path.
2. **Intent Classification** — Two-call DeepSeek architecture with deterministic keyword safety net for sensitive topics (harassment, assault, corruption, fee disputes).
3. **Ticket System** — Auto-escalation of sensitive complaints with tracking IDs (`TKT-XXXX`), priority scoring, and message history.
4. **Campus Navigation** — Panoee panorama tour integration with synonym-based location search and deep-linking buttons from chat.
5. **Admin Panel** — Full CRUD for Knowledge Base, Nav Nodes, Agent Account Creation, Ticket Oversight, and live Database Analytics.
6. **Real-time Updates** — Native FastAPI WebSockets broadcasting `ticket:new`, `ticket:update`, and `ticket:message` events live.

