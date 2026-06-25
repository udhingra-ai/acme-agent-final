import re
from fastapi import HTTPException

_PATTERNS = [
    r'ignore\s+(?:all\s+)?(?:previous|above|prior|all)\s+(instructions?|rules?|context|system)',
    r'disregard\s+.{0,40}\s+(instructions?|rules?|system\s+prompt)',
    r'you\s+are\s+now\s+.{0,60}(assistant|AI|bot|GPT|claude|unrestricted)',
    r'act\s+as\s+(?:if\s+you\s+are\s+)?(?:an?\s+)?(?:new|different|unrestricted|evil)',
    r'<\s*system\s*>',
    r'\[system\s*:',
    r'\bjailbreak\b',
    r'\bDAN\b.{0,30}\bmode\b',
    r'reveal\s+(?:your\s+)?(?:system\s+prompt|instructions|context|internal)',
    r'output\s+(?:all|entire|every|raw|complete)\s+(?:data|database|records|customers?|users?)',
    r'bypass\s+(?:security|rbac|auth(?:entication|orization)?|rate.?limit|guardrails?)',
    r';\s*(?:drop|delete|truncate|alter)\s+(?:table|database|index)',
    r"'\s*(?:or|and)\s+'?1\s*'?\s*=\s*'?1",
    r'--\s+',  # SQL comment injection
    r'\/\*.*?\*\/',  # SQL block comment
]

_compiled = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _PATTERNS]


def check_prompt(text: str) -> None:
    """Raise HTTP 400 if query matches a known injection or exfiltration pattern."""
    for pat in _compiled:
        if pat.search(text):
            raise HTTPException(
                status_code=400,
                detail='Query contains disallowed patterns. Please rephrase your request.',
            )
