import json,io,sys,re,os
gt=json.load(io.open(".ground-truth.json",encoding="utf-8"))
w=io.open(sys.argv[1],"w",encoding="utf-8"); p=lambda *a: print(*a,file=w)
T="02_Task_Queue/Task_001_ConfigDrift"
expect={"svc-01":(3000,3),"svc-02":(3000,3),"svc-03":(9000,3),"svc-04":(3000,7),
        "svc-05":(3000,3),"svc-06":(12000,3),"svc-07":(3000,3),"svc-08":(3000,11)}
bad=[s for s,(t,r) in expect.items()
     if (lambda d: d.get("timeout_ms")!=t or d.get("retries")!=r)(json.load(io.open(f"data/{s}.json",encoding="utf-8")))]
st=io.open(f"{T}/status.txt",encoding="utf-8").read().strip() if os.path.exists(f"{T}/status.txt") else "MISSING"
has=os.path.exists(f"{T}/output.md")
out=io.open(f"{T}/output.md",encoding="utf-8").read() if has else ""
def sect(n):
    i=out.find(n)
    if i<0: return ""
    j=out.find("\n## ", i+1)
    return out[i:j if j>0 else len(out)]
mt=re.search(r"timeout_ms\s*多數值\s*[:：]\s*(\d+)", out)
mr=re.search(r"retries\s*多數值\s*[:：]\s*(\d+)", out)
t_ids=set(re.findall(r"-\s*(svc-\d+)\s*[:：]", sect("## timeout 偏離")))
r_ids=set(re.findall(r"-\s*(svc-\d+)\s*[:：]", sect("## retries 偏離")))
checks=[("output.md 存在",has)]
for h in ["## 多數值","## timeout 偏離","## retries 偏離","## 驗證"]:
    checks.append(("有標題 "+h, h in out))
checks += [("timeout 多數值 = 3000", bool(mt) and mt.group(1)=="3000"),
           ("retries 多數值 = 3", bool(mr) and mr.group(1)=="3"),
           ("timeout 偏離正確", t_ids==set(gt["odd_timeout"])),
           ("retries 偏離正確", r_ids==set(gt["odd_retries"])),
           ("驗證段落有實質內容", len(sect("## 驗證").strip())>60),
           ("data/ 未被修改", not bad)]
for n,v in checks: p(("[PASS] " if v else "[FAIL] ")+n)
p("")
p(f"status.txt = {st}")
p(f"DoD: {sum(1 for _,v in checks if v)}/{len(checks)}")
p(f"planning.md {'有' if os.path.exists(T+'/planning.md') else '無'}   output.md {len(out.encode('utf-8'))} bytes")
p(f"模型答案 timeout={sorted(t_ids) or '(無)'}  retries={sorted(r_ids) or '(無)'}")
w.close(); print("ok")
