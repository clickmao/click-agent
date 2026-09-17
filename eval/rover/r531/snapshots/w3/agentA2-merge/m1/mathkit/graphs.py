"""Graph op: `shortest` (weighted undirected shortest path)."""

from typing import Dict, List


def shortest(args: Dict) -> str:
    """Dijkstra on an adjacency matrix (0 = no edge, symmetric).

    Returns the shortest path length from `src` to `dst`, or -1 when
    unreachable. Edge weights are positive.
    """
    matrix: List[List[int]] = args["matrix"]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    if n == 0:
        return "-1"
    if not (0 <= src < n and 0 <= dst < n):
        return "-1"
    if src == dst:
        return "0"

    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    visited = [False] * n

    for _ in range(n):
        u = -1
        best = INF
        for i in range(n):
            if not visited[i] and dist[i] < best:
                best = dist[i]
                u = i
        if u == -1:
            break
        visited[u] = True
        if u == dst:
            break
        for v in range(n):
            w = int(matrix[u][v])
            if w > 0 and not visited[v]:
                nd = dist[u] + w
                if nd < dist[v]:
                    dist[v] = nd

    return "-1" if dist[dst] == INF else str(int(dist[dst]))
