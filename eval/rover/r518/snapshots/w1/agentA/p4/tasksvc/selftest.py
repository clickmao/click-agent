#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tasksvc.selftest —— 无头自检，经**真实入口**（子进程跑 tasksvc.cli）驱动。

运行: python3 -B -m tasksvc.selftest
输出: 每条用例一行 PASS/FAIL，结尾 SELFTEST PASS / SELFTEST FAIL；
      退出码 0 = 全部通过，1 = 有失败。
"""

import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = []


def test(func):
    TESTS.append(func)
    return func


# ---------------------------------------------------------------- 驱动辅助

def cli(args, expect_code=0):
    """跑真实 CLI，返回解析后的 JSON 对象；同时机械校验「恰好一个 JSON 对象」契约。"""
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "tasksvc.cli"] + list(args),
        cwd=ROOT, capture_output=True,
    )
    out = proc.stdout.decode("utf-8")
    assert proc.returncode == expect_code, (
        "exit=%r want=%r args=%r out=%r err=%r"
        % (proc.returncode, expect_code, args, out, proc.stderr.decode("utf-8", "replace"))
    )
    assert out.endswith("\n") and out.count("\n") == 1, "stdout 必须是单个 JSON + 一个尾换行: %r" % out
    obj = json.loads(out)  # 多余内容会在此处失败
    assert isinstance(obj, dict), "顶层必须是 JSON 对象"
    return obj


def read_store(path):
    with open(path, "rb") as handle:
        raw = handle.read()
    assert not raw.startswith(b"\xef\xbb\xbf"), "存储文件不得带 BOM"
    return json.loads(raw.decode("utf-8"))


def dir_entries(directory):
    return sorted(os.listdir(directory))


# ---------------------------------------------------------------- 用例

@test
def t01_add_fields_and_persist():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        obj = cli(["--db", db, "--now", "1000", "add", "hello"])
        task = obj["task"]
        assert set(task) == {"id", "text", "done", "created_at", "expires_at"}, task
        assert task["id"] == 1 and task["text"] == "hello" and task["done"] is False
        assert task["created_at"] == 1000.0 and task["expires_at"] is None, task
        store = read_store(db)
        assert isinstance(store["next_id"], int) and not isinstance(store["next_id"], bool)
        assert store["next_id"] == 2, store
        assert dir_entries(d) == ["s.json"], "不得留下临时文件残留"


@test
def t02_text_byte_exact_roundtrip():
    samples = ["中文 文本", "emoji 🎉🚀 混排", "  leading and trailing  ", "tab\tinside", "  "]
    bad = []
    for idx, text in enumerate(samples):
        if text.strip() == "" or text.startswith("--"):
            continue
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.json")
            obj = cli(["--db", db, "--now", "5", "add", text])
            if obj["task"]["text"] != text:
                bad.append(("add", text, obj["task"]["text"]))
            listed = cli(["--db", db, "--now", "5", "list", "--status", "all"])["tasks"]
            if listed[0]["text"] != text:
                bad.append(("list", text, listed[0]["text"]))
            # 负向控制: 首尾空格绝不能被裁剪
            if text != text.strip() and listed[0]["text"] == text.strip():
                bad.append(("trimmed!", text, listed[0]["text"]))
    assert not bad, bad


@test
def t03_now_fallback_to_system_clock():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        before = time.time()
        obj = cli(["--db", db, "add", "no-now"])       # 不给 --now 必须成功
        after = time.time()
        created = obj["task"]["created_at"]
        assert before - 1 <= created <= after + 1, (before, created, after)
        assert isinstance(created, float), created


@test
def t04_ttl_boundary_now_ge_expires_is_expired():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        task = cli(["--db", db, "--now", "1000", "add", "x", "--ttl", "10"])["task"]
        assert task["expires_at"] == 1010.0, task
        open_at_1009 = cli(["--db", db, "--now", "1009", "list"])["tasks"]
        assert [t["id"] for t in open_at_1009] == [1], open_at_1009
        at_1010 = cli(["--db", db, "--now", "1010", "list"])
        assert at_1010["tasks"] == [], at_1010            # now == expires_at 即过期
        expired = cli(["--db", db, "--now", "1010", "list", "--status", "expired"])["tasks"]
        assert [t["id"] for t in expired] == [1], expired


@test
def t05_expire_really_deletes_and_ids_never_reused():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        cli(["--db", db, "--now", "1000", "add", "a", "--ttl", "5"])
        cli(["--db", db, "--now", "1000", "add", "b", "--ttl", "5"])
        cli(["--db", db, "--now", "1000", "add", "c"])          # 永不过期
        out = cli(["--db", db, "--now", "1006", "expire"])
        assert out["expired"] == [1, 2], out
        store = read_store(db)
        assert [t["id"] for t in store["tasks"]] == [3], store
        assert store["next_id"] == 4, store
        again = cli(["--db", db, "--now", "1006", "expire"])
        assert again["expired"] == [], again
        new_task = cli(["--db", db, "--now", "1006", "add", "d"])["task"]
        assert new_task["id"] == 4, new_task                    # 已删除的 1/2 绝不复用
        assert dir_entries(d) == ["s.json"], "不得留下临时文件残留"


@test
def t06_done_idempotent_and_not_found():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        cli(["--db", db, "--now", "10", "add", "a"])
        first = cli(["--db", db, "--now", "10", "done", "1"])
        assert first["task"]["done"] is True, first
        second = cli(["--db", db, "--now", "11", "done", "1"])   # 幂等，仍成功
        assert second["task"]["done"] is True and second["task"]["id"] == 1, second
        err = cli(["--db", db, "--now", "11", "done", "99"], expect_code=3)
        assert err == {"error": "not_found"}, err


@test
def t07_views_stats_and_id_order():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        cli(["--db", db, "--now", "1000", "add", "t1"])
        cli(["--db", db, "--now", "1000", "add", "t2", "--ttl", "10"])
        cli(["--db", db, "--now", "1000", "add", "t3"])
        cli(["--db", db, "--now", "1000", "add", "t4", "--ttl", "5"])
        cli(["--db", db, "--now", "1000", "done", "1"])

        def ids(status, now="1006"):
            return [t["id"] for t in cli(["--db", db, "--now", now, "list", "--status", status])["tasks"]]

        assert ids("open") == [2, 3], ids("open")
        assert ids("done") == [1], ids("done")
        assert ids("expired") == [4], ids("expired")
        assert ids("all") == [1, 2, 3, 4], ids("all")
        assert [t["id"] for t in cli(["--db", db, "--now", "1006", "list"])["tasks"]] == [2, 3]
        stats = cli(["--db", db, "--now", "1006", "stats"])
        assert stats == {"total": 4, "open": 2, "done": 1, "expired": 1}, stats
        # 过期优先于 done: 对已过期任务执行 done 仍成功，但视图仍归 expired
        done_expired = cli(["--db", db, "--now", "1006", "done", "4"])
        assert done_expired["task"]["done"] is True, done_expired
        assert ids("done") == [1] and ids("expired") == [4]
        stats2 = cli(["--db", db, "--now", "1006", "stats"])
        assert stats2 == {"total": 4, "open": 2, "done": 1, "expired": 1}, stats2


@test
def t08_bad_request_exit2():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        cases = [
            ["--db", db, "--now", "1", "add", ""],
            ["--db", db, "--now", "1", "add", "   "],
            ["--db", db, "--now", "1", "add", "x", "--ttl", "0"],
            ["--db", db, "--now", "1", "add", "x", "--ttl", "-5"],
            ["--db", db, "--now", "1", "add", "x", "--ttl", "abc"],
            ["--db", db, "--now", "1", "done", "abc"],
            ["--db", db, "--now", "1", "done", "1.5"],
            ["--db", db, "--now", "1", "frobnicate"],
            ["--db", db, "--now", "1", "list", "--status", "bogus"],
            ["--db", db, "--now", "1", "list", "extra"],
            ["--now", "1", "list"],                       # 缺 --db
            ["--db", db, "--now", "1"],                   # 缺子命令
            ["--db", db, "--now", "zzz", "list"],         # --now 非数字
        ]
        for args in cases:
            obj = cli(args, expect_code=2)
            assert obj == {"error": "bad_request"}, (args, obj)
        assert dir_entries(d) == [], "参数错不得产生任何存储文件"


@test
def t09_bad_store_exit4():
    with tempfile.TemporaryDirectory() as d:
        bad_payloads = [
            b"not json",
            b"",
            b"   \n",
            b"[]",
            b'{"next_id": "1"}',
            b'{"tasks": []}',
            b'{"next_id": 1, "tasks": {}}',
            b'{"next_id": 1, "tasks": [{"id": 1}]}',
            b'{"next_id": 1, "tasks": [{"id": 1, "text": "x", "done": "no", "created_at": 1.0, "expires_at": null}]}',
            b'{"next_id": -1, "tasks": []}',
            b'{"next_id": 1, "tasks": [{"id": 1, "text": "x", "done": false, "created_at": 1.0, "expires_at": null},'
            b'{"id": 1, "text": "y", "done": false, "created_at": 1.0, "expires_at": null}]}',
        ]
        for idx, payload in enumerate(bad_payloads):
            db = os.path.join(d, "bad%d.json" % idx)
            with open(db, "wb") as handle:
                handle.write(payload)
            obj = cli(["--db", db, "--now", "1", "list"], expect_code=4)
            assert obj == {"error": "bad_store"}, (payload, obj)
            with open(db, "rb") as handle:
                assert handle.read() == payload, "存储损坏时不得改写原文件"


@test
def t10_atomic_write_no_residue_and_always_valid():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        cli(["--db", db, "--now", "1", "add", "a"])
        for step in range(2, 12):
            cli(["--db", db, "--now", "1", "add", "t%d" % step])
            store = read_store(db)                      # 任一时点读到的都是完整 JSON
            assert len(store["tasks"]) == step
            assert store["next_id"] == step + 1
            assert dir_entries(d) == ["s.json"], dir_entries(d)
        cli(["--db", db, "--now", "1", "done", "1"])
        cli(["--db", db, "--now", "1", "stats"])
        assert dir_entries(d) == ["s.json"], "不得留下临时文件残留"


@test
def t11_next_id_monotonic_enforced_by_store():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "s.json")
        cli(["--db", db, "--now", "1", "add", "a"])
        assert read_store(db)["next_id"] == 2
        # 人为把 next_id 抬高（模拟外部写入），必须继续单调、不回退
        store = read_store(db)
        store["next_id"] = 50
        with open(db, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(store, ensure_ascii=False))
        assert cli(["--db", db, "--now", "1", "add", "b"])["task"]["id"] == 50
        assert read_store(db)["next_id"] == 51
        # 删除后再加，也不回退、不复用
        cli(["--db", db, "--now", "1", "expire"])
        assert cli(["--db", db, "--now", "1", "add", "c"])["task"]["id"] == 51


# ---------------------------------------------------------------- 入口

def main():
    failures = []
    for func in TESTS:
        try:
            func()
        except Exception as exc:                      # noqa: BLE001 —— 自检需报告所有失败
            failures.append((func.__name__, exc))
            print("FAIL %s: %s" % (func.__name__, exc))
        else:
            print("PASS %s" % func.__name__)
    if failures:
        print("SELFTEST FAIL (%d/%d)" % (len(failures), len(TESTS)))
        return 1
    print("SELFTEST PASS (%d/%d)" % (len(TESTS), len(TESTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
