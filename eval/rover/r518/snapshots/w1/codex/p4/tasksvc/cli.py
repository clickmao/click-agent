"""Command line interface for tasksvc.

Usage:
    python3 -B -m tasksvc.cli [--db PATH] [--now EPOCH] <command> [args]

Commands:
    add <text> [--ttl SECONDS]
    list [--status open|done|expired|all]
    done <id>
    stats
    expire
"""

import argparse
import json
import os
import sys
import time

from . import model
from .store import BadStoreError, load, save

BAD_REQUEST = "bad_request"
NOT_FOUND = "not_found"
BAD_STORE = "bad_store"


class CliError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


class Parser(argparse.ArgumentParser):
    """Argument parser that raises CliError instead of printing to stderr."""

    def error(self, message):
        raise CliError(message, BAD_REQUEST)

    def exit(self, status=0, message=None):
        raise CliError(message or "", BAD_REQUEST)


def jsonable_number(raw):
    """Parse an epoch/ttl argument as float or int."""
    try:
        if any(char in raw for char in ".eE"):
            return float(raw)
        return int(raw)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("expected a number")


def build_parser():
    parser = Parser(prog="tasksvc.cli", add_help=True)
    parser.add_argument("--db", default="tasks.json")
    parser.add_argument("--now", type=jsonable_number, default=None)

    subparsers = parser.add_subparsers(dest="command")

    add = subparsers.add_parser("add", add_help=True)
    add.add_argument("text")
    add.add_argument("--ttl", type=jsonable_number, default=None)

    list_cmd = subparsers.add_parser("list", add_help=True)
    list_cmd.add_argument("--status", choices=["open", "done", "expired", "all"], default="open")

    done = subparsers.add_parser("done", add_help=True)
    done.add_argument("id")

    subparsers.add_parser("stats", add_help=True)
    subparsers.add_parser("expire", add_help=True)
    return parser


def parse_args(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except CliError:
        raise
    if not args.command:
        raise CliError("missing command", BAD_REQUEST)

    if args.command == "add":
        if args.text.strip() == "":
            raise CliError("blank text", BAD_REQUEST)
        if args.ttl is not None:
            ttl = args.ttl
            if ttl <= 0:
                raise CliError("ttl must be positive", BAD_REQUEST)
    elif args.command == "done":
        try:
            args.id = int(args.id)
        except (TypeError, ValueError):
            raise CliError("id must be an integer", BAD_REQUEST)
    return args


def emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


def now_from(args):
    if args.now is None:
        return float(time.time())
    return float(args.now)


def run(argv):
    args = parse_args(argv)
    now = now_from(args)
    data = load(args.db)

    if args.command == "add":
        task = {
            "id": data["next_id"],
            "text": args.text,
            "done": False,
            "created_at": now,
            "expires_at": None,
        }
        if args.ttl is not None:
            task["expires_at"] = now + float(args.ttl)
        data["next_id"] = data["next_id"] + 1
        data.setdefault("tasks", []).append(task)
        save(args.db, data)
        emit({"task": model.public(task)})
        return 0

    if args.command == "list":
        tasks = model.select(data, args.status, now)
        emit({"tasks": [model.public(task) for task in tasks]})
        return 0

    if args.command == "done":
        for task in data.get("tasks", []):
            if task["id"] == args.id:
                if not task.get("done"):
                    task["done"] = True
                    save(args.db, data)
                emit({"task": model.public(task)})
                return 0
        raise CliError("unknown id", NOT_FOUND)

    if args.command == "stats":
        tasks = data.get("tasks", [])
        open_count = done_count = expired_count = 0
        for task in tasks:
            status = model.status_of(task, now)
            if status == "expired":
                expired_count += 1
            elif status == "done":
                done_count += 1
            else:
                open_count += 1
        emit(
            {
                "total": len(tasks),
                "open": open_count,
                "done": done_count,
                "expired": expired_count,
            }
        )
        return 0

    if args.command == "expire":
        expired_ids = model.purge_expired(data, now)
        if expired_ids:
            save(args.db, data)
        emit({"expired": expired_ids})
        return 0

    raise CliError("unknown command", BAD_REQUEST)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        code = run(argv)
    except CliError as exc:
        emit({"error": exc.code})
        return 2 if exc.code == BAD_REQUEST else 3
    except BadStoreError:
        emit({"error": BAD_STORE})
        return 4
    except (OSError, ValueError):
        emit({"error": BAD_STORE})
        return 4
    return code if code is not None else 0


if __name__ == "__main__":
    sys.exit(main())
