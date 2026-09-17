"""kvsvc —— 纯标准库实现的带 TTL 键值存储服务。

入口:  python3 -m kvsvc.server --port <int> --wal <path>
"""

__all__ = ["store", "server"]
