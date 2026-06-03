
Here is a professional and structured README.md file tailored for your Enumerak Tax Assistant chatbot. It is designed to clearly explain the project, stack, setup, and configuration (including the CORS setup we discussed) so that anyone—including you in the future—can easily understand and run it.

You can copy and paste this directly into a file named README.md in your project root folder.

Markdown
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
Create and activate a virtual environment:

Bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
Install required dependencies:

Bash
   pip install fastapi uvicorn
Run the FastAPI development server:

Bash
   uvicorn main:app --reload
The backend will be running at: http://127.0.0.1:8000

2. Frontend Setup (Next.js)
Navigate to the frontend directory:

Bash
   cd frontend
Install the node packages:

Bash
   npm install
Run the Next.js development server:

Bash
   npm run dev
The frontend will be running at: http://localhost:3000

🔒 Production Deployment & CORS Handling
When deploying live, ensure your backend main.py file whitelists both your local workspace and the live production domain of your Enumerak web deployment within the allow_origins array:

Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # Local testing URL
        "[https://www.enumerak.com](https://www.enumerak.com)",     # Production live URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
📝 License
This project is proprietary for the Enumerak platform.