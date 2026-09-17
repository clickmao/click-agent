"""Graph operations (pure functions, op(args)->str)."""

import heapq


def shortest(args: dict) -> str:
    """Shortest path length from src to dst on a weighted undirected graph.

    `matrix` is an adjacency matrix (0 = no edge, symmetric).  Returns -1 when
    dst is unreachable.
    """
    matrix = args["matrix"]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)

    if src == dst:
        return "0"

    dist = [None] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if dist[u] is not None and d > dist[u]:
            continue
        if u == dst:
            return str(d)
        for v in range(n):
            w = matrix[u][v]
            if not w:
                continue
            nd = d + int(w)
            if dist[v] is None or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return "-1"
