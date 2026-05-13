#!/usr/bin/env python3
"""
Reflect Core - Distilled from BayramAnnakov/claude-reflect
Provides pattern detection and learning extraction logic for Pi.
"""
import json
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

# --- Pattern Definitions (Distilled) ---

EXPLICIT_PATTERNS = [(r"remember:", "remember:", 0.90, 120)]
POSITIVE_PATTERNS = [
    (r"perfect!|exactly right|that's exactly", "perfect", 0.70, 90),
    (r"keep doing this|love it|nailed it", "keep-doing", 0.70, 90),
]
CORRECTION_PATTERNS = [
    (r"^no[,. ]+", "no,", True),
    (r"^don't\b|^do not\b", "don't", True),
    (r"^stop\b|^never\b", "stop/never", True),
    (r"that's (wrong|incorrect)", "that's-wrong", True),
    (r"^I meant\b|^I said\b", "I-meant/said", True),
    (r"^I told you\b", "I-told-you", True),
    (r"use .{1,30} not\b", "use-X-not-Y", True),
]
GUARDRAIL_PATTERNS = [
    (r"don't (?:add|include|create) .{1,40} unless", "dont-unless-asked", 0.90, 120),
    (r"only (?:change|modify|edit|touch) what I (?:asked|requested|said)", "only-what-asked", 0.90, 120),
    (r"stop (?:refactoring|changing|modifying|editing) (?:unrelated|other|surrounding)", "stop-unrelated", 0.90, 120),
    (r"leave .{1,30} (?:alone|unchanged|as is)", "leave-alone", 0.85, 90),
]
FALSE_POSITIVE_PATTERNS = [
    r"[?\uff1f]$", r"[\u55ce\u5417\u5462\u304b\uae4c]$",
    r"^(please|can you|could you|would you|help me)\b",
    r"(help|fix|check|review)\s+(this|that|it|the)\b",
    r"(error|failed|could not|cannot|can't|unable to)\s+\w+",
]
CJK_CORRECTION_PATTERNS = [
    (r"^不是[，,. ]", "bushi", True),
    (r"^错了|^錯了", "cuole", True),
    (r"不要.{0,20}要", "buyao-yao", True),
]

def detect_patterns(text: str) -> Tuple[Optional[str], str, float, str, int]:
    stripped = text.strip()
    has_cjk = bool(re.search(r'[\u3000-\u9fff\uf900-\ufaff\uac00-\ud7af]', stripped))
    if len(stripped) <= (2 if has_cjk else 4):
        return (None, "", 0.0, "correction", 90)

    for p, n, c, d in EXPLICIT_PATTERNS:
        if re.search(p, text, re.IGNORECASE): return ("explicit", n, c, "correction", d)
    for p, n, c, d in GUARDRAIL_PATTERNS:
        if re.search(p, text, re.IGNORECASE): return ("guardrail", n, c, "correction", d)
    for p in FALSE_POSITIVE_PATTERNS:
        if re.search(p, text, re.IGNORECASE): return (None, "", 0.0, "correction", 90)

    # CJK
    for p, n, strong in CJK_CORRECTION_PATTERNS:
        if re.search(p, stripped):
            conf = 0.75 if strong else 0.60
            return ("auto", n, conf, "correction", 90)

    # English
    matched = []
    has_strong = False
    for p, n, strong in CORRECTION_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            matched.append(n)
            if strong: has_strong = True

    if matched:
        conf = 0.70 if has_strong else 0.55
        return ("auto", " ".join(matched), conf, "correction", 60)

    return (None, "", 0.0, "correction", 90)

def extract_user_messages(session_file: Path) -> List[str]:
    """Extract user messages from Pi session file (jsonl)."""
    if not session_file.exists(): return []
    messages = []
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("role") == "user":
                        content = entry.get("content", "")
                        if isinstance(content, str) and content.strip():
                            messages.append(content)
                except: continue
    except: pass
    return messages
