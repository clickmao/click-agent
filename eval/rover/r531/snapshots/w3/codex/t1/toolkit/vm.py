"""A tiny stack virtual machine.

solve(text) interprets a program from stdin text and returns the program's
stdout text (without a trailing newline), or the single line "ERR".
"""

MAX_STEPS = 10000


def _err():
    return "ERR"


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return _err()
    try:
        k = int(lines[0].strip())
    except ValueError:
        return _err()
    if k < 1 or k > 64:
        return _err()
    if len(lines) < k + 1:
        return _err()

    program = []
    for i in range(1, k + 1):
        program.append(lines[i].strip().split())

    stack = []
    out = []
    pc = 0
    steps = 0

    def pop():
        if not stack:
            raise _StackError
        return stack.pop()

    while True:
        if pc < 0 or pc >= k:
            return _err()
        steps += 1
        if steps > MAX_STEPS:
            return _err()
        parts = program[pc]
        if not parts:
            return _err()
        op = parts[0]
        args = parts[1:]

        if op == "PUSH":
            if len(args) != 1:
                return _err()
            try:
                val = int(args[0])
            except ValueError:
                return _err()
            stack.append(val)
            pc += 1
        elif op == "POP":
            if args:
                return _err()
            try:
                pop()
            except _StackError:
                return _err()
            pc += 1
        elif op == "ADD":
            if args:
                return _err()
            try:
                a = pop()
                b = pop()
            except _StackError:
                return _err()
            stack.append(b + a)
            pc += 1
        elif op == "SUB":
            if args:
                return _err()
            try:
                a = pop()
                b = pop()
            except _StackError:
                return _err()
            stack.append(b - a)
            pc += 1
        elif op == "MUL":
            if args:
                return _err()
            try:
                a = pop()
                b = pop()
            except _StackError:
                return _err()
            stack.append(b * a)
            pc += 1
        elif op == "DUP":
            if args:
                return _err()
            if not stack:
                return _err()
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if args:
                return _err()
            if len(stack) < 2:
                return _err()
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if args:
                return _err()
            try:
                v = pop()
            except _StackError:
                return _err()
            out.append(str(v))
            pc += 1
        elif op == "JNZ":
            if len(args) != 1:
                return _err()
            try:
                a = int(args[0])
            except ValueError:
                return _err()
            try:
                v = pop()
            except _StackError:
                return _err()
            if a < 0 or a >= k:
                return _err()
            if v != 0:
                pc = a
            else:
                pc += 1
        elif op == "HALT":
            if args:
                return _err()
            return "\n".join(out)
        else:
            return _err()


class _StackError(Exception):
    pass
