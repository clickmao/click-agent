"""两两公开用例的暂存输入文件与期望输出文件生成器（供本地验证）。"""
import pathlib

CASES = {
    'life1_in': '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n',
    'life2_in': '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n',
}

for name, content in CASES.items():
    pathlib.Path('cases', name).write_text(content)
