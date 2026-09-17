"""Graph ops. Each op is a pure function op(args: dict) -> str."""

import heapq


def shortest(args: dict) -> str:
    """Shortest path length on a weighted undirected adjacency matrix.

    0 entries mean "no edge". Unreachable -> -1.
    """
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    if src < 0 or src >= n or dst < 0 or dst >= n:
        return "-1"
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
            if w > 0 and d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    if dist[dst] == INF:
        return "-1"
    return str(dist[dst])
