"""vm_run: 栈式虚拟机解释器.

solve(text) 接收该子命令的完整 stdin 文本, 返回应写出的 stdout 文本 (不带末尾换行).

规格:
  第一行整数 k (1<=k<=64, 指令条数); 随后 k 行, 每行一条指令 (地址从 0 开始).
  指令集:
    PUSH n   压入整数 n
    POP      弹出丢弃
    ADD      弹出 a=栈顶, b=次顶, 压入 b+a
    SUB      弹出 a=栈顶, b=次顶, 压入 b-a
    MUL      弹出 a=栈顶, b=次顶, 压入 b*a
    DUP      复制栈顶
    SWAP     交换栈顶两元素
    PRINT    弹出栈顶并输出一行
    JNZ a    弹出栈顶, 非 0 则跳转到地址 a, 否则继续
    HALT     结束
  任一错误 (栈空弹栈 / 操作数不足 / 跳转越界 / 未在 10000 步内 HALT /
  执行流越过最后一条指令) => 只输出一行 ERR.
"""


class VMError(Exception):
    pass


def _parse_instruction(line):
    """把一行解析成 (op, arg) 元组; 非法则抛 VMError."""
    parts = line.split()
    if not parts:
        raise VMError("empty line")
    op = parts[0]
    if op == "PUSH":
        if len(parts) != 2:
            raise VMError("bad PUSH")
        try:
            n = int(parts[1])
        except ValueError:
            raise VMError("bad PUSH arg")
        return ("PUSH", n)
    if op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
        if len(parts) != 1:
            raise VMError("trailing tokens: " + op)
        return (op, None)
    if op == "JNZ":
        if len(parts) != 2:
            raise VMError("bad JNZ")
        try:
            a = int(parts[1])
        except ValueError:
            raise VMError("bad JNZ arg")
        return ("JNZ", a)
    raise VMError("unknown op: " + op)


def solve(text):
    lines = text.splitlines()
    if not lines:
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
    try:
        for i in range(k):
            prog.append(_parse_instruction(lines[1 + i].strip()))
    except VMError:
        return "ERR"

    stack = []
    out = []
    ip = 0
    steps = 0
    try:
        while True:
            steps += 1
            if steps > 10000:
                raise VMError("step limit")
            if ip < 0 or ip >= k:
                raise VMError("pc out of range")
            op, arg = prog[ip]
            if op == "PUSH":
                stack.append(arg)
            elif op == "POP":
                if not stack:
                    raise VMError("underflow POP")
                stack.pop()
            elif op == "ADD":
                if len(stack) < 2:
                    raise VMError("underflow ADD")
                a = stack.pop()
                b = stack.pop()
                stack.append(b + a)
            elif op == "SUB":
                if len(stack) < 2:
                    raise VMError("underflow SUB")
                a = stack.pop()
                b = stack.pop()
                stack.append(b - a)
            elif op == "MUL":
                if len(stack) < 2:
                    raise VMError("underflow MUL")
                a = stack.pop()
                b = stack.pop()
                stack.append(b * a)
            elif op == "DUP":
                if not stack:
                    raise VMError("underflow DUP")
                stack.append(stack[-1])
            elif op == "SWAP":
                if len(stack) < 2:
                    raise VMError("underflow SWAP")
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif op == "PRINT":
                if not stack:
                    raise VMError("underflow PRINT")
                out.append(str(stack.pop()))
            elif op == "JNZ":
                if not stack:
                    raise VMError("underflow JNZ")
                v = stack.pop()
                if v != 0:
                    if arg < 0 or arg >= k:
                        raise VMError("jump out of range")
                    ip = arg
                    continue
            elif op == "HALT":
                return "\n".join(out)
            ip += 1
    except VMError:
        return "ERR"
