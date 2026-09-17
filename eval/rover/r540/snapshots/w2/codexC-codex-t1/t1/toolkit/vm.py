"""Multi-file toolkit: `vm` subcommand.

`solve` reads the whole stdin text for the `vm_run` family and returns the
exact stdout text (no trailing newline).
"""


class _VMError(Exception):
    pass


def _parse(text):
    lines = text.split("\n")
    # Tolerate a single trailing newline (or CRLF) at end of input.
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise _VMError()

    header = lines[0].strip()
    try:
        k = int(header)
    except ValueError:
        raise _VMError()
    if k < 1 or k > 64:
        raise _VMError()

    body = lines[1:]
    if len(body) != k:
        raise _VMError()

    program = []
    for raw in body:
        program.append(_parse_instr(raw))
    return program


def _parse_instr(raw):
    line = raw.strip()
    if line == "":
        raise _VMError()
    parts = line.split()
    op = parts[0].upper()
    rest = parts[1:]

    if op in ("PUSH", "JNZ"):
        if len(rest) != 1:
            raise _VMError()
        try:
            value = int(rest[0])
        except ValueError:
            raise _VMError()
        return (op, value)

    if op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
        if rest:
            raise _VMError()
        return (op,)

    raise _VMError()


def _run(program):
    out = []
    stack = []
    n = len(program)
    ip = 0
    steps = 0

    while True:
        if ip < 0 or ip >= n:
            raise _VMError()
        steps += 1
        if steps > 10000:
            raise _VMError()

        op, *arg = program[ip]

        if op == "PUSH":
            stack.append(arg[0])
            ip += 1
        elif op == "POP":
            if not stack:
                raise _VMError()
            stack.pop()
            ip += 1
        elif op == "ADD":
            if len(stack) < 2:
                raise _VMError()
            a = stack.pop()
            b = stack.pop()
            stack.append(b + a)
            ip += 1
        elif op == "SUB":
            if len(stack) < 2:
                raise _VMError()
            a = stack.pop()
            b = stack.pop()
            stack.append(b - a)
            ip += 1
        elif op == "MUL":
            if len(stack) < 2:
                raise _VMError()
            a = stack.pop()
            b = stack.pop()
            stack.append(b * a)
            ip += 1
        elif op == "DUP":
            if not stack:
                raise _VMError()
            stack.append(stack[-1])
            ip += 1
        elif op == "SWAP":
            if len(stack) < 2:
                raise _VMError()
            stack[-1], stack[-2] = stack[-2], stack[-1]
            ip += 1
        elif op == "PRINT":
            if not stack:
                raise _VMError()
            out.append(str(stack.pop()))
            ip += 1
        elif op == "JNZ":
            if not stack:
                raise _VMError()
            target = arg[0]
            if target < 0 or target >= n:
                raise _VMError()
            value = stack.pop()
            if value != 0:
                ip = target
            else:
                ip += 1
        elif op == "HALT":
            return out
        else:
            raise _VMError()


def solve(text: str) -> str:
    try:
        program = _parse(text)
        out = _run(program)
    except _VMError:
        return "ERR"
    except RecursionError:
        return "ERR"
    return "\n".join(out)
