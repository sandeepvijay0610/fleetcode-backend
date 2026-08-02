from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.scraper import generate_cookies, get_submission_code

router = APIRouter()


class FetchCodeRequest(BaseModel):
    url: str
    headless: bool = False


@router.post("/generate-cookies")
def api_generate_cookies(headless: bool = False):
    try:
        num_cookies = generate_cookies(headless)
        return {
            "message": f"Successfully authenticated and saved {num_cookies} cookies."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-code")
def api_fetch_code(req: FetchCodeRequest):
    try:
        code = get_submission_code(req.url, headless=req.headless)
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))