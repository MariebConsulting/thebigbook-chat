def enforce_quote_policy(text: str, max_chars: int = 1200) -> str:
    # Optional last-ditch clamp if the model got too long.
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"
