"""Stack virtual machine subcommand."""

MAX_STEPS = 10000


class _Fault(Exception):
    pass


def _parse(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise _Fault()
    try:
        k = int(lines[0].strip())
    except ValueError:
        raise _Fault()
    if k < 1 or k > 64:
        raise _Fault()
    body = lines[1:]
    if len(body) < k:
        raise _Fault()
    program = []
    for i in range(k):
        program.append(_parse_instr(body[i]))
    return program


def _parse_instr(line):
    parts = line.split()
    if not parts:
        raise _Fault()
    op = parts[0]
    if op == "PUSH":
        if len(parts) != 2:
            raise _Fault()
        try:
            return ("PUSH", int(parts[1]))
        except ValueError:
            raise _Fault()
    arity = {
        "POP": 0,
        "ADD": 0,
        "SUB": 0,
        "MUL": 0,
        "DUP": 0,
        "SWAP": 0,
        "PRINT": 0,
        "HALT": 0,
    }
    if op in arity:
        if len(parts) != 1:
            raise _Fault()
        return (op, None)
    if op == "JNZ":
        if len(parts) != 2:
            raise _Fault()
        try:
            return ("JNZ", int(parts[1]))
        except ValueError:
            raise _Fault()
    raise _Fault()


def _run(program):
    n = len(program)
    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if pc < 0 or pc >= n:
            raise _Fault()
        if steps >= MAX_STEPS:
            raise _Fault()
        op, arg = program[pc]
        steps += 1
        if op == "PUSH":
            stack.append(arg)
            pc += 1
        elif op == "POP":
            if not stack:
                raise _Fault()
            stack.pop()
            pc += 1
        elif op == "ADD" or op == "SUB" or op == "MUL":
            if len(stack) < 2:
                raise _Fault()
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
                raise _Fault()
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                raise _Fault()
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                raise _Fault()
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                raise _Fault()
            v = stack.pop()
            if v != 0:
                if arg < 0 or arg >= n:
                    raise _Fault()
                pc = arg
            else:
                pc += 1
        else:  # HALT
            return "\n".join(out)
    return "\n".join(out)


def solve(text: str) -> str:
    try:
        program = _parse(text)
        return _run(program)
    except _Fault:
        return "ERR"
    except RecursionError:
        return "ERR"
