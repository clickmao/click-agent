"""kvsvc —— 仅用 Python 3 标准库实现的带 TTL 键值存储服务。

包结构:
    kvsvc/__init__.py   包声明
    kvsvc/store.py      存储内核 (TTL / 惰性过期 / WAL 持久化 / 线程安全)
    kvsvc/server.py     HTTP 服务入口

启动:
    python3 -m kvsvc.server --port 8080 --wal /abs/path/wal.jsonl
"""

__all__ = ["store", "server"]
