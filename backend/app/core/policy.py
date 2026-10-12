"""Policy checks shared by API and agent entry points."""

import re


INJECTION_PATTERN = re.compile(
    r"ignore (all|previous|prior)|reveal (system|hidden) prompt|bypass (the )?mandate",
    re.IGNORECASE,
)


def contains_prompt_injection(text: str) -> bool:
    return INJECTION_PATTERN.search(text) is not None
