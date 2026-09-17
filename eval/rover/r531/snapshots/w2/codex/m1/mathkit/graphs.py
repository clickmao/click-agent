"""Graph algorithms."""


def shortest(args: dict) -> str:
    matrix = args["matrix"]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    inf = float("inf")
    dist = [inf] * n
    dist[src] = 0
    visited = [False] * n
    for _ in range(n):
        u = -1
        best = inf
        for i in range(n):
            if not visited[i] and dist[i] < best:
                best = dist[i]
                u = i
        if u == -1:
            break
        visited[u] = True
        for v in range(n):
            w = int(matrix[u][v])
            if w > 0 and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return str(int(dist[dst])) if dist[dst] != inf else "-1"
