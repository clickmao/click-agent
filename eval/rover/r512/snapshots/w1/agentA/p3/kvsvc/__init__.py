"""kvsvc: 带过期时间的键值存储服务(仅 Python 3 标准库)。

包结构:
    kvsvc/__init__.py   # 本文件
    kvsvc/store.py      # KvStore: 线程安全 + WAL 持久化 + TTL
    kvsvc/server.py     # 入口: python3 -m kvsvc.server --port P --wal PATH
"""

from .store import KvStore

__all__ = ["KvStore"]
