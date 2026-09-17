"""vm_run subcommand: a tiny stack virtual machine.

solve(text) -> stdout text (no trailing newline).
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    # Allow a trailing newline / trailing empty line: first line is k.
    # Strip a single trailing empty segment caused by a final newline.
    if lines and lines[-1] == "":
        lines.pop()
    try:
        if not lines:
            return "ERR"
        k = int(lines[0].strip())
        if k < 1 or k > 64:
            return "ERR"
        prog = []
        for i in range(1, k + 1):
            if i >= len(lines):
                return "ERR"
            prog.append(lines[i].strip())
    except ValueError:
        return "ERR"

    def parse_int(s):
        s = s.strip()
        if s == "":
            raise ValueError
        body = s[1:] if s[0] in "+-" else s
        if not body.isdigit():
            raise ValueError
        return int(s)

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        steps += 1
        if steps > 10000:
            return "ERR"
        if pc < 0 or pc >= len(prog):
            return "ERR"
        parts = prog[pc].split()
        if not parts:
            return "ERR"
        op = parts[0]
        args = parts[1:]
        if op == "PUSH":
            if len(args) != 1:
                return "ERR"
            try:
                v = parse_int(args[0])
            except ValueError:
                return "ERR"
            stack.append(v)
            pc += 1
        elif op == "POP":
            if args or not stack:
                return "ERR"
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if args or len(stack) < 2:
                return "ERR"
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
            if args or not stack:
                return "ERR"
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if args or len(stack) < 2:
                return "ERR"
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if args or not stack:
                return "ERR"
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if len(args) != 1 or not stack:
                return "ERR"
            try:
                target = parse_int(args[0])
            except ValueError:
                return "ERR"
            v = stack.pop()
            if v != 0:
                if target < 0 or target >= len(prog):
                    return "ERR"
                pc = target
            else:
                pc += 1
        elif op == "HALT":
            if args:
                return "ERR"
            return "\n".join(out)
        else:
            return "ERR"
