"""Graph ops."""

import heapq


def shortest(args: dict) -> str:
    """Shortest path length in a weighted undirected graph; -1 if unreachable."""
    matrix = args["matrix"]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            w = int(matrix[i][j])
            if w:
                adj[i].append((j, w))
    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        if u == dst:
            return str(d)
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return str(dist[dst]) if dist[dst] != INF else "-1"
