"""i18n routes for API v2.

Provides endpoints for fetching translations and managing language preferences.
"""

from fastapi import APIRouter, Request
from typing import Dict, Any, List

from app.utils.i18n import (
    get_translations_for_language,
    get_language_from_request,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    translate,
)

router = APIRouter()


@router.get("/i18n/translations")
async def get_translations(request: Request) -> Dict[str, Any]:
    """Get all translations for the detected language.

    Language is detected from query params, headers, cookies, or defaults to 'ru'.
    """
    lang = get_language_from_request(request)
    translations = get_translations_for_language(lang)

    return {
        "language": lang,
        "translations": translations,
    }


@router.get("/i18n/languages")
async def get_supported_languages() -> Dict[str, Any]:
    """Get list of supported languages."""
    return {
        "supported_languages": list(SUPPORTED_LANGUAGES),
        "default_language": DEFAULT_LANGUAGE,
    }


@router.get("/i18n/translate/{key}")
async def translate_key(key: str, request: Request, lang: str = None) -> Dict[str, Any]:
    """Translate a specific key.

    - **key**: Translation key in dot-notation (e.g., "payment.success")
    - **lang**: Optional language override (defaults to detected language)
    """
    target_lang = lang or get_language_from_request(request)
    if target_lang not in SUPPORTED_LANGUAGES:
        target_lang = DEFAULT_LANGUAGE

    text = translate(key, target_lang)

    return {
        "key": key,
        "language": target_lang,
        "translation": text,
    }
