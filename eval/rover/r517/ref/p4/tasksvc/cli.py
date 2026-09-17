"""tasksvc CLI 入口 (python3 -B -m tasksvc.cli)。

契约 (prompt 逐条):
  · 每条命令向 stdout 打印**恰好一个** JSON 对象 (ensure_ascii=False) + 换行; 不打别的。
  · 退出码: 0 成功 / 2 参数错 {"error":"bad_request"} / 3 未知 id {"error":"not_found"} / 4 存储损坏 {"error":"bad_store"}。
  · --db <path> 数据文件; --now <epoch> 注入时钟 (默认 time.time())。
  · 子命令: add <text> [--ttl N] / list [--status open|done|expired|all] / done <id> / stats / expire。
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from tasksvc import model, store

EXIT_OK = 0
EXIT_BAD = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4


class CliError(Exception):
    """带退出码的显式失败 (>2 用)。"""

    def __init__(self, code, error):
        super().__init__(error)
        self.code = code
        self.error = error


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()


def build_parser():
    ap = argparse.ArgumentParser(prog="tasksvc", add_help=True)
    ap.add_argument("--db", required=True, help="数据文件路径 (JSON)")
    ap.add_argument("--now", default=None, help="注入时钟 (epoch 秒, 浮点/整数)")
    sub = ap.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add")
    p_add.add_argument("text")
    p_add.add_argument("--ttl", default=None)

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", default="open", choices=list(model.STATUSES))

    p_done = sub.add_parser("done")
    p_done.add_argument("id")

    sub.add_parser("stats")
    sub.add_parser("expire")
    return ap


def now_of(args):
    if args.now is None:
        return time.time()
    try:
        return float(args.now)
    except (TypeError, ValueError) as exc:
        raise model.BadInput("now_not_number") from exc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # 缺子命令 ⇒ bad_request (不用 argparse 的 SystemExit(2) 文案, 保持输出面统一)
    if not argv or argv[-1] in ("-h", "--help"):
        emit({"error": "bad_request"})
        return EXIT_BAD
    try:
        ap = build_parser()
        try:
            args = ap.parse_args(argv)
        except SystemExit:
            emit({"error": "bad_request"})
            return EXIT_BAD
        if not args.cmd:
            raise model.BadInput("no_command")
        now = now_of(args)
        state = store.load(args.db)

        if args.cmd == "add":
            text = model.normalize_text(args.text)
            ttl = model.parse_ttl(args.ttl)
            task = model.make_task(state["next_id"], text, now, ttl)
            state["tasks"].append(task)
            state["next_id"] = int(state["next_id"]) + 1
            store.save(args.db, state)
            emit({"task": task})
            return EXIT_OK

        if args.cmd == "list":
            emit({"tasks": model.view(state["tasks"], now, args.status)})
            return EXIT_OK

        if args.cmd == "done":
            tid = model.parse_id(args.id)
            hit = None
            for t in state["tasks"]:
                if int(t["id"]) == tid:
                    hit = t
                    break
            if hit is None:
                raise CliError(EXIT_NOT_FOUND, "not_found")
            hit["done"] = True          # 幂等: 已是 done 仍返回 0
            store.save(args.db, state)
            emit({"task": hit})
            return EXIT_OK

        if args.cmd == "stats":
            counts = {"total": 0, "open": 0, "done": 0, "expired": 0}
            for t in state["tasks"]:
                counts["total"] += 1
                counts[model.status_of(t, now)] += 1
            emit(counts)
            return EXIT_OK

        if args.cmd == "expire":
            kept, gone = [], []
            for t in state["tasks"]:
                if model.is_expired(t, now):
                    gone.append(int(t["id"]))
                else:
                    kept.append(t)
            if gone:
                state["tasks"] = kept
                store.save(args.db, state)
            emit({"expired": sorted(gone)})
            return EXIT_OK

        raise model.BadInput("unknown_command")
    except model.BadInput as exc:
        emit({"error": "bad_request"})
        return EXIT_BAD
    except CliError as exc:
        emit({"error": exc.error})
        return exc.code
    except store.StoreError:
        emit({"error": "bad_store"})
        return EXIT_BAD_STORE


if __name__ == "__main__":
    raise SystemExit(main())
