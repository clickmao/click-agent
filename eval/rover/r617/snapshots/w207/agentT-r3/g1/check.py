"""对四个公开用例做逐字节比对的自检脚本。"""

import subprocess

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


for game_id, inp, want in CASES:
    out = subprocess.run(['python3', '-m', 'games', game_id], input=inp,
                         capture_output=True, text=True)
    got = out.stdout
    print(game_id, got == want)
    if got != want:
        print('  want:', repr(want))
        print('  got :', repr(got))
        print('  err :', repr(out.stderr))
