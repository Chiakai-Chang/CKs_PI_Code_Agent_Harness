#!/usr/bin/env python3
"""服務組態驗證器 —— 一次只回報一個問題。

用法:python check.py

它會依檔名順序掃描 services/*.json,**回報找到的第一個違規就停下來**,
離開碼 1。全部通過時印出 ALL OK,離開碼 0。

一次一個是刻意的:每修好一個才看得到下一個。
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRED = ["id", "name", "owner", "endpoint", "timeout_ms", "retries"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def violations(path, teams, defaults):
    """這個檔案的違規,依規則編號順序。"""
    stem = os.path.splitext(os.path.basename(path))[0]
    try:
        d = load(path)
    except Exception as exc:
        return ["R0 %s 不是合法的 JSON:%s" % (stem, exc)]

    out = []
    for key in REQUIRED:
        if key not in d:
            out.append("R1 %s 缺少必要欄位 `%s`(預設值見 defaults.json)" % (stem, key))
    if out:
        return out

    if d["id"] != stem:
        out.append("R2 %s 的 `id` 是 %r,應該等於檔名 %r" % (stem, d["id"], stem))
    expected_owner = teams.get(d["id"])
    if expected_owner and d["owner"] != expected_owner:
        out.append("R3 %s 的 `owner` 是 %r,teams.json 說應該是 %r"
                   % (stem, d["owner"], expected_owner))
    t = d["timeout_ms"]
    if not isinstance(t, int) or t < 1000 or t > 10000:
        out.append("R4 %s 的 `timeout_ms` 是 %r,必須是 1000 到 10000 之間的整數" % (stem, t))
    elif t % 500 != 0:
        out.append("R5 %s 的 `timeout_ms` 是 %d,必須是 500 的倍數(四捨五入到最近的 500)"
                   % (stem, t))
    r = d["retries"]
    if not isinstance(r, int) or r < 0 or r > 5:
        out.append("R6 %s 的 `retries` 是 %r,必須是 0 到 5 之間的整數" % (stem, r))
    if not str(d["endpoint"]).startswith("https://"):
        out.append("R7 %s 的 `endpoint` 是 %r,必須以 https:// 開頭"
                   % (stem, d["endpoint"]))
    return out


def main():
    teams = load(os.path.join(HERE, "teams.json"))
    defaults = load(os.path.join(HERE, "defaults.json"))
    files = sorted(glob.glob(os.path.join(HERE, "services", "*.json")))
    if not files:
        print("services/ 底下沒有檔案")
        return 1
    for path in files:
        v = violations(path, teams, defaults)
        if v:
            print(v[0])
            print("(還有其他問題沒有顯示 —— 修好這一個再跑一次。)")
            return 1
    print("ALL OK —— %d 個服務全部通過" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
