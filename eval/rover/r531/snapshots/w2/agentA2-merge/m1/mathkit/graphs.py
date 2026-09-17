"""Graph ops (pure functions, op(args: dict) -> str)."""


def shortest(args: dict) -> str:
    """Shortest path length on a weighted undirected graph (0 = no edge).

    Returns -1 when `dst` is unreachable from `src`.  Dijkstra with a
    simple O(n^2) scan; non-negative weights only.
    """
    matrix = [list(map(int, row)) for row in args["matrix"]]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    if not (0 <= src < n and 0 <= dst < n):
        return "-1"
    if src == dst:
        return "0"

    INF = float("inf")
    dist = [INF] * n
    done = [False] * n
    dist[src] = 0
    for _ in range(n):
        u = -1
        best = INF
        for v in range(n):
            if not done[v] and dist[v] < best:
                best = dist[v]
                u = v
        if u == -1:
            break
        done[u] = True
        for v in range(n):
            w = matrix[u][v]
            if w > 0 and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return str(dist[dst]) if dist[dst] != INF else "-1"
