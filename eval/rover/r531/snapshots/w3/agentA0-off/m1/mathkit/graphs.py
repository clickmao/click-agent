"""图算法相关 op：shortest。每个 op 导出 op(args: dict) -> str。"""

import heapq


def shortest(args: dict) -> str:
    """带权无向图邻接矩阵 (0 = 无边, 对称) 上 src 到 dst 的最短路径长度；不可达返回 -1。

    Dijkstra + 邻接矩阵展开。
    """
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    if src == dst:
        return "0"

    dist = [None] * n
    dist[src] = 0
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if dist[u] is not None and d > dist[u]:
            continue
        if u == dst:
            return str(d)
        for v in range(n):
            w = matrix[u][v]
            if w == 0 or v == u:
                continue
            nd = d + w
            if dist[v] is None or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return str(dist[dst]) if dist[dst] is not None else "-1"
