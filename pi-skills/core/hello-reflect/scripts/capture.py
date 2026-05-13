#!/usr/bin/env python3
"""
Capture Learning Script for hello-reflect.
Usage: python capture.py <session_file_path>
"""
import sys
import os
import json
from pathlib import Path

# Add script directory to path for core import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reflect_core import detect_patterns, extract_user_messages

def main():
    if len(sys.argv) < 2:
        print("Usage: python capture.py <session_file_path>")
        return 1
    
    session_file = Path(sys.argv[1])
    if not session_file.exists():
        print(f"Error: Session file {session_file} not found.")
        return 1

    messages = extract_user_messages(session_file)
    if not messages:
        return 0

    # We mostly care about the last few messages for live capture
    # But for a full session reflect, we scan all.
    learnings = []
    for msg in messages:
        item_type, patterns, conf, sentiment, decay = detect_patterns(msg)
        if item_type:
            learnings.append({
                "message": msg,
                "type": item_type,
                "patterns": patterns,
                "confidence": conf
            })

    if learnings:
        print(json.dumps(learnings, indent=2, ensure_ascii=False))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
