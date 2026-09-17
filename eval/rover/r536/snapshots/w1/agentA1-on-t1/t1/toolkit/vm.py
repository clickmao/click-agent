"""vm_run subcommand: a tiny stack machine interpreter.

Input: first line integer k (1<=k<=64), then k instruction lines (addresses from 0).
Instruction set:
  PUSH n  push integer n
  POP     pop and discard
  ADD/SUB/MUL  pop a=top, b=second, push b-a etc. (ADD: b+a, SUB: b-a, MUL: b*a)
  DUP     duplicate top
  SWAP    swap top two
  PRINT   pop top and output one line
  JNZ a   pop top; if non-zero jump to address a, else continue
  HALT    stop
Output: the popped values from each PRINT in order, one per line.
Errors (empty-stack pop, insufficient operands, out-of-range jump, no HALT within
10000 steps, or execution past the last instruction) -> a single line "ERR".
"""

_STEP_LIMIT = 10000


class _VmError(Exception):
    pass


def _parse(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise _VmError()
    try:
        k = int(lines[0].strip())
    except ValueError:
        raise _VmError()
    if k < 1 or k > 64:
        raise _VmError()
    if len(lines) - 1 != k:
        raise _VmError()
    prog = []
    for raw in lines[1:]:
        parts = raw.split()
        if not parts:
            raise _VmError()
        op = parts[0]
        if op in ("PUSH", "JNZ"):
            if len(parts) != 2:
                raise _VmError()
            try:
                arg = int(parts[1])
            except ValueError:
                raise _VmError()
            prog.append((op, arg))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                raise _VmError()
            prog.append((op, None))
        else:
            raise _VmError()
    return prog


def solve(text: str) -> str:
    try:
        prog = _parse(text)
        stack = []
        out = []
        pc = 0
        steps = 0
        n = len(prog)
        while True:
            if steps >= _STEP_LIMIT:
                raise _VmError()
            if pc < 0 or pc >= n:
                raise _VmError()
            op, arg = prog[pc]
            steps += 1
            if op == "PUSH":
                stack.append(arg)
            elif op == "POP":
                if not stack:
                    raise _VmError()
                stack.pop()
            elif op == "ADD":
                if len(stack) < 2:
                    raise _VmError()
                a = stack.pop()
                b = stack.pop()
                stack.append(b + a)
            elif op == "SUB":
                if len(stack) < 2:
                    raise _VmError()
                a = stack.pop()
                b = stack.pop()
                stack.append(b - a)
            elif op == "MUL":
                if len(stack) < 2:
                    raise _VmError()
                a = stack.pop()
                b = stack.pop()
                stack.append(b * a)
            elif op == "DUP":
                if not stack:
                    raise _VmError()
                stack.append(stack[-1])
            elif op == "SWAP":
                if len(stack) < 2:
                    raise _VmError()
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif op == "PRINT":
                if not stack:
                    raise _VmError()
                out.append(str(stack.pop()))
            elif op == "JNZ":
                if not stack:
                    raise _VmError()
                v = stack.pop()
                if v != 0:
                    if arg < 0 or arg >= n:
                        raise _VmError()
                    pc = arg
                    continue
            elif op == "HALT":
                break
            pc += 1
        return "\n".join(out)
    except _VmError:
        return "ERR"
