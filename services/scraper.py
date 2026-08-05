import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

def get_submission_code(url: str) -> str:
    """Fetches the full code of a LeetCode submission via the GraphQL API,
    using cookies injected directly from the .env file."""
    print(f"[Scraper] Fetching code from {url}")
    match = re.search(r"submissions/(\d+)", url)
    if not match:
        raise Exception("Invalid submission URL format.")
    submission_id = int(match.group(1))

    # Pull directly from environment variables
    env_session = os.getenv("LEETCODE_SESSION")
    env_csrf = os.getenv("LEETCODE_CSRFTOKEN")
    
    if not env_session or not env_csrf:
        raise Exception("Cookies missing. You must set LEETCODE_SESSION and LEETCODE_CSRFTOKEN in your .env file.")

    cookie_dict = {
        "LEETCODE_SESSION": env_session,
        "csrftoken": env_csrf
    }

    query = """
    query submissionDetails($submissionId: Int!) {
      submissionDetails(submissionId: $submissionId) {
        code
      }
    }
    """
    
    with httpx.Client(cookies=cookie_dict, headers={
        "User-Agent": "Mozilla/5.0",
        "x-csrftoken": env_csrf,
        "Referer": "https://leetcode.com/",
    }) as client:
        res = client.post("https://leetcode.com/graphql", json={
            "query": query,
            "variables": {"submissionId": submission_id},
        })
        
        data = res.json()
        data_obj = data.get("data") or {}
        submission_details = data_obj.get("submissionDetails") or {}
        code = submission_details.get("code")
        
        if not code:
            raise Exception("No code returned – your .env cookies may be expired or invalid.")
            
        print("[Scraper] Code fetched successfully.")
        return code