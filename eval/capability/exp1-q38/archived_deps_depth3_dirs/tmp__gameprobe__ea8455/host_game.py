#!/usr/bin/env python3
"""贪吃蛇 (终端文本渲染, 逻辑/渲染分离, 支持 --selftest 无头自测)。

用法:
  python3 game.py            # 交互游玩 (WASD/方向键, q 退出)
  python3 game.py --selftest # 无头自测 (打印 PASS/FAIL, 退出码 0/1)
"""
import os
import random
import sys

W, H = 20, 12
UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


class Snake:
    """纯逻辑: 无 IO / 无渲染 / 可确定性测试。"""

    def __init__(self, w=W, h=H, rng=None):
        self.w, self.h = w, h
        self.rng = rng or random.Random(0)
        self.reset()

    def reset(self):
        cx, cy = self.w // 2, self.h // 2
        self.body = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]  # 头在前
        self.direction = RIGHT
        self.pending = RIGHT
        self.score = 0
        self.dead = False
        self.food = self._spawn()

    def _spawn(self):
        free = [(x, y) for x in range(self.w) for y in range(self.h) if (x, y) not in self.body]
        return self.rng.choice(free) if free else None

    def turn(self, d):
        """拒绝 180° 反向 (经典规则)。"""
        if (d[0] == -self.direction[0] and d[1] == -self.direction[1]):
            return
        self.pending = d

    def step(self):
        if self.dead:
            return
        self.direction = self.pending
        hx, hy = self.body[0]
        nx, ny = hx + self.direction[0], hy + self.direction[1]
        if not (0 <= nx < self.w and 0 <= ny < self.h):      # 撞墙
            self.dead = True
            return
        if (nx, ny) in self.body[:-1]:                        # 撞自己 (尾巴会移走)
            self.dead = True
            return
        self.body.insert(0, (nx, ny))
        if (nx, ny) == self.food:
            self.score += 1
            self.food = self._spawn()
        else:
            self.body.pop()

    def render(self):
        rows = []
        for y in range(self.h):
            row = []
            for x in range(self.w):
                if (x, y) == self.body[0]:
                    row.append("@")
                elif (x, y) in self.body:
                    row.append("o")
                elif (x, y) == self.food:
                    row.append("*")
                else:
                    row.append(".")
            rows.append("".join(row))
        return "\n".join(rows) + f"\nscore={self.score} dead={self.dead}"


def selftest():
    """无头自测: 吃食物增长 / 撞墙死 / 撞自己死 / 反向被拒。"""
    fails = []

    g = Snake(rng=random.Random(1))
    g.food = (g.body[0][0] + 1, g.body[0][1])
    n0 = len(g.body)
    g.step()
    if len(g.body) != n0 + 1 or g.score != 1:
        fails.append(f"eat: len={len(g.body)} score={g.score}")

    g = Snake()
    g.pending = g.direction = RIGHT
    for _ in range(W):
        g.step()
    if not g.dead:
        fails.append("wall: 未判定撞墙")

    g = Snake(rng=random.Random(2))
    g.body = [(5, 5), (6, 5), (6, 6), (5, 6), (4, 6)]
    g.direction = RIGHT
    g.turn(LEFT)
    if g.pending != RIGHT:
        fails.append("turn: 180° 反向应被拒")

    g = Snake(rng=random.Random(3))
    g.body = [(5, 5), (5, 6), (6, 6), (6, 5)]
    for d, _ in ((DOWN, 1), (LEFT, 1), (UP, 1)):
        g.turn(d)
        g.step()
    if not g.dead:
        fails.append("self: 未判定撞自己")

    print("PASS" if not fails else "FAIL: " + "; ".join(fails))
    return 0 if not fails else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    import termios
    import tty

    def read_key():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                return {"[A": UP, "[B": DOWN, "[C": RIGHT, "[D": LEFT}.get(seq)
            return {"w": UP, "s": DOWN, "a": LEFT, "d": RIGHT}.get(ch.lower()) or ("q" if ch == "q" else None)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    g = Snake(rng=random.Random())
    while not g.dead:
        os.system("clear")
        print(g.render() + "\nWASD 移动, q 退出")
        k = read_key()
        if k == "q":
            break
        if k:
            g.turn(k)
        g.step()
    print(("游戏结束! " if g.dead else "已退出. ") + f"得分 {g.score}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
