import os
import json

def test_projection_integrity():
    print("🧪 Testing calibrated projection integrity (v4.1)...")
    
    # 1. Check if manifest exists
    assert os.path.exists("core/manifest.json"), "Manifest missing!"
    
    # 2. Check if bridges are generated for all 3 platforms
    assert os.path.exists("bridges/pi/gemini-extension.json"), "Pi projection missing!"
    assert os.path.exists("bridges/gemini_cli/.gemini/commands/neutral-test.md"), "Gemini CLI projection missing!"
    assert os.path.exists("bridges/claude/.claude/commands/neutral-test.md"), "Claude projection missing!"
    
    # 3. Check if mapping works
    if os.path.exists(".claude"):
        print("✅ Claude mapping verified.")
    if os.path.exists(".gemini"):
        print("✅ Gemini CLI mapping verified.")
    if os.path.exists("gemini-extension.json"):
        print("✅ Pi mapping verified.")
        
    # 4. Check tool translation in Gemini CLI projection
    with open("bridges/gemini_cli/.gemini/commands/neutral-test.md", "r", encoding="utf-8") as f:
        content = f.read()
        assert "read_file" in content, "Gemini CLI tool translation failed!"
        assert "{{READ}}" not in content, "Gemini CLI cleaning failed!"
        
    # 5. Check tool translation in Claude projection
    with open("bridges/claude/.claude/commands/neutral-test.md", "r", encoding="utf-8") as f:
        content = f.read()
        assert "Read" in content, "Claude tool translation failed!"
        assert "{{READ}}" not in content, "Claude cleaning failed!"
    
    print("🎉 All calibrated integrity tests PASSED.")

if __name__ == "__main__":
    test_projection_integrity()
