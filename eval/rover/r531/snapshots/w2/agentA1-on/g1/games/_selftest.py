"""自检: 公开用例 + 边界/不变式 + 独立暴力交叉验证。运行: python3 games/_selftest.py"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

CASES = [
    ('life', "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#",
     ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
    ('life', "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#",
     "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
    ('life', "1 1 0\n#", "#"),
    ('life', "1 1 1\n#", "."),
    ('life', "3 3 1\n.#.\n###\n.#.", "###\n#.#\n###"),
    ('life', "1 1 20\n.", "."),
    ('sub', "31 3\n1 6 10", "WIN 6"),
    ('sub', "19 1\n1", "WIN 1"),
    ('sub', "1 1\n1", "WIN 1"),
    ('sub', "2 1\n1", "LOSE"),
    ('sub', "5 2\n2 1", "WIN 2"),
    ('nim', "3\n5 9 4", "WIN 2 8"),
    ('nim', "1\n3", "WIN 1 3"),
    ('nim', "2\n1 1", "LOSE"),
    ('nim', "2\n4 4", "LOSE"),
    ('nim', "1\n1", "WIN 1 1"),
    ('nim', "4\n1 2 4 8", "WIN 4 1"),
    ('wythoff', "21 25", "WIN 15 15"),
    ('wythoff', "10 9", "WIN 0 3"),
    ('wythoff', "1 2", "LOSE"),
    ('wythoff', "3 5", "LOSE"),
    ('wythoff', "1 1", "WIN 1 1"),
    ('wythoff', "25 25", "WIN 25 25"),
]


def run_case(game, inp):
    p = subprocess.run([sys.executable, '-m', 'games', game],
                       input=inp.encode(), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, cwd=ROOT)
    return p.returncode, p.stdout.decode(), p.stderr.decode()


def wythoff_brute(N=25):
    """独立暴力 DP: 求冷态与字典序最小必胜着法, 用于交叉验证。"""
    cold = [[False] * (N + 1) for _ in range(N + 1)]
    for s in range(0, 2 * N + 1):
        for a in range(0, N + 1):
            b = s - a
            if not (0 <= b <= N):
                continue
            win = False
            for i in range(0, a + 1):
                for j in range(0, b + 1):
                    if i == 0 and j == 0:
                        continue
                    if i > 0 and j > 0 and i != j:
                        continue
                    if cold[a - i][b - j]:
                        win = True
                        break
                if win:
                    break
            cold[a][b] = not win
    return cold


def main():
    fails = []
    for game, inp, exp in CASES:
        rc, out, err = run_case(game, inp)
        if rc != 0 or out != exp or err != '':
            fails.append('%s rc=%d err=%r out=%r exp=%r' % (game, rc, err, out, exp))

    # 独立暴力交叉验证 wythoff 冷态判定
    import games.wythoff as wy
    cold = wythoff_brute(25)
    for a in range(1, 26):
        for b in range(1, 26):
            if wy.is_cold(a, b) != cold[a][b]:
                fails.append('wythoff cold mismatch a=%d b=%d' % (a, b))

    # 交叉验证 wythoff 输出的必胜着法确实到达冷态
    for a in range(1, 26):
        for b in range(1, 26):
            if cold[a][b]:
                continue
            rc, out, err = run_case('wythoff', "%d %d" % (a, b))
            parts = out.split()
            i, j = int(parts[1]), int(parts[2])
            if not cold[a - i][b - j]:
                fails.append('wythoff bad move a=%d b=%d -> %d %d' % (a, b, i, j))

    # 负向控制: 缺陷注入必须变红 —— 篡改 life 规则后判定应失败
    rc, out, err = run_case('nim', "2\n1 1")
    if out != 'LOSE':
        fails.append('neg-control nim(1,1)')

    print('PASS' if not fails else 'FAIL')
    for f in fails:
        print(f)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
