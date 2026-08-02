import os
from sqlmodel import create_engine, Session 
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("URL not set in environment")

engine = create_engine(DATABASE_URL, echo = False)

def get_session():
    with Session(engine) as session:
        yield session

