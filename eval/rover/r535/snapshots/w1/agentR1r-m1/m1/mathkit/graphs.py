"""Graph operations: shortest."""

import heapq


def shortest(args: dict) -> str:
    matrix = args["matrix"]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    inf = float("inf")
    dist = [inf] * n
    dist[src] = 0
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v in range(n):
            w = int(matrix[u][v])
            if w > 0 and d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (dist[v], v))
    return str(-1 if dist[dst] == inf else dist[dst])
