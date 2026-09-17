"""vm 子命令: 栈式虚拟机解释器。

solve(text) -> str: 入参为完整 stdin 文本, 返回应写出的 stdout (末尾不带换行)。
出错只返回 "ERR"。
"""


def _parse_int(tok):
    # 指令参数均为十进制整数 (允许负号)
    if not tok:
        return None
    s = tok[1:] if tok[0] in "+-" else tok
    if not s or not s.isdigit():
        return None
    return int(tok)


def solve(text):
    lines = text.split("\n")
    if not lines:
        return "ERR"
    k = _parse_int(lines[0].strip())
    if k is None or k < 1 or k > 64:
        return "ERR"
    # 需要恰好 k 条指令行
    body = lines[1:]
    # 去掉可能存在的末尾空行造成的多余元素判断: 取前 k 行, 且不能少于 k 行
    if len(body) < k:
        return "ERR"
    program = []
    for i in range(k):
        program.append(body[i].strip())
    out = []
    stack = []
    steps = 0
    pc = 0
    MAX_STEPS = 10000
    while True:
        if steps >= MAX_STEPS:
            return "ERR"
        if pc < 0 or pc >= k:
            # 执行流越过最后一条指令 / 跳转越界
            return "ERR"
        steps += 1
        line = program[pc]
        parts = line.split()
        if not parts:
            return "ERR"
        op = parts[0]
        args = parts[1:]
        if op == "PUSH":
            if len(args) != 1:
                return "ERR"
            n = _parse_int(args[0])
            if n is None:
                return "ERR"
            stack.append(n)
            pc += 1
        elif op == "POP":
            if args:
                return "ERR"
            if not stack:
                return "ERR"
            stack.pop()
            pc += 1
        elif op == "DUP":
            if args:
                return "ERR"
            if not stack:
                return "ERR"
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if args:
                return "ERR"
            if len(stack) < 2:
                return "ERR"
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if args:
                return "ERR"
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if op == "ADD":
                r = b + a
            elif op == "SUB":
                r = b - a
            else:
                r = b * a
            stack.append(r)
            pc += 1
        elif op == "PRINT":
            if args:
                return "ERR"
            if not stack:
                return "ERR"
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if len(args) != 1:
                return "ERR"
            a = _parse_int(args[0])
            if a is None:
                return "ERR"
            if not stack:
                return "ERR"
            v = stack.pop()
            if v != 0:
                if a < 0 or a >= k:
                    return "ERR"
                pc = a
            else:
                pc += 1
        elif op == "HALT":
            if args:
                return "ERR"
            return "\n".join(out)
        else:
            return "ERR"
