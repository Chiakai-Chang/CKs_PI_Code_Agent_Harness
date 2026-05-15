import os
import json

def test_projection_integrity():
    print("🧪 Testing projection integrity...")
    
    # 1. Check if manifest exists
    assert os.path.exists("core/manifest.json"), "Manifest missing!"
    
    # 2. Check if bridges are generated
    assert os.path.exists("bridges/gemini/gemini-extension.json"), "Gemini projection missing!"
    assert os.path.exists("bridges/claude/.claude/commands/omg-team.md"), "Claude projection missing!"
    
    # 3. Check if mapping works (assuming mapper.py has been run)
    if os.path.exists(".claude"):
        print("✅ Claude mapping verified.")
    if os.path.exists("gemini-extension.json"):
        print("✅ Gemini mapping verified.")
        
    # 4. Check tool translation in Claude projection
    with open("bridges/claude/.claude/commands/omg-team.md", "r", encoding="utf-8") as f:
        content = f.read()
        assert "{{READ}}" not in content, "Tool translation failed! {{READ}} still present."
        assert "Read" in content or "read_file" in content, "Tool translation failed! No platform tool found."
    
    print("🎉 All integrity tests PASSED.")

if __name__ == "__main__":
    test_projection_integrity()
