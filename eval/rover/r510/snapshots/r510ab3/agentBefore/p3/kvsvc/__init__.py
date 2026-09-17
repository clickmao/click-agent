"""kvsvc - 带过期时间的键值存储服务 (仅 Python 3 标准库)。

模块:
    kvsvc.store  -- 内存存储 + WAL 持久化 + 并发安全
    kvsvc.server -- HTTP 服务 (threading HTTPServer)，入口: python3 -m kvsvc.server
"""

from .store import KVStore, WALError

__all__ = ["KVStore", "WALError"]
__version__ = "1.0.0"
