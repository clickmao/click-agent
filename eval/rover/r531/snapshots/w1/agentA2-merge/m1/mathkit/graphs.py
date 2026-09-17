"""图论相关纯函数算子。

每个算子签名 ``op(args: dict) -> str``, 返回应写出的 stdout 文本 (末尾无换行)。
"""

import heapq


def shortest(args: dict) -> str:
    """带权无向图 (邻接矩阵, 0=无边) 上 src 到 dst 的最短路径长度。

    使用 Dijkstra 算法; 边权保证为正 (非零即权), 不可达返回 "-1"。
    自环 (src == dst) 长度为 0。
    """
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)

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
            if w != 0 and d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))

    if dist[dst] == INF:
        return "-1"
    return str(dist[dst])
