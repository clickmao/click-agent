# -*- coding: utf-8 -*-
"""vm subcommand: a tiny stack machine interpreter.

solve(text) -> stdout text (no trailing newline).

Reads:
  line 1: integer k (1 <= k <= 64) = number of instructions
  next k lines: one instruction each (addresses start at 0)

Instruction set:
  PUSH n   push integer n
  POP      pop and discard
  ADD      pop a (top), b (next), push b + a
  SUB      pop a (top), b (next), push b - a
  MUL      pop a (top), b (next), push b * a
  DUP      duplicate top
  SWAP     swap top two
  PRINT    pop top and emit it as one line
  JNZ a    pop top; if non-zero jump to a else continue
  HALT     end

Errors (emit exactly one line "ERR"):
  pop on empty stack, insufficient operands, jump out of range,
  no HALT within 10000 steps, or execution runs past the last instruction.
"""

MAX_STEPS = 10000


class _Empty(Exception):
    pass


class _Under(Exception):
    pass


def _parse_int(tok):
    if not tok:
        raise ValueError("empty int")
    body = tok
    if body[0] == "-":
        body = body[1:]
    if not body or not body.isdigit():
        raise ValueError("bad int")
    return int(tok)


def _parse_instr(line):
    parts = line.split()
    if not parts:
        raise ValueError("empty instruction")
    op = parts[0].upper()
    if op == "PUSH":
        if len(parts) != 2:
            raise ValueError("PUSH arity")
        return ("PUSH", _parse_int(parts[1]))
    if op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
        if len(parts) != 1:
            raise ValueError("arity")
        return (op, None)
    if op == "JNZ":
        if len(parts) != 2:
            raise ValueError("JNZ arity")
        return ("JNZ", _parse_int(parts[1]))
    raise ValueError("unknown op " + parts[0])


def _run(prog):
    """Execute program; returns (status, out) with status True on normal HALT."""
    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if steps >= MAX_STEPS:
            return (False, out)
        if pc < 0 or pc >= len(prog):
            return (False, out)
        op, arg = prog[pc]
        steps += 1
        try:
            if op == "PUSH":
                stack.append(arg)
                pc += 1
            elif op == "POP":
                if not stack:
                    raise _Empty()
                stack.pop()
                pc += 1
            elif op == "DUP":
                if not stack:
                    raise _Empty()
                stack.append(stack[-1])
                pc += 1
            elif op == "SWAP":
                if len(stack) < 2:
                    raise _Under()
                stack[-1], stack[-2] = stack[-2], stack[-1]
                pc += 1
            elif op == "ADD":
                if len(stack) < 2:
                    raise _Under()
                a = stack.pop()
                b = stack.pop()
                stack.append(b + a)
                pc += 1
            elif op == "SUB":
                if len(stack) < 2:
                    raise _Under()
                a = stack.pop()
                b = stack.pop()
                stack.append(b - a)
                pc += 1
            elif op == "MUL":
                if len(stack) < 2:
                    raise _Under()
                a = stack.pop()
                b = stack.pop()
                stack.append(b * a)
                pc += 1
            elif op == "PRINT":
                if not stack:
                    raise _Empty()
                out.append(str(stack.pop()))
                pc += 1
            elif op == "JNZ":
                if not stack:
                    raise _Empty()
                v = stack.pop()
                if v != 0:
                    if arg < 0 or arg >= len(prog):
                        return (False, out)
                    pc = arg
                else:
                    pc += 1
            elif op == "HALT":
                return (True, out)
            else:
                return (False, out)
        except _Empty:
            return (False, out)
        except _Under:
            return (False, out)


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return "ERR"
    try:
        k = _parse_int(lines[idx].strip())
    except ValueError:
        return "ERR"
    if not (1 <= k <= 64):
        return "ERR"
    idx += 1

    prog = []
    for _ in range(k):
        if idx >= len(lines):
            return "ERR"
        raw = lines[idx]
        idx += 1
        try:
            prog.append(_parse_instr(raw))
        except ValueError:
            return "ERR"

    ok, out = _run(prog)
    if not ok:
        return "ERR"
    return "\n".join(out)
