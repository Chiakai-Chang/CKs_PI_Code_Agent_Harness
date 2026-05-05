# 手動還原指南（Restore Commands）

若無法或不想使用 install.bat / install.sh，
可依照以下步驟手動還原 CK's Pi Code Agent Harness。

前提：
- 已安裝 Git、Python
- 已安裝 Node.js 與 npm
- 已安裝 Pi（例如：npm install -g @mariozechner/pi-coding-agent）

以下以：
- REPO_ROOT：本 repo 路徑
- PI_DIR：~/.pi
- AGENT_DIR：~/.pi/agent
為例。

1. 建立目錄

   - mkdir -p "$AGENT_DIR/skills"
   - mkdir -p "$AGENT_DIR/rules"
   - mkdir -p "$AGENT_DIR/extensions"
   - mkdir -p "$AGENT_DIR/git"

2. 還原配置

   - cp "$REPO_ROOT/pi-config/settings.json" "$AGENT_DIR/settings.json"
   - cp "$REPO_ROOT/pi-config/config.json"   "$AGENT_DIR/config.json"
   - cp "$REPO_ROOT/pi-config/git/.gitignore" "$AGENT_DIR/git/.gitignore"

   若有 TODO_NEW_MACHINE 字串，需手動替換為本機路徑。

3. 還原 skills

   - cp -r "$REPO_ROOT/pi-skills/"* "$AGENT_DIR/skills/"

4. 還原 rules

   - cp -r "$REPO_ROOT/pi-rules/"* "$AGENT_DIR/rules/"

5. 還原 extensions

   - cp -r "$REPO_ROOT/pi-extensions/"* "$AGENT_DIR/extensions/"

6. 完成

   - pi update
   - pi
   - 確認 Skills 與 Extensions 是否正常載入。
