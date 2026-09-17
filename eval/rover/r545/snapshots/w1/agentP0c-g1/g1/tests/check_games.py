import subprocess
import sys

CASES = [
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

def run_case(game, text):
    p = subprocess.run([sys.executable, '-m', 'games', game], input=text,
                       capture_output=True, text=True)
    return p

def main():
    ok = True
    for game, text, expected in CASES:
        p = run_case(game, text)
        got = p.stdout.rstrip('\n')
        if p.returncode != 0 or got != expected or p.stderr != '':
            ok = False
            print('FAIL', game, repr(got), 'expected', repr(expected),
                  'rc', p.returncode, 'stderr', repr(p.stderr))
    print('ALL_OK' if ok else 'SOME_FAIL')

if __name__ == '__main__':
    main()
