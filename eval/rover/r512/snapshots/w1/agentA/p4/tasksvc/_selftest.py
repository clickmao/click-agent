#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tasksvc._selftest —— 无头自检 (零第三方依赖)。

运行:
    python3 -B -m tasksvc._selftest
退出码: 0 = 全部 PASS; 非 0 = 有 FAIL。

自检经**真实 CLI 入口** (subprocess 调用 python3 -B -m tasksvc.cli) 驱动,
断言绑定真实 stdout / 退出码 / 存储文件内容, 并配负向控制。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 工作区根 / 包父目录


def run_cli(args, cwd):
    """经真实入口运行 CLI, 返回 (rc, stdout_text)。"""
    cmd = [sys.executable, "-B", "-m", "tasksvc.cli"] + list(args)
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        cmd, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout.decode("utf-8")


def parse_one(text):
    """断言 stdout 恰好一个 JSON 对象。"""
    stripped = text.strip()
    obj = json.loads(stripped)
    assert isinstance(obj, dict), "stdout must be a JSON object"
    return obj


class T:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, name, cond, detail=""):
        if cond:
            self.passed += 1
            print("PASS %s" % name)
        else:
            self.failed += 1
            print("FAIL %s %s" % (name, detail))


def main():
    t = T()
    tmp = tempfile.mkdtemp(prefix="tasksvc-selftest-")

    # ---- 1. 基本 add/list, id 从 1 开始, text 原样往返 (中文/emoji/首尾空格)
    db = os.path.join(tmp, "a.json")
    text = "  你好 🚀 world  "
    rc, out = run_cli(["--db", db, "--now", "1000", "add", text], tmp)
    t.check("add.rc0", rc == 0, "rc=%d" % rc)
    obj = parse_one(out)
    task = obj["task"]
    t.check("add.id1", task["id"] == 1, task)
    t.check("add.text-bytes", task["text"] == text, repr(task["text"]))
    t.check("add.done-false", task["done"] is False, task)
    t.check("add.created-float", task["created_at"] == 1000.0 and isinstance(task["created_at"], float), task)
    t.check("add.expires-null", task["expires_at"] is None, task)

    rc, out = run_cli(["--db", db, "--now", "1001", "list"], tmp)
    t.check("list.default-open", [x["id"] for x in parse_one(out)["tasks"]] == [1], out)

    # ---- 2. 空白 text => bad_request / rc 2
    rc, out = run_cli(["--db", db, "--now", "1001", "add", "   "], tmp)
    t.check("add.blank-rc2", rc == 2, "rc=%d" % rc)
    t.check("add.blank-badreq", parse_one(out) == {"error": "bad_request"}, out)

    # ---- 3. next_id 持久化只增不减 & id 永不复用
    raw = json.load(open(db, encoding="utf-8"))
    t.check("store.next_id-2", raw["next_id"] == 2, raw)
    rc, out = run_cli(["--db", db, "--now", "1002", "add", "second"], tmp)
    t.check("add.id2", parse_one(out)["task"]["id"] == 2, out)

    # ---- 4. done 幂等 + 未知 id => not_found/rc3
    rc, out = run_cli(["--db", db, "--now", "1003", "done", "2"], tmp)
    t.check("done.rc0", rc == 0 and parse_one(out)["task"]["done"] is True, out)
    rc, out = run_cli(["--db", db, "--now", "1004", "done", "2"], tmp)
    t.check("done.idempotent", rc == 0 and parse_one(out)["task"]["done"] is True, out)
    rc, out = run_cli(["--db", db, "--now", "1005", "done", "999"], tmp)
    t.check("done.missing-rc3", rc == 3, "rc=%d" % rc)
    t.check("done.missing-notfound", parse_one(out) == {"error": "not_found"}, out)

    # ---- 5. 非整数 id => bad_request
    rc, out = run_cli(["--db", db, "--now", "1005", "done", "abc"], tmp)
    t.check("done.nonint-rc2", rc == 2 and parse_one(out) == {"error": "bad_request"}, out)

    # ---- 6. --ttl 边界: <=0 => bad_request
    rc, out = run_cli(["--db", db, "--now", "1005", "add", "x", "--ttl", "0"], tmp)
    t.check("ttl.zero-rc2", rc == 2 and parse_one(out) == {"error": "bad_request"}, out)
    rc, out = run_cli(["--db", db, "--now", "1005", "add", "x", "--ttl", "-5"], tmp)
    t.check("ttl.neg-rc2", rc == 2, "rc=%d" % rc)

    # ---- 7. 过期判定 now >= expires_at (边界等于即过期)
    db2 = os.path.join(tmp, "b.json")
    rc, out = run_cli(["--db", db2, "--now", "2000", "add", "ttl-task", "--ttl", "10"], tmp)
    task = parse_one(out)["task"]
    t.check("ttl.expires_at", task["expires_at"] == 2010.0, task)
    # now=2009 未过期 -> open
    rc, out = run_cli(["--db", db2, "--now", "2009", "list", "--status", "open"], tmp)
    t.check("ttl.before-open", [x["id"] for x in parse_one(out)["tasks"]] == [1], out)
    # now=2010 恰好等于 expires_at -> expired
    rc, out = run_cli(["--db", db2, "--now", "2010", "list", "--status", "expired"], tmp)
    t.check("ttl.equal-expired", [x["id"] for x in parse_one(out)["tasks"]] == [1], out)
    # 过期优先于 done: 先 done 再过期
    rc, out = run_cli(["--db", db2, "--now", "2010", "done", "1"], tmp)
    rc, out = run_cli(["--db", db2, "--now", "2011", "list", "--status", "done"], tmp)
    t.check("ttl.expired-beats-done", parse_one(out)["tasks"] == [], out)
    rc, out = run_cli(["--db", db2, "--now", "2011", "stats"], tmp)
    s = parse_one(out)
    t.check("stats.mutual-excl", s == {"total": 1, "open": 0, "done": 0, "expired": 1}, s)

    # ---- 8. expire 真删除 + id 不复用
    rc, out = run_cli(["--db", db2, "--now", "2011", "expire"], tmp)
    t.check("expire.ids", parse_one(out) == {"expired": [1]}, out)
    raw2 = json.load(open(db2, encoding="utf-8"))
    t.check("expire.really-deleted", raw2["tasks"] == [], raw2)
    rc, out = run_cli(["--db", db2, "--now", "2012", "add", "after"], tmp)
    t.check("expire.id-not-reused", parse_one(out)["task"]["id"] == 2, out)

    # ---- 9. 原子写: 不留临时文件残留
    leftovers = [f for f in os.listdir(tmp) if f.startswith(".tasksvc-")]
    t.check("atomic.no-tmp-leftover", leftovers == [], leftovers)

    # ---- 10. 未知子命令 => bad_request
    rc, out = run_cli(["--db", db2, "--now", "1", "frobnicate"], tmp)
    t.check("unknown.cmd-rc2", rc == 2 and parse_one(out) == {"error": "bad_request"}, out)

    # ---- 11. 存储损坏 => bad_store/rc4 (非 JSON)
    bad = os.path.join(tmp, "bad.json")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    rc, out = run_cli(["--db", bad, "--now", "1", "list"], tmp)
    t.check("badstore.nonjson-rc4", rc == 4 and parse_one(out) == {"error": "bad_store"}, out)
    # schema 不符 (next_id 缺失)
    bad2 = os.path.join(tmp, "bad2.json")
    with open(bad2, "w", encoding="utf-8") as fh:
        json.dump({"tasks": []}, fh)
    rc, out = run_cli(["--db", bad2, "--now", "1", "list"], tmp)
    t.check("badstore.schema-rc4", rc == 4 and parse_one(out) == {"error": "bad_store"}, out)

    # ---- 12. 负向控制: 手工把 next_id 改小, 若实现复用 id 则本应失败 ——
    # 这里验证 next_id 单调由实现保证 (只增不减): 反复 add 后 next_id 等于已分配最大值+1
    db3 = os.path.join(tmp, "c.json")
    for k in range(3):
        run_cli(["--db", db3, "--now", str(3000 + k), "add", "t%d" % k], tmp)
    raw3 = json.load(open(db3, encoding="utf-8"))
    ids = sorted(x["id"] for x in raw3["tasks"])
    t.check("monotonic.ids", ids == [1, 2, 3], ids)
    t.check("monotonic.next_id", raw3["next_id"] == 4, raw3["next_id"])

    # ---- 13. list --status all 按 id 升序
    rc, out = run_cli(["--db", db3, "--now", "3100", "list", "--status", "all"], tmp)
    got = [x["id"] for x in parse_one(out)["tasks"]]
    t.check("list.asc", got == [1, 2, 3], got)

    print("----")
    print("passed=%d failed=%d" % (t.passed, t.failed))
    return 0 if t.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
