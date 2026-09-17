"""Tiny stack virtual machine.

``solve(text)`` parses a program from text and runs it, returning the PRINT
output joined by newlines (no trailing newline), or the single line ``ERR``
on any parse or runtime error.
"""

HALT = "HALT"
PUSH = "PUSH"
POP = "POP"
ADD = "ADD"
SUB = "SUB"
MUL = "MUL"
DUP = "DUP"
SWAP = "SWAP"
PRINT = "PRINT"
JNZ = "JNZ"

STEP_LIMIT = 10000
SIMPLE_OPS = (POP, ADD, SUB, MUL, DUP, SWAP, PRINT, HALT)


def _parse(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise ValueError("empty input")
    try:
        count = int(lines[0].strip())
    except ValueError:
        raise ValueError("bad instruction count")
    if count < 1 or count > 64:
        raise ValueError("instruction count out of range")

    body = lines[1:]
    if len(body) != count:
        raise ValueError("instruction count mismatch")

    program = []
    for raw in body:
        parts = raw.split()
        if not parts:
            raise ValueError("empty instruction")
        op = parts[0]
        if op == PUSH or op == JNZ:
            if len(parts) != 2:
                raise ValueError("bad operand count")
            try:
                program.append((op, int(parts[1])))
            except ValueError:
                raise ValueError("bad operand")
        elif op in SIMPLE_OPS:
            if len(parts) != 1:
                raise ValueError("bad instruction arity")
            program.append((op, None))
        else:
            raise ValueError("unknown opcode")
    return program


def _run(program):
    size = len(program)
    pc = 0
    steps = 0
    stack = []
    out = []

    while True:
        steps += 1
        if steps > STEP_LIMIT:
            break
        if pc < 0 or pc >= size:
            break
        op, arg = program[pc]
        if op == HALT:
            return "\n".join(out)
        if op == PUSH:
            stack.append(arg)
            pc += 1
        elif op == POP:
            if not stack:
                break
            stack.pop()
            pc += 1
        elif op == DUP:
            if not stack:
                break
            stack.append(stack[-1])
            pc += 1
        elif op == SWAP:
            if len(stack) < 2:
                break
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == ADD or op == SUB or op == MUL:
            if len(stack) < 2:
                break
            top = stack.pop()
            below = stack.pop()
            if op == ADD:
                stack.append(below + top)
            elif op == SUB:
                stack.append(below - top)
            else:
                stack.append(below * top)
            pc += 1
        elif op == JNZ:
            if not stack:
                break
            value = stack.pop()
            if value != 0:
                if arg < 0 or arg >= size:
                    break
                pc = arg
            else:
                pc += 1
        elif op == PRINT:
            if not stack:
                break
            out.append(str(stack.pop()))
            pc += 1
        else:
            break
    return "ERR"


def solve(text):
    try:
        program = _parse(text)
    except ValueError:
        return "ERR"
    try:
        return _run(program)
    except Exception:
        return "ERR"
