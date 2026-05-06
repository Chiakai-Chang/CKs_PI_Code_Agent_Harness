import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_readme():
    with open(os.path.join(ROOT, "README.md"), "r", encoding="utf-8") as f:
        return f.read()


def test_readme_has_quick_start_section():
    """README must have a '3 分鐘快速開始' or '3-Minute Quick Start' near top."""
    content = read_readme()
    first_500_chars = content[:500]
    assert any(kw in first_500_chars for kw in [
        "3 分鐘", "3-Minute", "Quick Start", "快速開始"
    ]), "README top 500 chars must contain a quick-start section"


def test_readme_has_trust_section():
    """README must have a trust checklist near top."""
    content = read_readme()
    first_1500_chars = content[:1500]
    assert any(kw in first_1500_chars for kw in [
        "信任", "Trust", "MIT", "開源", "open-source"
    ]), "README must have a trust checklist near top"


def test_readme_shows_one_command():
    """README must show a single git clone + install command near top."""
    content = read_readme()
    first_1500_chars = content[:1500]
    assert "git clone" in first_1500_chars, "README must show git clone command near top"
    assert "install.bat" in first_1500_chars or "install.sh" in first_1500_chars, "README must show install command near top"
