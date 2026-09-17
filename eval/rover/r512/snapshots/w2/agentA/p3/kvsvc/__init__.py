"""kvsvc —— 仅用 Python 3 标准库实现的带过期时间的键值存储服务。

包结构:
    kvsvc/__init__.py   包入口(本文件)
    kvsvc/store.py      存储核心(线程安全 + TTL + WAL 持久化)
    kvsvc/server.py     HTTP 服务(threading + 路由), 入口: python3 -m kvsvc.server

运行:
    python3 -m kvsvc.server --port 8080 --wal /tmp/kv.wal
自检:
    python3 -m kvsvc.server --selftest      # 无头, 打印 PASS/FAIL, 退出码 0=通过
"""

from .store import KVStore, WAL_FILENAME  # noqa: F401

__all__ = ["KVStore", "WAL_FILENAME"]
