"""VM subcommand.

Spec (verbatim intent):
  stdin: first line integer k (1<=k<=64) = instruction count; then k lines,
  each an instruction (addresses start at 0). Instruction set:
    PUSH n / POP / ADD / SUB / MUL / DUP / SWAP / PRINT /
    JNZ a / HALT
  ADD/SUB/MUL: pop a = top, b = next, push b-a (etc).
  PRINT: pop top, output one line.
  JNZ a: pop top; if != 0 jump to address a else continue.
  Output: integers printed by PRINT, one per line.
  Errors (stack underflow / not enough operands / jump out of range /
  no HALT within 10000 steps / flow runs past last instruction):
  output exactly one line "ERR".
"""


class _Err(Exception):
    pass


def _run(prog, limit=10000):
    stack = []
    out = []
    pc = 0
    steps = 0
    n = len(prog)
    while True:
        steps += 1
        if steps > limit:
            raise _Err()
        if pc < 0 or pc >= n:
            raise _Err()
        op, arg = prog[pc]
        if op == "PUSH":
            stack.append(arg)
            pc += 1
        elif op == "POP":
            if not stack:
                raise _Err()
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                raise _Err()
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
            out.append(stack.pop())
            pc += 1
        elif op == "JNZ":
            if not stack:
                raise _Err()
            v = stack.pop()
            if arg is None or arg < 0 or arg >= n:
                raise _Err()
            if v != 0:
                pc = arg
            else:
                pc += 1
        elif op == "HALT":
            return out
        else:
            raise _Err()


def _parse(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise _Err()
    try:
        k = int(lines[0].strip())
    except ValueError:
        raise _Err()
    if k < 1 or k > 64:
        raise _Err()
    body = lines[1:]
    if len(body) != k:
        raise _Err()
    prog = []
    for raw in body:
        toks = raw.split()
        if not toks:
            raise _Err()
        op = toks[0]
        if op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(toks) != 1:
                raise _Err()
            prog.append((op, None))
        elif op == "PUSH":
            if len(toks) != 2:
                raise _Err()
            try:
                n = int(toks[1])
            except ValueError:
                raise _Err()
            prog.append(("PUSH", n))
        elif op == "JNZ":
            if len(toks) != 2:
                raise _Err()
            try:
                a = int(toks[1])
            except ValueError:
                raise _Err()
            prog.append(("JNZ", a))
        else:
            raise _Err()
    return prog


def solve(text):
    try:
        prog = _parse(text)
        out = _run(prog)
    except _Err:
        return "ERR"
    except RecursionError:
        return "ERR"
    return "\n".join(str(v) for v in out)
