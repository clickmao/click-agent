"""图论相关 op：shortest（带权无向图最短路）。

纯函数，无 I/O，无第三方依赖（Dijkstra + 标准库 heapq）。
"""

import heapq


def shortest(args: dict) -> str:
    """邻接矩阵上 src 到 dst 的最短路径长度；不可达输出 -1。

    参数: matrix（n×n 整数二维数组, 0 表示无边, 对称）, src, dst。
    返回: 最短距离的十进制字符串，或 "-1"。
    """
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    if src == dst:
        return "0"

    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == dst:
            break
        for v in range(n):
            w = matrix[u][v]
            if w == 0:
                continue
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))

    if dist[dst] == INF:
        return "-1"
    return str(int(dist[dst]))
