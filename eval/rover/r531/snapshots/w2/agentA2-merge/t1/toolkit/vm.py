"""VM subcommand: simple stack machine interpreter.

solve(text) -> str : text is full stdin, return value is stdout (no trailing newline).
"""

LIMIT = 10000


class _Err(Exception):
    pass


def solve(text: str) -> str:
    lines = text.split("\n")
    # strip trailing empty line artifacts (e.g. trailing newline)
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return "ERR"
    try:
        k = int(lines[0].strip())
    except Exception:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    body = lines[1:]
    if len(body) < k:
        return "ERR"
    prog = []
    for i in range(k):
        prog.append(body[i].strip())
    # parse instructions
    instrs = []
    for line in prog:
        parts = line.split()
        if not parts:
            return "ERR"
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                return "ERR"
            try:
                n = int(parts[1])
            except Exception:
                return "ERR"
            instrs.append(("PUSH", n))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return "ERR"
            instrs.append((op,))
        elif op == "JNZ":
            if len(parts) != 2:
                return "ERR"
            try:
                a = int(parts[1])
            except Exception:
                return "ERR"
            instrs.append(("JNZ", a))
        else:
            return "ERR"

    stack = []
    out = []
    pc = 0
    steps = 0
    try:
        while True:
            steps += 1
            if steps > LIMIT:
                raise _Err()
            if pc < 0 or pc >= len(instrs):
                raise _Err()
            ins = instrs[pc]
            op = ins[0]
            if op == "PUSH":
                stack.append(ins[1])
                pc += 1
            elif op == "POP":
                if not stack:
                    raise _Err()
                stack.pop()
                pc += 1
            elif op == "ADD":
                if len(stack) < 2:
                    raise _Err()
                a = stack.pop()
                b = stack.pop()
                stack.append(b + a)
                pc += 1
            elif op == "SUB":
                if len(stack) < 2:
                    raise _Err()
                a = stack.pop()
                b = stack.pop()
                stack.append(b - a)
                pc += 1
            elif op == "MUL":
                if len(stack) < 2:
                    raise _Err()
                a = stack.pop()
                b = stack.pop()
                stack.append(b * a)
                pc += 1
            elif op == "DUP":
                if not stack:
                    raise _Err()
                stack.append(stack[-1])
                pc += 1
            elif op == "SWAP":
                if len(stack) < 2:
                    raise _Err()
                stack[-1], stack[-2] = stack[-2], stack[-1]
                pc += 1
            elif op == "PRINT":
                if not stack:
                    raise _Err()
                out.append(str(stack.pop()))
                pc += 1
            elif op == "JNZ":
                if not stack:
                    raise _Err()
                v = stack.pop()
                a = ins[1]
                if a < 0 or a >= len(instrs):
                    raise _Err()
                if v != 0:
                    pc = a
                else:
                    pc += 1
            elif op == "HALT":
                raise StopIteration
            else:
                raise _Err()
    except StopIteration:
        pass
    except _Err:
        return "ERR"
    return "\n".join(out)
