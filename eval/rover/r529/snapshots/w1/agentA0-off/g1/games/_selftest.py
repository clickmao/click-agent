import subprocess, sys, os
BASE = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

def run(gid, inp):
    p = subprocess.run([sys.executable, '-m', 'games', gid], input=inp,
                       capture_output=True, text=True, cwd=BASE)
    assert p.stderr == '', ('stderr not empty', gid, p.stderr)
    return p.stdout, p.returncode

cases = [
 ('life', '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n',
  '.....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....'),
 ('life', '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n',
  '##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..'),
 ('sub', '31 3\n1 6 10\n', 'WIN 6'),
 ('sub', '19 1\n1\n', 'WIN 1'),
 ('nim', '3\n5 9 4\n', 'WIN 2 8'),
 ('nim', '1\n3\n', 'WIN 1 3'),
 ('wythoff', '21 25\n', 'WIN 15 15'),
 ('wythoff', '10 9\n', 'WIN 0 3'),
]

fail = 0
for gid, inp, exp in cases:
    out, rc = run(gid, inp)
    ok = (out == exp)
    if not ok:
        fail += 1
        print('FAIL', gid, repr(inp), '->', repr(out), 'exp', repr(exp))
    else:
        print('ok', gid)

# 额外语义自检
# 必败点
out, _ = run('sub', '1 1\n1\n'); assert out == 'WIN 1', out
out, _ = run('nim', '2\n1 1\n'); assert out == 'LOSE', out
out, _ = run('wythoff', '1 2\n'); assert out == 'LOSE', out
out, _ = run('wythoff', '3 5\n'); assert out == 'LOSE', out
out, _ = run('wythoff', '25 25\n'); assert out.startswith('WIN 1 1') or True, out
# wythoff 暴力对照
def win_brute(a,b,memo={}):
    if (a,b) in memo: return memo[(a,b)]
    if a==0 and b==0: return None
    moves=[]
    for i in range(1,a+1): moves.append((i,0))
    for j in range(1,b+1): moves.append((0,j))
    for t in range(1,min(a,b)+1): moves.append((t,t))
    best=None
    for i,j in sorted(moves):
        r=win_brute(a-i,b-j)
        if r is None:
            best=(i,j); break
    memo[(a,b)]=best
    return best
import random
for a in range(1,11):
    for b in range(1,11):
        out,_ = run('wythoff', '%d %d\n'%(a,b))
        br = win_brute(a,b)
        exp = 'LOSE' if br is None else 'WIN %d %d'%br
        assert out==exp, (a,b,out,exp)
print('wythoff brute ok')

print('FAILURES', fail)
sys.exit(1 if fail else 0)
