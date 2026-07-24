# 🤖 Enumerak Tax Assistant Chatbot

An AI-powered conversational tax assistant designed for the **Enumerak** website. This chatbot helps users with tax consultancy queries by providing instant, accurate, and context-aware responses regarding tax regulations, filing, and financial guidance.

The project follows a modern **decoupled architecture** — a high-performance Python backend paired with a lightweight, fast frontend — allowing both services to scale, deploy, and be maintained independently.

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture & Connection](#️-architecture--connection)
- [Project Structure](#-project-structure)
- [Getting Started](#️-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#1-backend-setup-fastapi)
  - [Frontend Setup](#2-frontend-setup-nextjs)
- [Environment Variables](#-environment-variables)
- [API Overview](#-api-overview)
- [Production Deployment & CORS Handling](#-production-deployment--cors-handling)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

- 💬 Real-time, AI-powered conversational chatbot for tax-related queries
- 📊 Context-aware responses covering tax regulations, filing procedures, and financial guidance
- ⚡ Fast, asynchronous communication between frontend and backend via REST API
- 🎨 Clean, responsive UI built with Tailwind CSS
- 🔐 Secure cross-origin communication with configurable CORS policies
- 🌍 Ready for both local development and production deployment

---

## 🚀 Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| **Next.js** | React framework for building the UI |
| **Tailwind CSS** | Utility-first CSS for responsive styling |
| **Fetch API** | Asynchronous client-server communication |

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | Python web framework for building the REST API |
| **Uvicorn** | Lightning-fast ASGI server implementation |
| **Pydantic** | Data validation and settings management |

---

## ⚙️ Architecture & Connection

The frontend and backend run as **separate services** and communicate securely via an **HTTP REST API** using JSON payloads.

```
┌─────────────────┐          HTTP/JSON          ┌──────────────────┐
│                  │  ────────────────────────►  │                  │
│  Next.js Client  │                              │  FastAPI Server  │
│  (Port 3000)     │  ◄────────────────────────  │  (Port 8000)     │
│                  │                              │                  │
└─────────────────┘                              └──────────────────┘
```

### CORS Configuration
To allow the Next.js frontend to securely fetch data from the Python FastAPI backend, **Cross-Origin Resource Sharing (CORS)** middleware is configured in the backend to whitelist approved domains — covering both local development and production environments.

---

## 📁 Project Structure

```
enumerak-tax-assistant/
├── backend/
│   ├── main.py              # FastAPI entry point & CORS config
│   ├── requirements.txt     # Python dependencies
│   ├── venv/                # Virtual environment (not committed)
│   └── ...                  # Routers, models, services, etc.
│
├── frontend/
│   ├── app/ or pages/        # Next.js pages/routes
│   ├── components/           # Reusable UI components
│   ├── public/                # Static assets
│   ├── package.json
│   └── ...
│
└── README.md
```

---

## 🛠️ Getting Started

### Prerequisites

Make sure the following are installed on your machine before proceeding:

- **Node.js** v18 or higher — [Download here](https://nodejs.org/)
- **Python** 3.9 or higher — [Download here](https://www.python.org/)
- **npm** or **yarn** (comes with Node.js)
- **pip** (comes with Python)

Verify installations:
```bash
node -v
python --version
pip --version
```

---

### 1. Backend Setup (FastAPI)

**Step 1 — Navigate to the backend directory:**
```bash
cd backend
```

**Step 2 — Create and activate a virtual environment:**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**Step 3 — Install required dependencies:**
```bash
pip install fastapi uvicorn
```

> 💡 **Tip:** If you have a `requirements.txt` file, install everything in one go instead:
> ```bash
> pip install -r requirements.txt
> ```

**Step 4 — Run the FastAPI development server:**
```bash
uvicorn main:app --reload
```

✅ The backend will be running at: **http://127.0.0.1:8000**

📖 Interactive API docs (Swagger UI) will be available at: **http://127.0.0.1:8000/docs**

---

### 2. Frontend Setup (Next.js)

**Step 1 — Navigate to the frontend directory:**
```bash
cd frontend
```

**Step 2 — Install the node packages:**
```bash
npm install
```

**Step 3 — Run the Next.js development server:**
```bash
npm run dev
```

✅ The frontend will be running at: **http://localhost:3000**

---

## 🔑 Environment Variables

Create a `.env.local` file inside the `frontend/` directory to store the backend API URL:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Create a `.env` file inside the `backend/` directory for backend-specific secrets (API keys, database URLs, etc.):

```env
OPENAI_API_KEY=your_api_key_here
ALLOWED_ORIGINS=http://localhost:3000,https://www.enumerak.com
```

> ⚠️ **Important:** Never commit `.env` or `.env.local` files to version control. Add them to `.gitignore`.

---

## 📡 API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check / welcome route |
| `POST` | `/chat` | Sends a user query and returns the chatbot's response |
| `GET` | `/docs` | Auto-generated Swagger API documentation |

**Example Request:**
```json
POST /chat
{
  "message": "What is the tax filing deadline for this year?"
}
```

**Example Response:**
```json
{
  "response": "The standard tax filing deadline is typically April 15th, but this may vary based on your jurisdiction..."
}
```

---

## 🔒 Production Deployment & CORS Handling

When deploying live, ensure your backend `main.py` file whitelists both your local workspace and the live production domain of your Enumerak web deployment within the `allow_origins` array:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",        # Local testing URL
        "https://www.enumerak.com",     # Production live URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Deployment Checklist
- [ ] Set `DEBUG=False` in production environment
- [ ] Use environment variables for all secrets (never hardcode API keys)
- [ ] Restrict `allow_origins` to only trusted domains (avoid using `"*"` in production)
- [ ] Use HTTPS for both frontend and backend in production
- [ ] Run the backend behind a production-grade process manager (e.g., Gunicorn + Uvicorn workers, or a containerized setup)
- [ ] Set up proper logging and monitoring

---

## 🐞 Troubleshooting

**Issue: CORS error in browser console**
> Make sure the frontend's origin (e.g., `http://localhost:3000`) is listed in the backend's `allow_origins` array, and that the backend server has been restarted after changes.

**Issue: `uvicorn: command not found`**
> Ensure your virtual environment is activated and `uvicorn` was installed inside it.

**Issue: Frontend can't reach backend API**
> Confirm the backend is running on the expected port and that `NEXT_PUBLIC_API_URL` in `.env.local` matches the backend's address.

---

## 🗺️ Roadmap

- [ ] Add user authentication for personalized tax history
- [ ] Integrate multi-language support for regional tax queries
- [ ] Add conversation history persistence (database-backed)
- [ ] Deploy backend and frontend to production infrastructure
- [ ] Add automated testing (pytest for backend, Jest for frontend)

---

## 🤝 Contributing

This is currently a proprietary project for Enumerak. If you're part of the internal team:

1. Create a new branch for your feature/fix
2. Commit your changes with clear messages
3. Open a pull request for review before merging to `main`

---

## 📝 License

This project is **proprietary** for the Enumerak platform. All rights reserved. Unauthorized copying, distribution, or use of this software, in whole or in part, is strictly prohibited without prior written permission.