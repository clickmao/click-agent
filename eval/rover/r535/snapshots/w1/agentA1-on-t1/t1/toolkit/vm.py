"""vm_run: 栈式虚拟机解释器。

solve(text) -> str
  text: 完整 stdin 文本
  返回: 应写出的 stdout 文本, 末尾不带换行

指令集: PUSH n / POP / ADD / SUB / MUL / DUP / SWAP / PRINT / JNZ a / HALT
出错情形: 栈空弹栈、操作数不足、跳转地址越界、超过 10000 步未 HALT、执行流越过最后一条指令。
出错时只输出 "ERR"。
"""

_LIMIT = 10000


class _Err(Exception):
    pass


def solve(text: str) -> str:
    lines = text.split("\n")
    if len(lines) < 1:
        return "ERR"
    try:
        k = int(lines[0].strip())
    except ValueError:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    if len(lines) < 1 + k:
        return "ERR"

    prog = []
    for i in range(1, 1 + k):
        parts = lines[i].split()
        if not parts:
            return "ERR"
        prog.append(parts)

    stack = []
    out = []
    steps = 0
    pc = 0

    def pop():
        if not stack:
            raise _Err()
        return stack.pop()

    while True:
        if pc < 0 or pc >= k:
            return "ERR"
        if steps >= _LIMIT:
            return "ERR"
        steps += 1
        ins = prog[pc]
        op = ins[0]
        try:
            if op == "PUSH":
                if len(ins) != 2:
                    return "ERR"
                stack.append(int(ins[1]))
            elif op == "POP":
                if len(ins) != 1:
                    return "ERR"
                pop()
            elif op == "ADD":
                if len(ins) != 1:
                    return "ERR"
                a = pop()
                b = pop()
                stack.append(b + a)
            elif op == "SUB":
                if len(ins) != 1:
                    return "ERR"
                a = pop()
                b = pop()
                stack.append(b - a)
            elif op == "MUL":
                if len(ins) != 1:
                    return "ERR"
                a = pop()
                b = pop()
                stack.append(b * a)
            elif op == "DUP":
                if len(ins) != 1:
                    return "ERR"
                if not stack:
                    return "ERR"
                stack.append(stack[-1])
            elif op == "SWAP":
                if len(ins) != 1:
                    return "ERR"
                if len(stack) < 2:
                    return "ERR"
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif op == "PRINT":
                if len(ins) != 1:
                    return "ERR"
                out.append(str(pop()))
            elif op == "JNZ":
                if len(ins) != 2:
                    return "ERR"
                target = int(ins[1])
                v = pop()
                if target < 0 or target >= k:
                    return "ERR"
                if v != 0:
                    pc = target
                    continue
            elif op == "HALT":
                if len(ins) != 1:
                    return "ERR"
                return "\n".join(out)
            else:
                return "ERR"
        except _Err:
            return "ERR"
        except (ValueError, IndexError):
            return "ERR"
        pc += 1
