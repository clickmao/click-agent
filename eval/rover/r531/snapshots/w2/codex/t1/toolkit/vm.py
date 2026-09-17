"""VM subcommand: interpret a tiny stack machine."""

MAX_STEPS = 10000


class _VMError(Exception):
    pass


def _run(prog):
    stack = []
    pc = 0
    steps = 0
    out = []
    n = len(prog)

    while True:
        if pc < 0 or pc >= n:
            raise _VMError()
        steps += 1
        if steps > MAX_STEPS:
            raise _VMError()
        op, arg = prog[pc]
        pc += 1
        if op == 'PUSH':
            stack.append(arg)
        elif op == 'POP':
            if not stack:
                raise _VMError()
            stack.pop()
        elif op in ('ADD', 'SUB', 'MUL'):
            if len(stack) < 2:
                raise _VMError()
            a = stack.pop()
            b = stack.pop()
            if op == 'ADD':
                stack.append(b + a)
            elif op == 'SUB':
                stack.append(b - a)
            else:
                stack.append(b * a)
        elif op == 'DUP':
            if not stack:
                raise _VMError()
            stack.append(stack[-1])
        elif op == 'SWAP':
            if len(stack) < 2:
                raise _VMError()
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == 'PRINT':
            if not stack:
                raise _VMError()
            out.append(str(stack.pop()))
        elif op == 'JNZ':
            if not stack:
                raise _VMError()
            v = stack.pop()
            if v != 0:
                pc = arg
        elif op == 'HALT':
            return out
        else:
            raise _VMError()


def _parse(text):
    lines = text.split('\n')
    if not lines:
        raise _VMError()
    head = lines[0].strip()
    try:
        k = int(head)
    except ValueError:
        raise _VMError()
    if k < 1 or k > 64:
        raise _VMError()
    prog = []
    if len(lines) - 1 < k:
        raise _VMError()
    for i in range(1, k + 1):
        parts = lines[i].split()
        if not parts:
            raise _VMError()
        op = parts[0]
        if op in ('PUSH', 'JNZ'):
            if len(parts) != 2:
                raise _VMError()
            try:
                arg = int(parts[1])
            except ValueError:
                raise _VMError()
            prog.append((op, arg))
        elif op in ('POP', 'ADD', 'SUB', 'MUL', 'DUP', 'SWAP', 'PRINT', 'HALT'):
            if len(parts) != 1:
                raise _VMError()
            prog.append((op, None))
        else:
            raise _VMError()
    return prog


def solve(text: str) -> str:
    try:
        prog = _parse(text)
    except _VMError:
        return 'ERR'
    try:
        out = _run(prog)
    except _VMError:
        return 'ERR'
    return '\n'.join(out)
