import difflib
import re


def sanitize_code(code: str) -> str:
    if not code:
        return ""
    # Remove single-line comments
    code = re.sub(r"#.*", "", code)
    code = re.sub(r"//.*", "", code)
    # Remove all whitespace
    code = re.sub(r"\s+", "", code)
    return code


def check_similarity(code1: str, code2: str) -> float:
    if not code1 or not code2:
        return 0.0
    s1 = sanitize_code(code1)
    s2 = sanitize_code(code2)
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()