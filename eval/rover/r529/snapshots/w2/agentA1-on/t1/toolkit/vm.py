"""vm_run 子命令: 小型栈式虚拟机。

solve(text) 接收完整 stdin 文本, 返回应写出的 stdout 文本 (末尾不带换行)。
出错 (栈空弹栈 / 操作数不足 / 跳转越界 / 未在 10000 步内 HALT / 执行流越过最后一条指令)
统一返回 "ERR"。
"""

MAX_STEPS = 10000


def _err():
    return "ERR"


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return _err()
    first = lines[0].strip()
    if not first:
        return _err()
    try:
        k = int(first)
    except ValueError:
        return _err()
    if k < 1 or k > 64:
        return _err()
    if len(lines) - 1 < k:
        return _err()

    prog = []
    for i in range(k):
        raw = lines[i + 1].strip()
        parts = raw.split()
        if not parts:
            return _err()
        op = parts[0]
        arg = None
        if op == "PUSH":
            if len(parts) != 2:
                return _err()
            try:
                arg = int(parts[1])
            except ValueError:
                return _err()
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return _err()
        elif op == "JNZ":
            if len(parts) != 2:
                return _err()
            try:
                arg = int(parts[1])
            except ValueError:
                return _err()
        else:
            return _err()
        prog.append((op, arg))

    stack = []
    out = []
    pc = 0
    steps = 0

    def pop():
        if not stack:
            raise ValueError
        return stack.pop()

    while True:
        if steps >= MAX_STEPS:
            return _err()
        if pc < 0 or pc >= k:
            return _err()
        steps += 1
        op, arg = prog[pc]
        if op == "PUSH":
            stack.append(arg)
            pc += 1
        elif op == "POP":
            try:
                pop()
            except ValueError:
                return _err()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            try:
                a = pop()
                b = pop()
            except ValueError:
                return _err()
            if op == "ADD":
                stack.append(b + a)
            elif op == "SUB":
                stack.append(b - a)
            else:
                stack.append(b * a)
            pc += 1
        elif op == "DUP":
            try:
                a = pop()
            except ValueError:
                return _err()
            stack.append(a)
            stack.append(a)
            pc += 1
        elif op == "SWAP":
            try:
                a = pop()
                b = pop()
            except ValueError:
                return _err()
            stack.append(a)
            stack.append(b)
            pc += 1
        elif op == "PRINT":
            try:
                a = pop()
            except ValueError:
                return _err()
            out.append(str(a))
            pc += 1
        elif op == "JNZ":
            try:
                a = pop()
            except ValueError:
                return _err()
            if a != 0:
                if arg < 0 or arg >= k:
                    return _err()
                pc = arg
            else:
                pc += 1
        elif op == "HALT":
            break
        else:
            return _err()

    return "\n".join(out)
