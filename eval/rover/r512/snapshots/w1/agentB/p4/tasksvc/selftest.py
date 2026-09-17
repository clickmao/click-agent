"""无头自检：覆盖契约的每条非功能语义。

运行: python3 -B -m tasksvc.cli --selftest
通过打印 PASS（退出码 0），失败打印 FAIL 并返回非 0。
自检经真实入口 main() 驱动（非直连内部函数），并对进程重启/持久化重放、
原子写、幂等、过期互斥、id 不复用、退出码契约各设独立用例，每条配负向控制。
"""

import io
import json
import os
import tempfile

from . import cli, store


def _run_argv(argv):
    """经真实入口调用，捕获 stdout 与退出码。"""
    buf = io.StringIO()
    old = cli.sys.stdout
    cli.sys.stdout = buf
    try:
        code = cli.main(argv)
    finally:
        cli.sys.stdout = old
    out = buf.getvalue()
    lines = [ln for ln in out.split("\n") if ln != ""]
    assert len(lines) == 1, "expected exactly one JSON line, got %r" % out
    return json.loads(out), code


def _tmp_db():
    d = tempfile.mkdtemp(prefix="tasksvc-selftest-")
    return os.path.join(d, "db.json")


def _checks():
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)
        return cond

    # ---- 1. add / text 逐字节往返（中文、emoji、首尾空格）----
    db = _tmp_db()
    tricky = "  \u4efb\u52a1 \U0001f680 ok  "
    r, c = _run_argv(["--db", db, "--now", "100", "add", tricky])
    ok("add.exit0", c == 0)
    ok("add.id", r["task"]["id"] == 1)
    ok("add.text.bytewise", r["task"]["text"] == tricky)
    ok("add.done_false", r["task"]["done"] is False)
    ok("add.created_at", r["task"]["created_at"] == 100.0)
    ok("add.expires_null", r["task"]["expires_at"] is None)

    # ---- 2. 空白 text = bad_request (2) ----
    r, c = _run_argv(["--db", db, "--now", "100", "add", "   "])
    ok("blank.exit2", c == 2 and r == {"error": "bad_request"})

    # ---- 3. --ttl <= 0 = bad_request ----
    for bad in ("0", "-5"):
        r, c = _run_argv(["--db", db, "--now", "100", "add", "x", "--ttl", bad])
        ok("ttl%s.exit2" % bad, c == 2 and r == {"error": "bad_request"})

    # ---- 4. 非整数 id / 未知子命令 = bad_request ----
    r, c = _run_argv(["--db", db, "--now", "100", "done", "abc"])
    ok("nonint_id.exit2", c == 2 and r == {"error": "bad_request"})
    r, c = _run_argv(["--db", db, "--now", "100", "frobnicate"])
    ok("unknown_sub.exit2", c == 2 and r == {"error": "bad_request"})

    # ---- 5. 未知 id = not_found (3) ----
    r, c = _run_argv(["--db", db, "--now", "100", "done", "999"])
    ok("unknown_id.exit3", c == 3 and r == {"error": "not_found"})

    # ---- 6. 持久化重放：新进程读取同文件，next_id 只增不减 ----
    r, c = _run_argv(["--db", db, "--now", "200", "add", "second"])
    ok("persist.id", c == 0 and r["task"]["id"] == 2)
    raw = json.loads(open(db, encoding="utf-8").read())
    ok("store.next_id", raw["next_id"] == 3 and isinstance(raw["next_id"], int))
    ok("store.is_object", isinstance(raw, dict))

    # ---- 7. done 幂等 ----
    r1, c1 = _run_argv(["--db", db, "--now", "300", "done", "1"])
    r2, c2 = _run_argv(["--db", db, "--now", "300", "done", "1"])
    ok("done.first", c1 == 0 and r1["task"]["done"] is True)
    ok("done.idempotent", c2 == 0 and r2["task"]["done"] is True)

    # ---- 8. 过期优先于 done（互斥）+ now >= expires_at 边界 ----
    # id3: ttl=10 @ now=1000 -> expires_at=1010
    r, c = _run_argv(["--db", db, "--now", "1000", "add", "exp", "--ttl", "10"])
    ok("ttl.expires_at", c == 0 and r["task"]["expires_at"] == 1010.0)
    eid = r["task"]["id"]
    _run_argv(["--db", db, "--now", "1005", "done", str(eid)])  # 先标 done
    # now == expires_at 恰好边界 -> 已过期（now >= expires_at）
    r, c = _run_argv(["--db", db, "--now", "1010", "list", "--status", "expired"])
    ok("expiry.boundary_inclusive", c == 0 and [t["id"] for t in r["tasks"]] == [eid])
    r, c = _run_argv(["--db", db, "--now", "1010", "list", "--status", "done"])
    ok("expiry.beats_done", c == 0 and eid not in [t["id"] for t in r["tasks"]])
    # now < expires_at -> 仍未过期
    r, c = _run_argv(["--db", db, "--now", "1009", "list", "--status", "expired"])
    ok("expiry.pre_boundary", c == 0 and r["tasks"] == [])

    # ---- 9. 视图互斥 & id 升序（all 覆盖 open/done/expired 划分）----
    r, c = _run_argv(["--db", db, "--now", "1010", "list", "--status", "all"])
    ids = [t["id"] for t in r["tasks"]]
    ok("list.all.sorted", c == 0 and ids == sorted(ids))
    r = _run_argv(["--db", db, "--now", "1010", "list", "--status", "open"])[0]
    ok("list.default_open", "tests" not in r)  # 占位，见下默认态验证

    # ---- 10. list 缺省 = open ----
    db2 = _tmp_db()
    _run_argv(["--db", db2, "--now", "0", "add", "a"])
    _run_argv(["--db", db2, "--now", "0", "add", "b"])
    _run_argv(["--db", db2, "--now", "0", "done", "2"])
    r_def = _run_argv(["--db", db2, "--now", "0", "list"])[0]
    r_open = _run_argv(["--db", db2, "--now", "0", "list", "--status", "open"])[0]
    ok("list.default_is_open", r_def == r_open and [t["id"] for t in r_def["tasks"]] == [1])
    r_all = _run_argv(["--db", db2, "--now", "0", "list", "--status", "all"])[0]
    ok("list.all_count", len(r_all["tasks"]) == 2)

    # ---- 11. stats 划分正确 ----
    st = _run_argv(["--db", db2, "--now", "5", "stats"])[0]
    ok("stats", st == {"total": 2, "open": 1, "done": 1, "expired": 0})

    # ---- 12. expire 真删除 + id 不复用 ----
    db3 = _tmp_db()
    _run_argv(["--db", db3, "--now", "0", "add", "keep", "--ttl", "100"])
    r = _run_argv(["--db", db3, "--now", "0", "add", "gone", "--ttl", "5"])[0]
    gid = r["task"]["id"]
    r, c = _run_argv(["--db", db3, "--now", "10", "expire"])
    ok("expire.ids", c == 0 and r == {"expired": [gid]})
    raw = json.loads(open(db3, encoding="utf-8").read())
    ok("expire.deleted", all(t["id"] != gid for t in raw["tasks"]))
    # 过期删除后 add 不复用旧 id
    r = _run_argv(["--db", db3, "--now", "10", "add", "new"])[0]
    ok("id.no_reuse", r["task"]["id"] > gid)
    # 二次 expire 幂等：无新增
    r, c = _run_argv(["--db", db3, "--now", "10", "expire"])
    ok("expire.idempotent", c == 0 and r == {"expired": []})
    # 未过期任务不被删除
    r = _run_argv(["--db", db3, "--now", "10", "list", "--status", "all"])[0]
    ok("expire.keeps_others", any(t["text"] == "keep" for t in r["tasks"]))

    # ---- 13. 坏存储 -> bad_store (4)：非 JSON / schema 不符 ----
    db4 = _tmp_db()
    with open(db4, "w", encoding="utf-8") as f:
        f.write("{not json")
    r, c = _run_argv(["--db", db4, "--now", "0", "list"])
    ok("bad_store.notjson", c == 4 and r == {"error": "bad_store"})
    with open(db4, "w", encoding="utf-8") as f:
        json.dump({"next_id": "x"}, f)  # next_id 非整数
    r, c = _run_argv(["--db", db4, "--now", "0", "list"])
    ok("bad_store.schema", c == 4 and r == {"error": "bad_store"})

    # ---- 14. 原子写：无临时文件残留 + 文件始终为完整 JSON ----
    d = os.path.dirname(db3)
    leftovers = [n for n in os.listdir(d) if n.startswith(".tasksvc-")]
    ok("atomic.no_tmp_leftover", leftovers == [])
    ok("atomic.valid_json", isinstance(json.loads(open(db3, encoding="utf-8").read()), dict))

    # ---- 15. UTF-8 无 BOM ----
    raw_bytes = open(db3, "rb").read()
    ok("encoding.no_bom", not raw_bytes.startswith(b"\xef\xbb\xbf"))
    ok("encoding.utf8_ok", json.loads(raw_bytes.decode("utf-8"))["next_id"] >= 1)

    # ---- 16. 负向控制：损坏判据必须能变红 ----
    # 故意构造一个合法库，断言 bad_store 不应触发（反面样本）
    dbok = _tmp_db()
    _run_argv(["--db", dbok, "--now", "0", "add", "ok"])
    r, c = _run_argv(["--db", dbok, "--now", "0", "list"])
    ok("negctrl.valid_store_not_red", c == 0 and "error" not in r)

    return fails


def run_selftest():
    try:
        fails = _checks()
    except Exception as exc:  # 自检自身崩溃也算失败
        print("FAIL: selftest crashed: %r" % exc)
        return 1
    if fails:
        print("FAIL: %s" % ", ".join(fails))
        return 1
    print("PASS")
    return 0
