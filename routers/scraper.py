from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.scraper import get_submission_code

router = APIRouter()

class FetchCodeRequest(BaseModel):
    url: str
    headless: bool = False
@router.post("/fetch-code")
def api_fetch_code(req: FetchCodeRequest):
    try:
        code = get_submission_code(req.url, headless=req.headless)
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))