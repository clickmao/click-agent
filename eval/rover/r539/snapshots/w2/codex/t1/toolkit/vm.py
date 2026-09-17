"""Subcommand ``vm``: tiny stack virtual machine interpreter.

``solve`` takes the whole stdin text and returns the exact stdout text
(without a trailing newline).
"""

_ERR = "ERR"
_MAX_STEPS = 10000

_ZERO_ARG = {"POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"}
_ONE_ARG = {"PUSH", "JNZ"}


class _Err(Exception):
    """Any condition that must produce a single ``ERR`` line."""


def _parse(text):
    lines = text.split("\n")
    try:
        k = int(lines[0].strip())
    except (IndexError, ValueError):
        raise _Err
    if not 1 <= k <= 64:
        raise _Err
    body = lines[1:1 + k]
    if len(body) < k:
        raise _Err
    prog = []
    for line in body:
        parts = line.split()
        if not parts:
            raise _Err
        op = parts[0]
        if op in _ONE_ARG:
            if len(parts) != 2:
                raise _Err
            try:
                arg = int(parts[1])
            except ValueError:
                raise _Err
            prog.append((op, arg))
        elif op in _ZERO_ARG:
            if len(parts) != 1:
                raise _Err
            prog.append((op,))
        else:
            raise _Err
    return prog


def _run(prog):
    stack = []
    out = []
    pc = 0
    steps = 0
    n = len(prog)
    while True:
        if steps >= _MAX_STEPS:
            raise _Err
        if not 0 <= pc < n:
            raise _Err
        steps += 1
        ins = prog[pc]
        op = ins[0]
        if op == "PUSH":
            stack.append(ins[1])
            pc += 1
        elif op == "POP":
            if not stack:
                raise _Err
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                raise _Err
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
                raise _Err
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                raise _Err
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                raise _Err
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                raise _Err
            value = stack.pop()
            pc = ins[1] if value != 0 else pc + 1
        elif op == "HALT":
            return out
    raise _Err


def solve(text):
    try:
        program = _parse(text)
        out = _run(program)
    except _Err:
        return _ERR
    return "\n".join(out)
