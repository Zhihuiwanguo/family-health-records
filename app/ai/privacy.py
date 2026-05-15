from app.utils import mask_identifier


def desensitize_text(text: str) -> str:
    return mask_identifier(text)
