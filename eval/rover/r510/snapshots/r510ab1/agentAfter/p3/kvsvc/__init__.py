"""kvsvc —— 纯标准库实现的带过期时间(TTL)的键值存储服务。

包结构:
    kvsvc/__init__.py   包导出
    kvsvc/store.py      存储核心(线程安全 / TTL / WAL 重放)
    kvsvc/server.py     HTTP 服务入口 (python3 -m kvsvc.server)

运行:
    python3 -m kvsvc.server --port 8000 --wal /tmp/kv.wal
    python3 -m kvsvc.server --selftest        # 无头自检, 退出码 0=PASS / 1=FAIL
"""

from .store import KVStore

__all__ = ["KVStore"]
__version__ = "1.0.0"
