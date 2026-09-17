"""kvsvc: 纯标准库实现的带 TTL 的 JSON 键值存储服务。

入口: python3 -m kvsvc.server --port PORT --wal PATH
"""

__version__ = "1.0.0"

__all__ = ["store", "server"]
