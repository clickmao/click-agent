#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R511 P4 隐藏用例 (逐条机械判对) —— 在**产物目录**内以 `python3 -I -B` 运行。

判据: 只驱动产物真实行为 (`python3 -B -m tasksvc.cli …` 子进程), 不读产物源码。
      每条命令必须是**新进程** ⇒ 「跨进程持久化」由用例形态本身保证。
输出: 每行 `CASE <name> PASS` 或 `CASE <name> FAIL <reason>`; 全部 PASS 才 rc=0。
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import tempfile

ENTRY = ["-B", "-m", "tasksvc.cli"]
# 用例在**产物目录**内以 cwd=产物目录 运行 ⇒ 子进程一律继承 cwd (禁把用例自身路径当产物根)。
FAILS = []


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def cli(*args, cwd=None):
    """跑一条命令; 返回 (rc, stdout, stderr)。cwd 缺省 = 当前产物目录。"""
    p = subprocess.run([sys.executable] + ENTRY + list(args),
                       cwd=cwd or os.getcwd(), capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


def jobj(out, rc):
    """stdout 必须是**恰好一个** JSON 对象 (可带尾换行)。"""
    body = out.strip()
    need(body != "", "stdout 为空 (rc=%d)" % rc)
    obj = json.loads(body)
    need(isinstance(obj, dict), "stdout 不是 JSON 对象: %r" % body[:80])
    return obj


def dbpath(tag):
    d = tempfile.mkdtemp(prefix="p4-%s-" % tag)
    return os.path.join(d, "tasks.json")


def case(fn):
    name = fn.__name__[5:]
    try:
        fn()
        print("CASE %s PASS" % name)
    except Exception as exc:  # noqa: BLE001
        FAILS.append(name)
        print("CASE %s FAIL %s: %s" % (name, type(exc).__name__, str(exc).replace("\n", " ")[:220]))


# ---------------------------------------------------------------- 用例

def test_add_creates_and_lists():
    db = dbpath("c01")
    rc, out, err = cli("--db", db, "add", "买菜")
    need(rc == 0, "add rc=%d stderr=%s" % (rc, err[:120]))
    o = jobj(out, rc)
    need("task" in o, "add 输出缺 task: %s" % out[:120])
    t = o["task"]
    need(t["id"] == 1 and t["text"] == "买菜" and t["done"] is False, "task 字段不符: %s" % t)
    need(t.get("expires_at") is None, "无 --ttl 时 expires_at 必须为 null: %s" % t)
    rc, out, _ = cli("--db", db, "list")
    need(rc == 0, "list rc=%d" % rc)
    o = jobj(out, rc)
    need([x["id"] for x in o["tasks"]] == [1], "list 内容不符: %s" % out[:160])


def test_id_monotonic_no_reuse():
    db = dbpath("c02")
    need(cli("--db", db, "add", "a")[0] == 0, "add a 失败")
    need(cli("--db", db, "done", "1")[0] == 0, "done 1 失败")
    rc, out, _ = cli("--db", db, "add", "b")
    need(rc == 0, "add b rc=%d" % rc)
    need(jobj(out, rc)["task"]["id"] == 2, "id 必须单调不复用: %s" % out[:120])
    rc, out, _ = cli("--db", db, "list", "--status", "all")
    need(rc == 0 and [x["id"] for x in jobj(out, rc)["tasks"]] == [1, 2], "all 视图: %s" % out[:160])


def test_unicode_roundtrip():
    db = dbpath("c03")
    text = "中文😀 mixed éÑ \u00a0 尾部空格 "
    need(cli("--db", db, "add", text)[0] == 0, "add unicode 失败")
    rc, out, _ = cli("--db", db, "list")
    need(rc == 0, "list rc=%d" % rc)
    got = jobj(out, rc)["tasks"][0]["text"]
    need(got == text, "unicode 未逐字节保留: %r != %r" % (got, text))


def test_done_idempotent():
    db = dbpath("c04")
    need(cli("--db", db, "add", "x")[0] == 0, "add 失败")
    rc1, out1, _ = cli("--db", db, "done", "1")
    rc2, out2, _ = cli("--db", db, "done", "1")
    need(rc1 == 0 and rc2 == 0, "重复 done 必须都 rc=0 (幂等): %d/%d" % (rc1, rc2))
    need(jobj(out2, rc2)["task"]["done"] is True, "重复 done 后 done 必须仍为 true")


def test_done_unknown_id():
    db = dbpath("c05")
    need(cli("--db", db, "add", "x")[0] == 0, "add 失败")
    rc, out, _ = cli("--db", db, "done", "77")
    need(rc == 3, "未知 id 必须 rc=3, 实得 %d" % rc)
    need(jobj(out, rc).get("error") == "not_found", "未知 id 输出应为 not_found: %s" % out[:120])


def test_bad_request_exit2():
    db = dbpath("c06")
    rc, out, _ = cli("--db", db, "add", "   ")
    need(rc == 2, "空白 text 必须 rc=2, 实得 %d" % rc)
    need(jobj(out, rc).get("error") == "bad_request", "空白 text 输出: %s" % out[:120])
    rc, out, _ = cli("--db", db, "done", "abc")
    need(rc == 2, "非整数 id 必须 rc=2, 实得 %d" % rc)
    rc, out, _ = cli("--db", db, "add", "x", "--ttl", "0")
    need(rc == 2, "--ttl 0 必须 rc=2, 实得 %d" % rc)
    rc, out, _ = cli("--db", db, "nosuchcmd")
    need(rc == 2, "未知子命令必须 rc=2, 实得 %d" % rc)


def test_ttl_expiry_uses_injected_clock():
    db = dbpath("c07")
    rc, out, _ = cli("--db", db, "--now", "1000", "add", "短命", "--ttl", "100")
    need(rc == 0, "add --ttl rc=%d" % rc)
    need(jobj(out, rc)["task"]["expires_at"] == 1100.0, "expires_at 应为 now+ttl: %s" % out[:120])
    rc, out, _ = cli("--db", db, "--now", "1099", "list")
    need([x["id"] for x in jobj(out, rc)["tasks"]] == [1], "未到期必须可见: %s" % out[:160])
    rc, out, _ = cli("--db", db, "--now", "1100", "list")
    need(jobj(out, rc)["tasks"] == [], "到期时刻起必须过期(不出现在 open): %s" % out[:160])
    rc, out, _ = cli("--db", db, "--now", "1100", "list", "--status", "expired")
    need([x["id"] for x in jobj(out, rc)["tasks"]] == [1], "expired 视图应含该任务: %s" % out[:160])


def test_stats_counts_three_states():
    db = dbpath("c08")
    cli("--db", db, "--now", "0", "add", "open1")
    cli("--db", db, "--now", "0", "add", "done1")
    cli("--db", db, "--now", "0", "add", "exp1", "--ttl", "10")
    need(cli("--db", db, "--now", "5", "done", "2")[0] == 0, "done 2 失败")
    rc, out, _ = cli("--db", db, "--now", "20", "stats")
    need(rc == 0, "stats rc=%d" % rc)
    o = jobj(out, rc)
    need(o == {"total": 3, "open": 1, "done": 1, "expired": 1}, "stats 读数不符: %s" % o)


def test_expire_removes_expired_tasks():
    db = dbpath("c09")
    cli("--db", db, "--now", "0", "add", "keep")
    cli("--db", db, "--now", "0", "add", "gone", "--ttl", "5")
    rc, out, _ = cli("--db", db, "--now", "10", "expire")
    need(rc == 0, "expire rc=%d" % rc)
    need(jobj(out, rc)["expired"] == [2], "expire 报告不符: %s" % out[:120])
    rc, out, _ = cli("--db", db, "--now", "10", "list", "--status", "all")
    need([x["id"] for x in jobj(out, rc)["tasks"]] == [1], "过期任务必须真删除: %s" % out[:160])
    rc, out, _ = cli("--db", db, "--now", "10", "add", "next")
    need(jobj(out, rc)["task"]["id"] == 3, "删除后 id 仍不得复用: %s" % out[:120])


def test_persistence_across_processes():
    db = dbpath("c10")
    need(cli("--db", db, "add", "跨进程")[0] == 0, "add 失败")
    # 新进程读同一文件
    rc, out, _ = cli("--db", db, "list")
    need(rc == 0 and [x["text"] for x in jobj(out, rc)["tasks"]] == ["跨进程"], "跨进程读失败: %s" % out[:160])
    raw = open(db, "r", encoding="utf-8").read()
    st = json.loads(raw)
    need(isinstance(st, dict) and "tasks" in st, "db 文件必须是合法 JSON 对象: %r" % raw[:120])
    need(int(st["next_id"]) >= 2, "next_id 必须持久化 (>=2): %s" % st.get("next_id"))


def test_no_temp_residue():
    db = dbpath("c11")
    d = os.path.dirname(db)
    for i in range(4):
        must0(cli("--db", db, "add", "t%d" % i))
    # 原子写判别力 (结构可观测): temp+rename ⇒ 每次更新换 inode; 原地截断重写 ⇒ inode 不变。
    ino_before = os.stat(db).st_ino
    must0(cli("--db", db, "add", "t4"))
    ino_after = os.stat(db).st_ino
    need(ino_after != ino_before, "更新后 inode 未变 ⇒ 非原子重写 (必须 temp+rename)")
    must0(cli("--db", db, "done", "1"))
    must0(cli("--db", db, "expire"))
    leftovers = [os.path.basename(p) for p in glob.glob(os.path.join(d, "*")) if "tmp" in os.path.basename(p).lower()]
    need(leftovers == [], "临时文件残留: %s" % leftovers)
    json.loads(open(db, "r", encoding="utf-8").read())  # 文件仍是合法 JSON


def test_list_filter_and_order():
    db = dbpath("c12")
    for t in ("a", "b", "c"):
        must0(cli("--db", db, "add", t))
    must0(cli("--db", db, "done", "2"))
    rc, out, _ = cli("--db", db, "list")
    need([x["id"] for x in jobj(out, rc)["tasks"]] == [1, 3], "open 视图必须按 id 升序: %s" % out[:160])
    rc, out, _ = cli("--db", db, "list", "--status", "done")
    need([x["id"] for x in jobj(out, rc)["tasks"]] == [2], "done 视图: %s" % out[:160])
    rc, out, _ = cli("--db", db, "list", "--status", "all")
    need([x["id"] for x in jobj(out, rc)["tasks"]] == [1, 2, 3], "all 视图顺序: %s" % out[:160])


def must0(res):
    rc, out, err = res
    need(rc == 0, "前置命令 rc=%d out=%s err=%s" % (rc, out[:80], err[:80]))


ALL = [
    test_add_creates_and_lists,
    test_id_monotonic_no_reuse,
    test_unicode_roundtrip,
    test_done_idempotent,
    test_done_unknown_id,
    test_bad_request_exit2,
    test_ttl_expiry_uses_injected_clock,
    test_stats_counts_three_states,
    test_expire_removes_expired_tasks,
    test_persistence_across_processes,
    test_no_temp_residue,
    test_list_filter_and_order,
]

for _fn in ALL:
    case(_fn)

if FAILS:
    print("SUMMARY %d/%d FAIL" % (len(FAILS), len(ALL)))
    sys.exit(1)
print("SUMMARY 12/12 PASS")
sys.exit(0)
