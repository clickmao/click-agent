# mathkit — pure-function math toolkit (Python 3, standard library only)

Each module exports one function per op with signature ``op(args: dict) -> str``
returning the exact stdout text (no trailing newline):

| op        | module         | meaning                                                  |
|-----------|----------------|----------------------------------------------------------|
| `qr_count`| `modular.py`   | #solutions of x^2 == a (mod m), 0 <= x < m                |
| `choose`  | `modular.py`   | C(n, k) mod prime `mod`                                   |
| `det`     | `linear.py`    | integer determinant mod prime `mod` (Bareiss, exact ints) |
| `shortest`| `graphs.py`    | Dijkstra length on symmetric weighted adjacency; -1 if NA |
| `expect`  | `prob.py`      | E[#red] = draw*red/(red+blue) as reduced `p/q`            |

## Usage

```
echo '{"a": 11, "m": 16}'        | python3 -m mathkit qr_count    # -> 0
echo '{"n": 18, "k": 7, "mod":97}' | python3 -m mathkit choose   # -> 8
echo '{"matrix": [[-2,0],[-1,-6]], "mod": 101}' | python3 -m mathkit det  # -> 12
```

The CLI reads one JSON object from stdin and writes exactly one line (the
answer, **no trailing newline**) to stdout; nothing is ever written to stderr.

## Self-check

```
python3 -m mathkit.selftest
```

Exit 0 = all PASS, non-zero = number of failures printed.  It drives every op
through the real CLI and cross-checks against independent brute-force
implementations (exhaustive modular scan, permutation determinant,
Floyd–Warshall, exact `Fraction`), plus negative controls.
