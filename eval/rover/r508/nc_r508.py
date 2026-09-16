#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 判据器负控 (判别力证据)。

① 正控: 参考解必须全过; 不过 ⇒ NC_HOLLOW (判据器空心, 弃权)。
② 负控: 对参考解注入**指名缺陷** ⇒ 整题必须变红, 且**预期用例必须真失败**
   (未命中 ⇒ NC_NOT_DETECTED; 补丁没打上 ⇒ PATCH_NOT_APPLIED, fail-closed)。
输出 JSON: {hollow, mutants:[{id,task,expect_fail,detected,failed_cases,rc}], verdict}
"""
from __future__ import annotations
import argparse, copy, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GRADE = os.path.join(HERE, "proj_grade.py")
REF = {"p1": ("ref/p1/app.py",), "p2": ("ref/p2/logpipe.py",), "p3": ("kvsvc/server.py", "kvsvc/store.py")}

# id -> (task, 相对文件, old, new, 预期必须失败的用例)
MUTANTS = [
    ("p1_no_delete_route", "p1", "app.py",
     '        return _send(self, 200, {"deleted": True})',
     '        return _send(self, 500, {"error": "delete_disabled"})',
     ["delete_and_404"]),
    ("p1_sqlite_id_reuse", "p1", "app.py",
     "id INTEGER PRIMARY KEY AUTOINCREMENT",
     "id INTEGER PRIMARY KEY",
     ["restart_persistence_no_id_reuse"]),
    ("p1_blank_text_accepted", "p1", "app.py",
     "if not isinstance(text, str) or not text.strip():",
     "if not isinstance(text, str):",
     ["bad_request_400"]),
    ("p2_tie_break_reversed", "p2", "logpipe.py",
     "items = sorted(ipc.items(), key=lambda kv: (-kv[1], kv[0]))[:max(0, top)]",
     "items = sorted(ipc.items(), key=lambda kv: (-kv[1], kv[0]), reverse=True)[:max(0, top)]",
     ["top_tie_break_ip_asc"]),
    ("p2_p95_off_by_one", "p2", "logpipe.py",
     "idx = int(math.ceil(0.95 * len(s))) - 1",
     "idx = int(math.floor(0.95 * len(s)))",
     ["p95_nearest_rank_20"]),
    ("p2_utf8_sig_bom", "p2", "logpipe.py",
     'with open(a.out, "w", encoding="utf-8", newline="\\n") as fh:',
     'with open(a.out, "w", encoding="utf-8-sig", newline="\\n") as fh:',
     ["utf8_no_bom"]),
    ("p2_blank_line_not_skipped", "p2", "logpipe.py",
     "        if not raw.strip():\n            skipped += 1\n            continue",
     "        if not raw.strip():\n            continue",
     ["all_bad_lines"]),
    ("p3_incr_nonatomic", "p3", "kvsvc/store.py",
     "    def incr(self, key: str, by: int):\n        with self._lock:\n            now = time.time()\n            v = self._purge(key, now)",
     "    def incr(self, key: str, by: int):\n        if True:\n            now = time.time()\n            v = self._purge(key, now)\n            time.sleep(0.01)",
     ["incr_concurrent_atomic"]),
    ("p3_ttl_never_expires", "p3", "kvsvc/store.py",
     "        if v is not None and v[1] is not None and v[1] <= now:",
     "        if False and v is not None and v[1] is not None and v[1] <= now:",
     ["ttl_expire_and_count"]),
    ("p3_no_wal_replay", "p3", "kvsvc/store.py",
     "        now = time.time()\n        for ln in lines:",
     "        now = time.time()\n        lines = []\n        for ln in lines:",
     ["restart_recovery"]),
]


def grade(task, d):
    out = os.path.join(d, "_grade.json")
    p = subprocess.run([sys.executable, GRADE, "--task", task, "--dir", d, "--json", out],
                       capture_output=True, text=True, timeout=900)
    data = {}
    if os.path.exists(out):
        with open(out, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    data["_rc"] = p.returncode
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    report = {"hollow": False, "mutants": [], "positive": {}}

    # ① 正控
    for task in sorted(REF):
        r = grade(task, os.path.join(HERE, "ref", task))
        report["positive"][task] = {"all_pass": r.get("all_pass"), "pass": r.get("pass_count"),
                                    "of": r.get("case_count")}
        if not r.get("all_pass"):
            report["hollow"] = True
    if report["hollow"]:
        report["verdict"] = "NC_HOLLOW"
        _emit(report, a.json)
        return 3

    # ② 负控
    all_ok = True
    for mid, task, rel, old, new, expect in MUTANTS:
        tmp = tempfile.mkdtemp(prefix="r508-nc-")
        src = os.path.join(HERE, "ref", task)
        shutil.copytree(src, tmp, dirs_exist_ok=True)
        path = os.path.join(tmp, rel)
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if old not in text:
            report["mutants"].append({"id": mid, "task": task, "expect_fail": expect,
                                      "detected": False, "patch": "PATCH_NOT_APPLIED"})
            all_ok = False
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new, 1))
        r = grade(task, tmp)
        failed = [c["name"] for c in r.get("cases", []) if c["status"] == "FAIL"]
        missed = [c for c in expect if c not in failed]
        detected = (not r.get("all_pass")) and not missed
        all_ok = all_ok and detected
        report["mutants"].append({"id": mid, "task": task, "expect_fail": expect,
                                  "failed_cases": failed, "missed": missed,
                                  "all_pass_after_mutation": bool(r.get("all_pass")),
                                  "detected": detected})
        shutil.rmtree(tmp, ignore_errors=True)

    report["verdict"] = "SELFTEST=OK" if all_ok else "NC_NOT_DETECTED"
    _emit(report, a.json)
    return 0 if all_ok else 1


def _emit(report, path):
    blob = json.dumps(report, ensure_ascii=False, indent=1)
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(blob)
    print("POSITIVE", json.dumps(report["positive"], ensure_ascii=False))
    for m in report["mutants"]:
        print("MUTANT %-26s detected=%s failed=%s missed=%s" % (m["id"], m["detected"], m.get("failed_cases"), m.get("missed")))
    print("VERDICT", report["verdict"])


if __name__ == "__main__":
    raise SystemExit(main())
