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


def read_file(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


def test_install_bat_has_trust_statement():
    content = read_file("install.bat")
    assert any(kw in content for kw in [
        "trust", "Trust", "MIT", "開源", "Source", "Source:"
    ]), "install.bat must include a short trust/source statement"


def test_install_bat_has_progress_indicators():
    content = read_file("install.bat")
    assert re.search(r"\[\d+/\d+\]", content), "install.bat should show progress markers"


def test_install_bat_has_confirmation_prompt():
    content = read_file("install.bat")
    assert "Continue?" in content or "繼續" in content, "install.bat must ask for confirmation"


def test_setup_py_supports_auto_mode():
    content = read_file("scripts/setup.py")
    assert "argparse" in content, "setup.py should use argparse for --auto"
    assert "--auto" in content, "setup.py must support --auto flag"


def test_uninstall_script_exists():
    path = os.path.join(ROOT, "scripts", "uninstall.py")
    assert os.path.isfile(path), "scripts/uninstall.py must exist"


def test_uninstall_script_is_executable_style():
    content = read_file("scripts/uninstall.py")
    assert "if __name__" in content, "uninstall.py must be runnable as script"
    assert "backup" in content.lower() or "restore" in content.lower(), "uninstall.py must mention backup/restore"


def test_setup_py_has_llm_friendly_message():
    content = read_file("scripts/setup.py")
    assert any(kw in content for kw in [
        "No local LLM",
        "No LLM detected",
        "未偵測到本地 LLM",
        "install Ollama",
        "稍後",
        "skip"
    ]), "setup.py must guide user when no LLM detected"


def test_readme_shows_one_command():
    """README must show a single git clone + install command near top."""
    content = read_readme()
    first_1500_chars = content[:1500]
    assert "git clone" in first_1500_chars, "README must show git clone command near top"
    assert "install.bat" in first_1500_chars or "install.sh" in first_1500_chars, "README must show install command near top"
