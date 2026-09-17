"""kvsvc: 带过期时间的键值存储服务 (仅 Python 3 标准库).

入口: python3 -m kvsvc.server --port <int> --wal <path>
"""

__all__ = ["store", "server"]
__version__ = "1.0.0"
