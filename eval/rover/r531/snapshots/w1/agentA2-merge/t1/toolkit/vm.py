"""vm_run: stack machine interpreter.

Takes the full stdin text, returns the exact stdout text (no trailing newline).

Instruction set (addresses from 0):
  PUSH n / POP / ADD / SUB / MUL / DUP / SWAP / PRINT
  JNZ a   (pop stack top; if non-zero jump to address a, else continue)
  HALT    (end)

Binary ops: a = top, b = second -> push (b OP a).
Errors (stack underflow, too few operands, jump out of range, no HALT within
10000 steps, execution running past the last instruction) => single line "ERR".
"""

MAX_STEPS = 10000


class _VmError(Exception):
    pass


def _parse_int(tok):
    # integers optionally signed; no leading zeros requirement is not stated
    # for the VM, so keep it simple and strict on the sign+digits form.
    s = tok
    if s.startswith("-") or s.startswith("+"):
        body = s[1:]
    else:
        body = s
    if not body or not body.isdigit():
        raise _VmError()
    if s.startswith("+"):
        return int(body)
    return int(s)


def _parse_program(text):
    lines = text.split("\n")
    # tolerate a trailing "\r" and blank trailing lines caused by final newline
    if lines and lines[-1] == "":
        lines.pop()

    tokens = []
    for line in lines:
        tokens.append(line.strip().split())

    if not tokens or not tokens[0] or len(tokens[0]) != 1:
        raise _VmError()
    k = _parse_int(tokens[0][0])
    if k < 1 or k > 64:
        raise _VmError()
    if len(tokens) - 1 != k:
        raise _VmError()

    prog = []
    for raw in tokens[1:]:
        if not raw:
            raise _VmError()
        op = raw[0]
        if op == "PUSH":
            if len(raw) != 2:
                raise _VmError()
            prog.append(("PUSH", _parse_int(raw[1])))
        elif op in ("POP",):
            if len(raw) != 1:
                raise _VmError()
            prog.append(("POP",))
        elif op in ("ADD", "SUB", "MUL"):
            if len(raw) != 1:
                raise _VmError()
            prog.append((op,))
        elif op in ("DUP", "SWAP", "PRINT"):
            if len(raw) != 1:
                raise _VmError()
            prog.append((op,))
        elif op == "JNZ":
            if len(raw) != 2:
                raise _VmError()
            prog.append(("JNZ", _parse_int(raw[1])))
        elif op == "HALT":
            if len(raw) != 1:
                raise _VmError()
            prog.append(("HALT",))
        else:
            raise _VmError()
    return prog


def solve(text: str) -> str:
    try:
        prog = _parse_program(text)
    except _VmError:
        return "ERR"

    out = []
    stack = []
    pc = 0
    steps = 0

    def pop():
        if not stack:
            raise _VmError()
        return stack.pop()

    try:
        while True:
            if pc < 0 or pc >= len(prog):
                # ran past the last instruction without HALT
                raise _VmError()
            steps += 1
            if steps > MAX_STEPS:
                raise _VmError()
            inst = prog[pc]
            op = inst[0]
            if op == "PUSH":
                stack.append(inst[1])
                pc += 1
            elif op == "POP":
                pop()
                pc += 1
            elif op in ("ADD", "SUB", "MUL"):
                a = pop()
                b = pop()
                if op == "ADD":
                    stack.append(b + a)
                elif op == "SUB":
                    stack.append(b - a)
                else:
                    stack.append(b * a)
                pc += 1
            elif op == "DUP":
                v = pop()
                stack.append(v)
                stack.append(v)
                pc += 1
            elif op == "SWAP":
                a = pop()
                b = pop()
                stack.append(a)
                stack.append(b)
                pc += 1
            elif op == "PRINT":
                out.append(str(pop()))
                pc += 1
            elif op == "JNZ":
                v = pop()
                addr = inst[1]
                if v != 0:
                    if addr < 0 or addr >= len(prog):
                        raise _VmError()
                    pc = addr
                else:
                    pc += 1
            elif op == "HALT":
                break
            else:
                raise _VmError()
    except _VmError:
        return "ERR"

    return "\n".join(out)
