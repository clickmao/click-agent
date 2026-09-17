"""vm 子命令: 栈式虚拟机解释器。

导出: solve(text: str) -> str
  入参 text = 完整 stdin 文本; 返回 = 应写出的 stdout 文本 (末尾不带换行)。

指令集:
  PUSH n  压入整数 n
  POP     弹出丢弃
  ADD     弹出 a=栈顶, b=次顶, 压入 b-a
  SUB     弹出 a=栈顶, b=次顶, 压入 b-a
  MUL     弹出 a=栈顶, b=次顶, 压入 b-a
  DUP     复制栈顶
  SWAP    交换栈顶两元素
  PRINT   弹出栈顶并输出一行
  JNZ a   弹出栈顶, 非 0 则跳转到地址 a, 否则继续
  HALT    结束

出错 (栈空弹栈 / 操作数不足 / 跳转越界 / 未在 10000 步内 HALT / 执行流越过末条指令)
只输出一行 ERR。
"""


def solve(text: str):
    lines = text.split("\n")
    # 去掉可能的尾部空行产生的空串, 但保留内部结构
    idx = 0
    n_lines = len(lines)
    if idx >= n_lines:
        return "ERR"
    first = lines[idx].strip()
    idx += 1
    try:
        k = int(first)
    except Exception:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"

    prog = []
    for _ in range(k):
        if idx >= n_lines:
            return "ERR"
        instr = lines[idx].strip()
        idx += 1
        parts = instr.split()
        if len(parts) == 0:
            return "ERR"
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                return "ERR"
            try:
                val = int(parts[1])
            except Exception:
                return "ERR"
            prog.append(("PUSH", val))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return "ERR"
            prog.append((op, 0))
        elif op == "JNZ":
            if len(parts) != 2:
                return "ERR"
            try:
                addr = int(parts[1])
            except Exception:
                return "ERR"
            prog.append(("JNZ", addr))
        else:
            return "ERR"

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if pc < 0 or pc >= k:
            return "ERR"
        steps += 1
        if steps > 10000:
            return "ERR"
        op, arg = prog[pc]
        if op == "PUSH":
            stack.append(arg)
            pc += 1
        elif op == "POP":
            if not stack:
                return "ERR"
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
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
            if not stack:
                return "ERR"
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return "ERR"
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                return "ERR"
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                return "ERR"
            v = stack.pop()
            if v != 0:
                if arg < 0 or arg >= k:
                    return "ERR"
                pc = arg
            else:
                pc += 1
        elif op == "HALT":
            break
        else:
            return "ERR"

    return "\n".join(out)
