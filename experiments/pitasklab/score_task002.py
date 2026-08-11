"""Score Task_002_ConfigRepair against ground truth. Run from PiTaskLab."""
import hashlib, io, json, os, re, subprocess, sys

T = "02_Task_Queue/Task_002_ConfigRepair"
out = io.open(sys.argv[1], "w", encoding="utf-8")
p = lambda *a: print(*a, file=out)

gt = json.load(io.open(".ground-truth-002.json", encoding="utf-8"))
expected, defects = gt["expected"], gt["defects"]

r = subprocess.run([sys.executable, "check.py"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
check_ok = r.returncode == 0 and "ALL OK" in r.stdout

# every service file must match ground truth exactly
wrong = []
for sid, exp in expected.items():
    try:
        got = json.load(io.open("services/%s.json" % sid, encoding="utf-8"))
    except Exception as exc:
        wrong.append("%s unreadable (%s)" % (sid, exc)); continue
    for k, v in exp.items():
        if got.get(k) != v:
            wrong.append("%s.%s = %r, expected %r" % (sid, k, got.get(k), v))

files = sorted(f for f in os.listdir("services") if f.endswith(".json"))
file_set_ok = files == sorted("%s.json" % s for s in expected)

# tools untouched. sha256 from the baseline written by make-lab.py, hashed the
# same way here — `md5sum` was a shell dependency and this scorer must run
# anywhere the task does.
base = {}
for line in io.open(".baseline-002.txt", encoding="utf-8"):
    if line.strip():
        digest, name = line.split()
        base[name] = digest
tools_ok = all(
    hashlib.sha256(io.open(name, "rb").read()).hexdigest() == digest
    for name, digest in base.items())

log_path = "%s/fixlog.md" % T
has_log = os.path.exists(log_path)
log = io.open(log_path, encoding="utf-8").read() if has_log else ""
rounds = re.findall(r"^###\s*第\s*(\d+)\s*輪", log, re.M)
msgs = re.findall(r"^-\s*訊息[::]\s*(.+)$", log, re.M)
fileln = re.findall(r"^-\s*檔案[::]\s*(.+)$", log, re.M)
change = re.findall(r"^-\s*修改[::]\s*(.+)$", log, re.M)
rlike = [m for m in msgs if re.match(r"^R\d", m.strip().strip("`"))]

checks = [
    ("check.py 離開碼 0 且輸出 ALL OK", check_ok),
    ("每個 services/*.json 都等於標準答案", not wrong),
    ("services/ 檔案集合沒有增減", file_set_ok),
    ("check.py / teams.json / defaults.json 未被修改", tools_ok),
    ("fixlog.md 存在", has_log),
    ("輪數等於違規數 (%d)" % len(defects), len(rounds) == len(defects)),
    ("每一輪都有 訊息/檔案/修改 三個欄位",
     has_log and len(msgs) == len(rounds) == len(fileln) == len(change) and len(rounds) > 0),
    ("每一則訊息都以 R<數字> 開頭", bool(msgs) and len(rlike) == len(msgs)),
    ("收尾段有總輪數", "總輪數" in log),
]
for n, v in checks:
    p(("[PASS] " if v else "[FAIL] ") + n)
p("")
p("check.py -> exit %d | %s" % (r.returncode, r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""))
p("status.txt = %s" % io.open("%s/status.txt" % T, encoding="utf-8").read().strip())
p("DoD: %d/%d" % (sum(1 for _, v in checks if v), len(checks)))
p("rounds logged: %d  (seeded defects: %d)" % (len(rounds), len(defects)))
if wrong:
    p("value mismatches: " + "; ".join(wrong[:8]))
out.close()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print(io.open(sys.argv[1], encoding="utf-8").read())
