"""Graph algorithms (pure functions)."""


def shortest(args: dict) -> str:
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
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
        for v in range(n):
            w = matrix[u][v]
            if w and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    if dist[dst] == INF:
        return "-1"
    return str(dist[dst])
