"""Command line interface for the task queue service.

Usage:
    python3 -B -m tasksvc.cli [--db PATH] [--now EPOCH] <command> [args]
"""

import argparse
import json
import sys
import time

from . import service, store


EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4


class BadRequest(Exception):
    """Raised for usage/argument errors detected after parsing."""


class _ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that reports usage errors with exit code 2 and no stderr noise."""

    def error(self, message):
        raise BadRequest(message)

    def exit(self, status=0, message=None):
        if status:
            raise BadRequest(message or "usage error")
        raise SystemExit(status)


def build_parser():
    parser = _ArgumentParser(prog="tasksvc", add_help=True)
    parser.add_argument("--db", required=True, metavar="PATH")
    parser.add_argument("--now", type=float, default=None, metavar="EPOCH")
    sub = parser.add_subparsers(dest="command")

    add_parser = sub.add_parser("add")
    add_parser.add_argument("text")
    add_parser.add_argument("--ttl", type=float, default=None)

    list_parser = sub.add_parser("list")
    list_parser.add_argument(
        "--status", choices=["open", "done", "expired", "all"], default="open"
    )

    done_parser = sub.add_parser("done")
    done_parser.add_argument("id")

    sub.add_parser("stats")
    sub.add_parser("expire")
    return parser


def emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def parse_task_id(raw):
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise BadRequest("id must be an integer")


def resolve_now(args):
    return time.time() if args.now is None else float(args.now)


def run(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if not args.command:
            raise BadRequest("missing command")
    except SystemExit as exc:
        if exc.code:
            emit({"error": "bad_request"})
            return EXIT_BAD_REQUEST
        raise
    except BadRequest:
        emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST

    now = resolve_now(args)

    if args.command == "add":
        if args.ttl is not None and not args.ttl > 0:
            emit({"error": "bad_request"})
            return EXIT_BAD_REQUEST
        if not args.text.strip():
            emit({"error": "bad_request"})
            return EXIT_BAD_REQUEST
    if args.command == "done":
        try:
            task_id = parse_task_id(args.id)
        except BadRequest:
            emit({"error": "bad_request"})
            return EXIT_BAD_REQUEST
    else:
        task_id = None

    try:
        data = store.load(args.db)
    except store.BadStore:
        emit({"error": "bad_store"})
        return EXIT_BAD_STORE

    try:
        if args.command == "add":
            task = service.add(data, args.text, now, args.ttl)
            store.save(args.db, data)
            emit({"task": service.view(task)})
        elif args.command == "list":
            tasks = service.list_tasks(data, now, args.status)
            emit({"tasks": [service.view(task) for task in tasks]})
        elif args.command == "done":
            task = service.mark_done(data, task_id, now)
            store.save(args.db, data)
            emit({"task": service.view(task)})
        elif args.command == "stats":
            emit(service.stats(data, now))
        elif args.command == "expire":
            expired = service.expire(data, now)
            if expired:
                store.save(args.db, data)
            emit({"expired": expired})
    except service.NotFound:
        emit({"error": "not_found"})
        return EXIT_NOT_FOUND
    except store.BadStore:
        emit({"error": "bad_store"})
        return EXIT_BAD_STORE
    except RecursionError:
        emit({"error": "bad_store"})
        return EXIT_BAD_STORE

    return EXIT_OK


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        code = run(argv)
    except BrokenPipeError:
        return EXIT_OK
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        return EXIT_OK
    return code


if __name__ == "__main__":
    raise SystemExit(main())
