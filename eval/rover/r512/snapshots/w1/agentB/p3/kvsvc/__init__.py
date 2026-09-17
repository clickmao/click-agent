"""kvsvc: 标准库实现的带 TTL 的线程安全键值存储服务。

模块划分:
    kvsvc.store  —— 内存存储 + WAL 持久化 + 过期语义 (纯逻辑, 无 IO 框架依赖)
    kvsvc.server —— HTTP 服务 (http.server.ThreadingHTTPServer) + 自检入口
"""

from .store import KVStore

__all__ = ["KVStore"]
