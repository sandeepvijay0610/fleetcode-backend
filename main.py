from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from database import engine
from routers import auth, squad, dashboard, leaderboard, scraper
from services.poller import start_poller

app = FastAPI(title="FleetCode Backend", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(squad.router, prefix="/api/squad", tags=["Squad"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["Leaderboard"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["Scraper"])

@app.on_event("startup")
def on_startup():
    print("Initializing database tables...")
    SQLModel.metadata.create_all(engine)
    start_poller()
    print("FleetCode backend is online.")