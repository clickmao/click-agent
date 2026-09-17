"""Subcommand ``vm_run``: a tiny stack virtual machine with jumps."""

MAX_STEPS = 10000


class _VMError(Exception):
    """Raised internally when the machine faults; converted to ``ERR``."""


def _solve(lines):
    if not lines:
        return "ERR"
    try:
        count = int(lines[0].strip())
    except ValueError:
        return "ERR"
    if count < 1 or count > 64:
        return "ERR"
    if len(lines) < 1 + count:
        return "ERR"

    program = []
    for raw in lines[1:1 + count]:
        parts = raw.split()
        if not parts:
            return "ERR"
        program.append(parts)

    stack = []
    out = []
    pc = 0
    steps = 0

    try:
        while True:
            if pc < 0 or pc >= count:
                return "ERR"
            steps += 1
            if steps > MAX_STEPS:
                return "ERR"

            parts = program[pc]
            op = parts[0]
            args = parts[1:]

            if op == "PUSH":
                if len(args) != 1:
                    return "ERR"
                stack.append(int(args[0]))
                pc += 1
            elif op == "POP":
                if args:
                    return "ERR"
                stack.pop()
                pc += 1
            elif op == "ADD":
                if args:
                    return "ERR"
                a = stack.pop()
                b = stack.pop()
                stack.append(b + a)
                pc += 1
            elif op == "SUB":
                if args:
                    return "ERR"
                a = stack.pop()
                b = stack.pop()
                stack.append(b - a)
                pc += 1
            elif op == "MUL":
                if args:
                    return "ERR"
                a = stack.pop()
                b = stack.pop()
                stack.append(b * a)
                pc += 1
            elif op == "DUP":
                if args:
                    return "ERR"
                stack.append(stack[-1])
                pc += 1
            elif op == "SWAP":
                if args:
                    return "ERR"
                top = stack.pop()
                second = stack.pop()
                stack.append(top)
                stack.append(second)
                pc += 1
            elif op == "PRINT":
                if args:
                    return "ERR"
                out.append(str(stack.pop()))
                pc += 1
            elif op == "JNZ":
                if len(args) != 1:
                    return "ERR"
                target = int(args[0])
                value = stack.pop()
                if target < 0 or target >= count:
                    return "ERR"
                if value != 0:
                    pc = target
                else:
                    pc += 1
            elif op == "HALT":
                if args:
                    return "ERR"
                return "\n".join(out)
            else:
                return "ERR"
    except _VMError:
        return "ERR"
    except (IndexError, ValueError):
        return "ERR"


def solve(text):
    """Evaluate the program encoded in ``text`` and return the output text."""
    if text == "":
        return "ERR"
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    return _solve(lines)
