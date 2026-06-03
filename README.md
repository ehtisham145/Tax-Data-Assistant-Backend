# Enumerak Tax Assistant Chatbot

An AI-powered conversational tax assistant designed for the **Enumerak** website. This chatbot helps users with tax consultancy queries by providing instant, accurate, and context-aware responses regarding tax regulations, filing, and financial guidance.

The project is split into a modern decoupled architecture: a high-performance Python backend and a lightweight, fast frontend.

---

## 🚀 Tech Stack

### Frontend
* **Next.js** (React Framework)
* **Tailwind CSS** (For responsive UI styling)
* **Fetch API** (For asynchronous client/server communication)

### Backend
* **FastAPI** (Python Web Framework)
* **Uvicorn** (Lightning-fast ASGI server implementation)
* **Pydantic** (Data validation and settings management)

---

## ⚙️ Architecture & Connection

The frontend and backend run as separate services and communicate securely via an HTTP REST API using JSON payloads. 

### CORS Configuration
To allow the Next.js frontend to securely fetch data from the Python FastAPI backend, Cross-Origin Resource Sharing (CORS) middleware is configured in the backend to whitelist approved domains (Local development and Production domains).

---

## 🛠️ Getting Started

### Prerequisites
* Node.js (v18 or higher)
* Python (3.9 or higher)

---

### 1. Backend Setup (FastAPI)

1. Navigate to the backend directory:
```bash
   cd backend