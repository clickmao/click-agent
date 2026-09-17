"""kvsvc - 基于 Python 3 标准库的带过期时间(TTL)键值存储服务。

包结构:
    kvsvc/__init__.py  包入口, 导出公共符号
    kvsvc/store.py     存储内核: TTL / incr 原子性 / WAL 追加与重放
    kvsvc/server.py    HTTP 服务: 路由 + JSON 响应 + 线程化并发

入口:
    python3 -m kvsvc.server --port <int> --wal <path>
"""

from .store import KVStore, WALError  # noqa: F401

__all__ = ["KVStore", "WALError"]
__version__ = "1.0.0"
