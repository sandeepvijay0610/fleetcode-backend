import os
import time
import pickle
import re
import httpx
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

# Patch to suppress WinError 6 on Windows
_original_del = uc.Chrome.__del__
def _patched_del(self):
    try:
        _original_del(self)
    except OSError:
        pass
uc.Chrome.__del__ = _patched_del


def generate_cookies() -> int:
    headless = os.getenv("SELENIUM_HEADLESS", "false").lower() == "true"
    print(f"[Scraper] Generating cookies (headless={headless})...")
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless")

    driver = uc.Chrome(options=options, version_main=149)

    try:
        driver.get("https://leetcode.com")
        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        # Click Sign in
        try:
            driver.find_element(By.LINK_TEXT, "Sign in").click()
        except:
            print("[Scraper] Sign in link not found, maybe already on login page.")

        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(3)

        email_el = driver.find_element(By.ID, "id_login")
        password_el = driver.find_element(By.ID, "id_password")
        email_el.clear()
        email_el.send_keys(os.getenv("LEETCODE_EMAIL"))
        password_el.clear()
        password_el.send_keys(os.getenv("LEETCODE_PASSWORD"))
        password_el.send_keys(Keys.ENTER)

        print("[Scraper] Credentials submitted. Waiting for Cloudflare/auth...")
        time.sleep(20)

        cookies = driver.get_cookies()
        with open("cookies.pkl", "wb") as f:
            pickle.dump(cookies, f)

        print(f"[Scraper] Saved {len(cookies)} cookies.")
        return len(cookies)

    finally:
        driver.quit()


def get_submission_code(url: str, headless: bool = False) -> str:
    """Fetches the full code of a LeetCode submission via the GraphQL API,
    using cookies stored in cookies.pkl."""
    print(f"[Scraper] Fetching code from {url}")
    match = re.search(r"submissions/(\d+)", url)
    if not match:
        raise Exception("Invalid submission URL format.")
    submission_id = int(match.group(1))

    try:
        with open("cookies.pkl", "rb") as f:
            cookies = pickle.load(f)
            cookie_dict = {c["name"]: c["value"] for c in cookies}
    except Exception:
        raise Exception("Cookies file missing or expired. Run generate-cookies first.")

    query = """
    query submissionDetails($submissionId: Int!) {
      submissionDetails(submissionId: $submissionId) {
        code
      }
    }
    """
    csrftoken = cookie_dict.get("csrftoken", "")
    with httpx.Client(cookies=cookie_dict, headers={
        "User-Agent": "Mozilla/5.0",
        "x-csrftoken": csrftoken,
        "Referer": "https://leetcode.com/",
    }) as client:
        res = client.post("https://leetcode.com/graphql", json={
            "query": query,
            "variables": {"submissionId": submission_id},
        })
        data = res.json()
        code = data.get("data", {}).get("submissionDetails", {}).get("code")
        if not code:
            raise Exception("No code returned – cookies may be expired.")
        print("[Scraper] Code fetched successfully.")
        return code