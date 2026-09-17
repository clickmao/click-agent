"""Graph ops: shortest path on a weighted undirected adjacency matrix."""

import heapq


def shortest(args: dict) -> str:
    """Dijkstra shortest path length from ``src`` to ``dst``; -1 if unreachable.

    Matrix entry 0 means "no edge" (weights are positive), and the matrix is
    symmetric (undirected graph).
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

    return "-1" if dist[dst] is None else str(dist[dst])
