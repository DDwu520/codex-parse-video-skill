#!/usr/bin/env python3
"""生成同时兼容 macOS 与 Windows 的交付目录名。"""

from __future__ import annotations

from datetime import date
import hashlib
import re
import unicodedata


INVALID_COMPONENT = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")
WINDOWS_RESERVED = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


def safe_component(value: str, *, max_length: int = 80) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = INVALID_COMPONENT.sub("_", normalized)
    normalized = WHITESPACE.sub(" ", normalized).strip(" .")
    if not normalized:
        normalized = "未命名视频"
    stem = normalized.split(".", 1)[0].casefold()
    if stem in WINDOWS_RESERVED:
        normalized = f"_{normalized}"
    if len(normalized) > max_length:
        normalized = normalized[:max_length].rstrip(" .")
    return normalized or "未命名视频"


def delivery_folder_name(
    *,
    platform: str,
    title: str,
    source_url: str,
    day: date | None = None,
    max_length: int = 120,
) -> str:
    current_day = day or date.today()
    prefix = f"{safe_component(platform, max_length=24)}-{current_day:%Y%m%d}-"
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:8]
    suffix = f"-{digest}"
    title_limit = max(12, max_length - len(prefix) - len(suffix))
    safe_title = safe_component(title, max_length=title_limit)
    return f"{prefix}{safe_title}{suffix}"
