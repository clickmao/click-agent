"""vm_run 子命令: 栈式虚拟机解释器.

solve(text) -> str : 入参为该子命令完整 stdin 文本, 返回应当写出的 stdout 文本(末尾不带换行).
"""

_ERR = "ERR"
_LIMIT = 10000


def _parse_instructions(lines):
    k = int(lines[0])
    prog = []
    for i in range(1, k + 1):
        parts = lines[i].split()
        if not parts:
            raise ValueError("empty instruction")
        op = parts[0]
        opnd = None
        if op in ("PUSH", "JNZ"):
            if len(parts) != 2:
                raise ValueError("bad operand count")
            opnd = int(parts[1])
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                raise ValueError("bad operand count")
        else:
            raise ValueError("unknown op")
        prog.append((op, opnd))
    return prog


def _run(prog):
    stack = []
    out = []
    pc = 0
    steps = 0
    n = len(prog)
    while True:
        if steps >= _LIMIT:
            return None
        steps += 1
        if pc < 0 or pc >= n:
            return None
        op, opnd = prog[pc]
        if op == "PUSH":
            stack.append(opnd)
            pc += 1
        elif op == "POP":
            if not stack:
                return None
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                return None
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
                return None
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                return None
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                return None
            v = stack.pop()
            if v != 0:
                if opnd < 0 or opnd >= n:
                    return None
                pc = opnd
            else:
                pc += 1
        else:  # HALT
            return out
    return None


def solve(text: str) -> str:
    lines = text.split("\n")
    # 去掉尾部空行产生的空串
    while lines and lines[-1] == "":
        lines.pop()
    for ln in lines:
        if ln.strip() == "":
            return _ERR
    try:
        prog = _parse_instructions(lines)
    except Exception:
        return _ERR
    res = _run(prog)
    if res is None:
        return _ERR
    return "\n".join(res)
