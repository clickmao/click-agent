"""vm 子命令: 栈式虚拟机解释器。

solve(text) -> str
  text: 完整 stdin 文本; 第一行整数 k, 随后 k 行每行一条指令。
  返回: 按 PRINT 顺序逐行输出的整数 (末尾不带换行); 出错返回 "ERR"。

指令集:
  PUSH n / POP / ADD / SUB / MUL / DUP / SWAP / PRINT / JNZ a / HALT
  a = 栈顶, b = 次顶; ADD->b+a, SUB->b-a, MUL->b*a (弹出这两者, 压入结果)。
错误: 栈空弹栈 / 操作数不足 / 跳转越界 / 未在 10000 步内 HALT / 越过最后一条指令
      -> 只输出一行 ERR。
"""
import sys

ERR = "ERR"
STEP_LIMIT = 10000


def _parse(text):
    # 保留原始行; 用 split('\n') 以便把末尾空行(可能是最后一条指令后的换行)区分开
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return None
    first = lines[0].strip()
    if not first:
        return None
    try:
        k = int(first)
    except ValueError:
        return None
    if len(lines) - 1 != k:
        return None
    prog = []
    for raw in lines[1:]:
        parts = raw.split()
        if not parts:
            return None
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                return None
            try:
                n = int(parts[1])
            except ValueError:
                return None
            prog.append(("PUSH", n))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return None
            prog.append((op, None))
        elif op == "JNZ":
            if len(parts) != 2:
                return None
            try:
                a = int(parts[1])
            except ValueError:
                return None
            prog.append(("JNZ", a))
        else:
            return None
    return prog


def run(prog):
    n = len(prog)
    stack = []
    out = []
    ip = 0
    steps = 0
    seen = set()
    while True:
        key = (ip, tuple(stack))
        if key in seen:
            # 状态环 => 必然步数无界, 等价于超出 10000 步限制
            return ERR
        seen.add(key)
        if steps >= STEP_LIMIT:
            return ERR
        steps += 1
        if ip < 0 or ip >= n:
            return ERR
        op, arg = prog[ip]
        if op == "HALT":
            return "\n".join(str(v) for v in out)
        if op == "PUSH":
            stack.append(arg)
            ip += 1
        elif op == "POP":
            if not stack:
                return ERR
            stack.pop()
            ip += 1
        elif op == "DUP":
            if not stack:
                return ERR
            stack.append(stack[-1])
            ip += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return ERR
            stack[-1], stack[-2] = stack[-2], stack[-1]
            ip += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                return ERR
            a = stack.pop()  # 栈顶
            b = stack.pop()  # 次顶
            if op == "ADD":
                stack.append(b + a)
            elif op == "SUB":
                stack.append(b - a)
            else:
                stack.append(b * a)
            ip += 1
        elif op == "PRINT":
            if not stack:
                return ERR
            out.append(stack.pop())
            ip += 1
        elif op == "JNZ":
            if not stack:
                return ERR
            v = stack.pop()
            if v != 0:
                if arg < 0 or arg >= n:
                    return ERR
                ip = arg
            else:
                ip += 1
        else:
            return ERR


def solve(text):
    prog = _parse(text)
    if prog is None:
        return ERR
    return run(prog)


if __name__ == "__main__":
    sys.stdout.write(solve(sys.stdin.read()))
