"""Graph algorithms: weighted shortest path on adjacency matrices."""

import heapq


def shortest(args: dict) -> str:
    """Shortest path length from src to dst; -1 when unreachable."""
    matrix = args["matrix"]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
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
            if w:
                nd = d + int(w)
                if dist[v] is None or nd < dist[v]:
                    dist[v] = nd
                    heapq.heappush(heap, (nd, v))
    return str(dist[dst]) if dist[dst] is not None else "-1"
