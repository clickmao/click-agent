"""vm_run 子命令: 执行给定指令序列, 按 PRINT 顺序逐行输出; 任何错误只输出 ERR。"""

_OPS0 = ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT")


def _is_digit(ch):
    o = ord(ch)
    return 48 <= o <= 57


def _parse_int(s):
    """解析十进制整数 (允许前导符号), 非法返回 None。"""
    s = s.strip()
    if not s:
        return None
    i = 0
    neg = False
    if s[0] == "-":
        neg = True
        i = 1
    elif s[0] == "+":
        i = 1
    if i >= len(s):
        return None
    val = 0
    while i < len(s):
        ch = s[i]
        if not _is_digit(ch):
            return None
        val = val * 10 + (ord(ch) - 48)
        i += 1
    return -val if neg else val


def _int_str(value):
    neg = value < 0
    if neg:
        value = -value
    digits = []
    while value > 0:
        digits.append(chr(48 + value % 10))
        value = value // 10
    if not digits:
        digits.append("0")
    if neg:
        digits.append("-")
    digits.reverse()
    return "".join(digits)


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return "ERR"
    k = _parse_int(lines[0])
    if k is None:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    if len(lines) - 1 != k:
        return "ERR"

    program = []
    for raw in lines[1:]:
        parts = raw.split()
        if not parts:
            return "ERR"
        op = parts[0]
        args = parts[1:]
        if op == "PUSH":
            if len(args) != 1:
                return "ERR"
            v = _parse_int(args[0])
            if v is None:
                return "ERR"
            program.append((op, v))
        elif op in _OPS0:
            if args:
                return "ERR"
            program.append((op,))
        elif op == "JNZ":
            if len(args) != 1:
                return "ERR"
            a = _parse_int(args[0])
            if a is None:
                return "ERR"
            program.append((op, a))
        else:
            return "ERR"

    total = len(program)
    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if steps >= 10000:
            return "ERR"
        if pc < 0 or pc >= total:
            return "ERR"
        steps += 1
        instr = program[pc]
        op = instr[0]
        if op == "PUSH":
            stack.append(instr[1])
            pc += 1
        elif op == "POP":
            if not stack:
                return "ERR"
            stack.pop()
            pc += 1
        elif op == "ADD" or op == "SUB" or op == "MUL":
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if op == "ADD":
                stack.append(b + a)
            elif op == "SUB":
                stack.append(b - a)
            else:
                stack.append(b * a)
            pc += 1
        elif op == "DUP":
            if not stack:
                return "ERR"
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return "ERR"
            top = stack[-1]
            stack[-1] = stack[-2]
            stack[-2] = top
            pc += 1
        elif op == "PRINT":
            if not stack:
                return "ERR"
            out.append(_int_str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                return "ERR"
            v = stack.pop()
            if v != 0:
                target = instr[1]
                if target < 0 or target >= total:
                    return "ERR"
                pc = target
            else:
                pc += 1
        else:  # HALT
            return "\n".join(out)
