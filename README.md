# FleetCode Backend

A FastAPI-based asynchronous backend service for **FleetCode**, a platform designed to manage coding squads, track competitive programming and LeetCode performance, detect code plagiarism, run automated scraping tasks, and monitor user progress via dashboards and leaderboards.

---

## 🛠️ Tech Stack & Architecture

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python)


* **Task Queue & Scheduler:** [Celery](https://docs.celeryq.dev/) with Celery Beat


* **Database:** Relational Database (SQLAlchemy / PostgreSQL / SQLite)


* **Containerization:** Docker & Docker Compose


* **Asynchronous Execution:** Asyncio for web scraping and scheduled polling



---

## 📂 Project Structure

```text
fleetcode-backend-main/
├── .dockerignore
├── .gitignore
├── Dockerfile                  # Container definition for API and Celery workers
├── docker-compose.yaml         # Multi-container setup (API, Celery Beat, Workers, DB/Broker)
├── requirements.txt            # Python dependencies
├── main.py                     # Application entry point and router registrations
├── database.py                 # Database connections and session management
├── models.py                   # SQLAlchemy ORM models
├── celery_app.py               # Celery configuration and initialization
├── tasks.py                    # Celery asynchronous background tasks
├── backfill_topics.py          # Data migration/backfill utility script
├── routers/                    # API Route Handlers
│   ├── __init__.py
│   ├── auth.py                 # User authentication & JWT management
│   ├── dashboard.py            # User stats, metrics, and progress summaries
│   ├── leaderboard.py          # Squad & global user rankings
│   ├── scraper.py              # On-demand scraping trigger endpoints
│   └── squad.py                # Squad creation, management, and membership
└── services/                   # Business Logic & Core Drivers
    ├── __init__.py
    ├── plagiarism.py           # Code similarity and anti-cheat checking
    ├── poller.py               # Periodic automated background monitoring
    └── scraper.py              # Web scrapers for coding platforms (e.g., LeetCode)

```

---

## ✨ Features

1. **Authentication (`routers/auth.py`)**
* User sign-up, login, token-based authentication, and access control.




2. **Squad Management (`routers/squad.py`)**
* Create, join, and manage competitive programming groups/squads.




3. **Dashboard & Metrics (`routers/dashboard.py`)**
* Detailed user progress visualization, problem difficulty metrics, and solved statistics.




4. **Leaderboard (`routers/leaderboard.py`)**
* Dynamic user and squad ranking systems based on solved problems and scores.




5. **Automated Polling & Scraping (`services/scraper.py`, `services/poller.py`)**
* Automated submission tracking and profile scraping to keep statistics up to date without manual user input.




6. **Plagiarism Detection (`services/plagiarism.py`)**
* Code comparison tools to evaluate submission integrity and detect duplicate/plagiarized code within squads.




7. **Asynchronous Background Processing (`celery_app.py`, `tasks.py`)**
* Scheduled tasks via Celery Beat for non-blocking periodic background jobs.





---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* Docker & Docker Compose (Optional, for containerized setup)
* Redis / RabbitMQ (as Celery message broker)

---

### Local Setup (Without Docker)

1. **Clone the repository:**
```bash
git clone <repository-url>
cd fleetcode-backend-main

```


2. **Create and activate a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

```


3. **Install dependencies:**
```bash
pip install -r requirements.txt

```


4. **Run the FastAPI server:**
```bash
uvicorn main:app --reload

```


The API will be accessible at `[http://127.0.0.1:8000](http://127.0.0.1:8000)`.
Interactive API documentation (Swagger UI) will be available at `[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)`.
5. **Start Celery Worker & Beat (Separate terminal instances):**
```bash
# Worker
celery -A celery_app worker --loglevel=info

# Beat Scheduler
celery -A celery_app beat --loglevel=info

```



---

### Docker Setup

To run the complete stack (API, database, message broker, and Celery worker/beat) with a single command:

```bash
docker-compose up --build

```

---

## 🛠️ Utilities & Maintenance

* **Backfill Topics:**
If topic tags or historic data need backfilling into the database, run:
```bash
python backfill_topics.py

```
