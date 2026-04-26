# AI-Powered Adaptive Programming Quiz Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

> **Final Year Project** — Development of an AI-Powered Web Platform for Adaptive Programming Quizzes and Practical Learning

A full-stack web application that generates personalised, AI-driven programming quizzes and coding challenges in real time. Users specify a topic, programming language, and number of questions. The platform uses a large language model to produce either multiple-choice questions or practical coding challenges, assigns a difficulty rating predicted by a trained machine learning model, and provides a live in-browser code editor where users can write, run, and submit solutions against automated test cases.

Adaptive difficulty is a core design goal. Rather than hardcoding difficulty, the system infers it through an ML pipeline trained on IBM Project CodeNet, a dataset of over four million competitive programming submissions across more than 4000 problems. A second ML model performs multi-label topic classification, trained on a LeetCode dataset, tagging each generated question with its primary algorithmic categories before it is returned to the user.

## Screencast Demo

[![Watch on YouTube](https://img.shields.io/badge/Watch%20Demo-YouTube-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/watch?v=aBWo7vzyTZA)

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Core Features](#core-features)
3. [Quick Start](#quick-start)
4. [Project Structure](#project-structure)
5. [Environment Variables](#environment-variables)
6. [Setup and Running](#setup-and-running)
7. [Docker Deployment](#docker-deployment)
8. [Testing](#testing)
9. [API Reference](#api-reference)
10. [Machine Learning Models](#machine-learning-models)
11. [Security Notes](#security-notes)
12. [AI Usage Declaration](#ai-usage-declaration)
13. [Author](#author)

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Bootstrap 5 |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Database | PostgreSQL 16 via psycopg3 |
| AI Generation | OpenAI GPT-4o-mini, Ollama Llama 3.1:8b |
| Difficulty ML | scikit-learn (Random Forest, Gradient Boosting, XGBoost, SVM, Logistic Regression, kNN) |
| Topic ML | Multi-label Logistic Regression (One-vs-Rest) trained on LeetCode data |
| Code Execution | Server-side subprocess sandboxing (Python, JavaScript) |
| Authentication | JWT (PyJWT) with bcrypt password hashing, SMTP email verification |
| In-Browser Editor | Monaco Editor |
| Containerisation | Docker, Docker Compose |
| Data Visualisation | Recharts |

---

## Core Features

### Quiz Generation

Users navigate to the prompt page, select a programming language and topic, choose the number of questions (1 to 20), and select between two quiz types. The prompt is sent to the backend, which constructs a structured system instruction from a format guide and forwards it to the active AI model. The response is parsed server-side into a validated Pydantic schema before being returned to the frontend.

### Multiple-Choice Quizzes

AI-generated MCQ quizzes present the user with a question and four answer options. Users answer each question, receive immediate feedback, and earn XP for correct answers. An AI-powered hint system is available on demand, which calls a dedicated backend endpoint to generate contextual hints for any question without revealing the answer.

### Coding Challenges

Coding questions include a problem description, language-specific starter code, and a set of test cases. The user writes their solution in the Monaco editor embedded in the browser. Code can be run freely against visible inputs at any point, and submitted when ready. Submissions are executed server-side and evaluated against the full test suite. Results display pass or fail status per test case alongside actual and expected output.

### Adaptive Difficulty Prediction

Every generated question is automatically classified as easy, medium, or hard before it reaches the user. The backend difficulty service loads a trained scikit-learn pipeline once at startup and applies it at inference time. The pipeline extracts numeric features including time and memory limits, estimated acceptance rate, average CPU time and code size, and character and word count of the problem description. TF-IDF vectorisation is applied to the full description text, and a keyword detector identifies topic categories such as dynamic programming, graph traversal, recursion, sorting, binary search, string manipulation, greedy algorithms, and stack-based problems.

### Automatic Topic Tagging

A multi-label classifier predicts algorithmic topic tags for each generated question. The classifier is trained on a LeetCode dataset and is capable of assigning multiple tags per question, such as Array, Hash Table, Dynamic Programming, Graph, String, and Tree. Tags are attached to the question response and displayed to the user.

### User Accounts and Progression

Users register with email verification via SMTP. Passwords are hashed with bcrypt before storage. Upon login, a 24-hour JWT is issued and stored client-side. Authenticated users have a profile page showing their current XP total, level, quiz history, and statistics. XP is awarded on quiz completion, and level boundaries are recalculated server-side.

### Social Features

Authenticated users can search for other users, view public profiles, send and respond to friend requests, and browse a social feed. Statistics pages are visible to friends. Users can customise their display name, bio, and avatar.

### AI Model Switching

The platform supports switching between OpenAI GPT-4o-mini and a locally hosted Llama 3.1:8b model via Ollama. The active model is stored in application state on the backend and can be changed at runtime via the frontend settings without restarting the server.

### Code Sandbox

A standalone code sandbox page provides a free-form editor where users can write and execute code in any supported language outside of the quiz context.

---

## Quick Start

The fastest way to get the platform running is via Docker Compose. Ensure Docker Desktop is installed, then:

1. Clone the repository and navigate to the project root.
2. Copy the environment variable example and fill in your values:

```bash
cp .env.example .env
```

3. Ensure the trained ML model files are present (see [Machine Learning Models](#machine-learning-models)):

```
ml_models/difficulty_classifier/difficulty_model.pkl
ml_models/tag_classifier/topic_model.pkl
```

4. Start all services:

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

For local development without Docker, see [Setup and Running](#setup-and-running).

---

## Project Structure

```
backend/
    main.py                  FastAPI application entry point and route definitions
    config.py                Environment configuration and constants
    db.py                    Database connection management
    pydantic_models.py       Request and response schemas
    core/
        auth.py              JWT creation, verification, and bcrypt utilities
    services/
        ai_models.py         OpenAI and Ollama request handling with retry logic
        code_executor.py     Subprocess-based code execution and test case evaluation
        users.py             User management, XP system, social features, and email
    ml/
        difficulty_service.py  Loads difficulty model and runs inference
        tag_service.py         Loads topic model and predicts algorithmic tags
    parsers/
        parser_openai.py     Parses and validates OpenAI API responses
        parser_ollama.py     Parses and validates Ollama API responses
    tests/
        test_example.py      pytest test suite

frontend/
    src/
        components/
            App.tsx           Root router and auth provider
            StatsPage.tsx     User statistics dashboard
            auth/             Registration, login, and email verification pages
            layout/           Navbar and shared layout components
            pages/            Landing, prompt, quiz, profile, social, sandbox pages
            ui/               Reusable UI components (ComboBox, PromptForm)
        hooks/
            useHint.tsx       Custom hook for the MCQ hint system
        utils/
            AuthContext.tsx   Global authentication state via React context

ml_models/
    difficulty_classifier/
        difficulty_predictor.py   Training script for difficulty classifier
        difficulty_model.pkl      Serialised scikit-learn pipeline (generated)
    tag_classifier/
        train.py                  Training script for topic tag classifier
        predict.py                Inference utilities for topic prediction
        topic_model.pkl           Serialised multi-label classifier (generated)
        leetcode.csv              Training dataset

docs/
    dissertation/             LaTeX source for the written dissertation
    ml_docs/                  Training figures and evaluation outputs
```

---

## Environment Variables

Create a `.env` file in the project root before running the backend or Docker Compose.

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (for OpenAI) | OpenAI API key |
| `JWT_SECRET` | Yes | Secret key for signing JWT tokens |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `APP_BASE_URL` | No | Base URL for email verification links (default: `http://localhost:5173`) |
| `SMTP_HOST` | No | SMTP server hostname for email verification |
| `SMTP_PORT` | No | SMTP port (default: `587`) |
| `SMTP_USERNAME` | No | SMTP account username |
| `SMTP_PASSWORD` | No | SMTP account password |
| `SMTP_FROM` | No | Sender address for verification emails |
| `SMTP_USE_TLS` | No | Enable TLS for SMTP (`true` by default) |
| `POSTGRES_USER` | Docker only | PostgreSQL username for Docker Compose (default: `fyp`) |
| `POSTGRES_PASSWORD` | Docker only | PostgreSQL password for Docker Compose |
| `POSTGRES_DB` | Docker only | PostgreSQL database name for Docker Compose (default: `fyp`) |
| `CODENET_PATH` | ML training only | Path to a local IBM Project CodeNet installation |

Example `.env`:

```dotenv
OPENAI_API_KEY=sk-...
JWT_SECRET=change-me-in-production
DATABASE_URL=postgresql://fyp:password@localhost:5432/fyp
APP_BASE_URL=http://localhost:5173

# Docker Compose
POSTGRES_PASSWORD=password

# SMTP (optional — omit to disable email verification)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=no-reply@example.com
```

> **Security:** Never commit your `.env` file to version control. Add it to `.gitignore`.

---

## Setup and Running

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Backend runtime |
| Node.js | 22+ | Frontend build tooling |
| PostgreSQL | 16 | Can be run via Docker |
| OpenAI API key | — | Required for GPT-4o-mini |
| Ollama | latest | Optional, for local LLM |

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend development server will be available at `http://localhost:5173`.

### Local LLM via Ollama (Optional)

Install Ollama from [ollama.com](https://ollama.com) and pull the Llama 3.1 8B model:

```bash
ollama pull llama3.1:8b
ollama serve
```

Once running, the active model can be switched from the frontend settings page without restarting the backend.

---

Install Ollama from [ollama.com](https://ollama.com) and pull the Llama 3.1 8B model:

```bash
ollama pull llama3.1:8b
ollama serve
```

Once running, the active model can be switched from the frontend without restarting the backend.

## Docker Deployment

The project includes a `docker-compose.yml` that brings up the PostgreSQL database, FastAPI backend, and Nginx-served frontend as a single stack.

Ensure the trained model files are present before building:

```
ml_models/difficulty_classifier/difficulty_model.pkl
ml_models/tag_classifier/topic_model.pkl
```

Build and start all services:

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

The database service includes a health check. The backend waits for PostgreSQL to be ready before starting. All services restart automatically unless stopped.

To stop and remove containers:

```bash
docker compose down
```

To stop and remove containers **including the database volume** (destructive):

```bash
docker compose down -v
```

---

## Testing

The backend uses pytest. Test files are located in `backend/tests/`.

```bash
cd backend
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_example.py
```

Generate a coverage report:

```bash
pytest --cov=. --cov-report=html
```

---

## API Reference

All authenticated endpoints require an `Authorization: Bearer <token>` header containing the JWT returned by `/login`.

### AI and Quiz

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/prompt` | Generate a quiz or coding challenge | No |
| `POST` | `/model` | Switch the active AI model (`openai` or `llama3.1:8b`) | Yes |
| `POST` | `/hint/mcq` | Generate a contextual hint for an MCQ question | No |

### Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/register` | Register a new user account | No |
| `POST` | `/login` | Authenticate and receive a JWT token | No |
| `GET` | `/verify-email` | Verify email address via token | No |
| `POST` | `/resend-verification` | Resend the verification email | No |

### User Profile

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/me` | Get the authenticated user's profile | Yes |
| `PATCH` | `/me/profile` | Update display name, bio, or avatar | Yes |
| `POST` | `/add-xp` | Award XP to the authenticated user | Yes |
| `GET` | `/user-stats` | Get aggregated quiz statistics | Yes |
| `GET` | `/quiz-history` | Get the last 20 quiz sessions | Yes |
| `POST` | `/save-quiz-result` | Save a completed quiz result | Yes |
| `POST` | `/quiz-session` | Save a full quiz session with per-question detail | Yes |

### Social

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/users/search` | Search users by name or email | Yes |
| `GET` | `/users/{user_id}/profile` | Get a user's public profile | Yes |
| `GET` | `/users/{user_id}/stats` | Get a user's statistics (friends only) | Yes |
| `POST` | `/friends/request/{addressee_id}` | Send a friend request | Yes |
| `POST` | `/friends/respond` | Accept or reject a friend request | Yes |
| `GET` | `/friends/requests` | List pending incoming friend requests | Yes |
| `GET` | `/friends/requests/pending-count` | Get count of pending friend requests | Yes |
| `GET` | `/friends` | List confirmed friends | Yes |
| `DELETE` | `/friends/{friend_id}` | Remove a friend | Yes |
| `GET` | `/friends/count` | Get friend count | Yes |

### Code Execution

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/run-code` | Execute code and return stdout/stderr | No |
| `POST` | `/submit-code` | Run code against test cases and return results | No |

### System

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/health` | Health check — returns `{"status": "alive"}` | No |

---

## Machine Learning Models

### Difficulty Classifier

The difficulty classifier is trained on IBM Project CodeNet, an open dataset published by IBM Research containing over 14 million code submissions across more than 4000 competitive programming problems in 50 languages. The training script reads problem-level metadata (time limits, memory limits), aggregates per-submission statistics (acceptance rate, average CPU time, memory usage, code size), and parses HTML problem descriptions to extract TF-IDF features and algorithmic keyword signals. Six classifiers are trained and evaluated: Random Forest, Gradient Boosting, XGBoost, Linear SVM, Logistic Regression, and kNN. The best-performing pipeline is serialised to `ml_models/difficulty_classifier/difficulty_model.pkl`.

To retrain from scratch, a local installation of IBM Project CodeNet is required. Set `CODENET_PATH` in `.env` to the dataset root, then run:

```bash
python ml_models/difficulty_classifier/difficulty_predictor.py
```

### Topic Tag Classifier

The topic classifier is a multi-label model trained on a LeetCode problem dataset. It predicts one or more algorithmic topic tags per question, such as Array, Hash Table, String, Dynamic Programming, Graph, Tree, Binary Search, and others. Tags with fewer than 60 training samples are excluded. The model uses TF-IDF features over question titles and descriptions with a One-vs-Rest Logistic Regression classifier. It is serialised to `ml_models/tag_classifier/topic_model.pkl`.

To retrain:

```bash
python ml_models/tag_classifier/train.py
```

Both trained model files must be present for the backend to perform difficulty and tag prediction at runtime. If either file is missing, the backend will start but predictions will be skipped for the unavailable model.

---

## Security Notes

- **Code execution** uses `subprocess.run()` with a timeout and captures output from a temporary file. This provides basic isolation suitable for a development or demonstration environment. It does **not** provide OS-level sandboxing. Production deployments requiring untrusted code execution should use a container-based or VM-based sandbox such as nsjail, gVisor, or Firecracker.
- **JWT tokens** are signed with `HS256` using the `JWT_SECRET` environment variable. Use a cryptographically random value of at least 32 bytes in production.
- **Passwords** are hashed with bcrypt before storage. Plain-text passwords are never persisted.
- **CORS** is restricted to `localhost:5173`, `localhost:3000`, and `127.0.0.1:8000` by default. Update `CORS_ORIGINS` in `config.py` for production deployments.

---

## AI Usage Declaration

Generative AI tools were used during the development of this project in a supplementary capacity, consistent with responsible academic practice. AI was used to assist with routine coding tasks, clarify technical concepts, and help debug implementation issues. All design decisions, architectural choices, and written work are the author's own. AI-generated content was reviewed, adapted, and integrated only where it was accurate and appropriate.

### Examples of AI Assistance

**Prompt:** "In Python, what is the correct way to load a scikit-learn pipeline from a pickle file exactly once at module import time so that inference requests do not repeatedly deserialise the model?"

**Response summary:** The AI explained using a module-level variable initialised to `None` and a `_load_model()` helper that checks this guard before calling `joblib.load()`. It noted that this pattern ensures the model is deserialised only on the first call and reused for all subsequent requests within the same process lifetime.

---

**Prompt:** "How does One-vs-Rest multi-label classification work, and why would I choose it over a classifier chain for a topic tagging task?"

**Response summary:** The AI explained that One-vs-Rest trains one independent binary classifier per label, making it straightforward to tune per-label decision thresholds after training. It noted that classifier chains model label correlations but are slower to train and more sensitive to label ordering. For a topic tagging task where labels are largely independent, One-vs-Rest was described as a practical and interpretable choice.

---

**Prompt:** "I am using FastAPI with JWT authentication. How do I protect an endpoint so that only authenticated users can access it, and how do I extract the user ID from the token inside the route?"

**Response summary:** The AI showed how to use `Depends()` with a custom `verify_token` function that reads the `Authorization` header via `HTTPBearer`, decodes the JWT with `PyJWT`, and returns the payload as a dict. It demonstrated injecting this dependency directly into the route signature so the decoded payload is available without writing repeated boilerplate in each handler.

---

**Prompt:** "What is a safe and simple way to run user-submitted Python and JavaScript code server-side in a subprocess with a timeout?"

**Response summary:** The AI outlined using Python's `subprocess.run()` with `timeout`, `capture_output=True`, and writing the submitted code to a temporary file via `tempfile.NamedTemporaryFile`. It highlighted the importance of cleaning up the temporary file after execution and treating all subprocess output as untrusted. It also noted that true sandboxing requires OS-level isolation and that the subprocess approach carries inherent risk in a production environment.

---

## Author

**Fionn McGoldrick** — G00422349  
Atlantic Technological University

---

*This project was submitted in partial fulfilment of the requirements for the Bachelor of Science (Honours) in Software Development.*
