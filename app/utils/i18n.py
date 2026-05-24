"""Internationalization (i18n) utility module.

Provides translation functions with support for multiple languages.
Default language is Russian (ru), with English (en) as secondary.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Request

# Supported languages
SUPPORTED_LANGUAGES = {"ru", "en"}
DEFAULT_LANGUAGE = "ru"

# In-memory cache for translations
_translations: Dict[str, Dict[str, str]] = {}


def _load_translations(lang: str) -> Dict[str, str]:
    """Load translations from JSON file for a given language."""
    if lang in _translations:
        return _translations[lang]

    translations_dir = Path(__file__).parent.parent / "translations"
    translation_file = translations_dir / f"{lang}.json"

    if not translation_file.exists():
        # Fallback to default language
        if lang != DEFAULT_LANGUAGE:
            return _load_translations(DEFAULT_LANGUAGE)
        return {}

    try:
        with open(translation_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Flatten nested dict structure
        flat_translations = {}
        _flatten_dict(data, "", flat_translations)
        _translations[lang] = flat_translations
        return flat_translations
    except (json.JSONDecodeError, IOError) as e:
        if lang != DEFAULT_LANGUAGE:
            return _load_translations(DEFAULT_LANGUAGE)
        return {}


def _flatten_dict(d: Dict[str, Any], prefix: str, result: Dict[str, str]) -> None:
    """Flatten nested dictionary into dot-notation keys."""
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _flatten_dict(value, full_key, result)
        else:
            result[full_key] = str(value)


def get_language_from_request(request: Request) -> str:
    """Extract language preference from request.

    Priority:
    1. Query parameter (?lang=en)
    2. Header (Accept-Language or X-Language)
    3. Cookie (language)
    4. Default language
    """
    # Check query parameter
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # Check headers
    lang = request.headers.get("X-Language")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # Check Accept-Language header
    accept_language = request.headers.get("Accept-Language", "")
    if accept_language:
        # Parse Accept-Language header (e.g., "en-US,en;q=0.9,ru;q=0.8")
        for lang_part in accept_language.split(","):
            lang_code = lang_part.strip().split(";")[0].split("-")[0]
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code

    # Check cookie
    lang = request.cookies.get("language") or request.cookies.get("lang")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    return DEFAULT_LANGUAGE


def translate(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    """Translate a key to the specified language.

    Args:
        key: Translation key (dot-notation, e.g., "payment.success")
        lang: Language code (auto-detected if None)
        **kwargs: Format arguments for the translation string

    Returns:
        Translated string, or the key itself if translation not found
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE

    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    translations = _load_translations(lang)
    text = translations.get(key, key)

    # Format with kwargs if provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass

    return text


def get_translations_for_language(lang: Optional[str] = None) -> Dict[str, str]:
    """Get all translations for a language."""
    if lang is None:
        lang = DEFAULT_LANGUAGE
    return _load_translations(lang)


# Convenience function for use in templates and responses
def t(key: str, request: Optional[Request] = None, **kwargs: Any) -> str:
    """Shorthand for translate with automatic language detection."""
    lang = DEFAULT_LANGUAGE
    if request is not None:
        lang = get_language_from_request(request)
    return translate(key, lang, **kwargs)
