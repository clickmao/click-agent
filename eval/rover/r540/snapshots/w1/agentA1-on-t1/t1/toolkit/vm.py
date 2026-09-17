"""vm_run 子命令: 简易栈式虚拟机。

读入: 第一行整数 k (1<=k<=64, 指令条数); 随后 k 行, 每行一条指令 (地址从 0 开始)。
指令集:
  PUSH n  压入整数 n
  POP     弹出丢弃
  ADD     弹出 a=栈顶, b=次顶, 压入 b+a
  SUB     压入 b-a
  MUL     压入 b*a
  DUP     复制栈顶
  SWAP    交换栈顶两元素
  PRINT   弹出栈顶并输出一行
  JNZ a   弹出栈顶, 非 0 则跳转到地址 a, 否则继续
  HALT    结束
错误条件 (只输出一行 ERR): 栈空弹栈、操作数不足、跳转地址越界、
  未在 10000 步内执行 HALT、执行流越过最后一条指令。
"""

_STEP_LIMIT = 10000


def solve(text: str) -> str:
    lines = text.split("\n")
    # 去掉最后一个换行造成的尾部空串
    if lines and lines[-1] == "":
        lines.pop()

    if not lines:
        return "ERR"

    try:
        k = int(lines[0].strip())
    except ValueError:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    if len(lines) - 1 < k:
        return "ERR"

    program = []
    for i in range(k):
        program.append(lines[1 + i].strip())

    stack = []
    out = []
    # 解析首 token 与参数
    steps = 0

    def fail():
        raise _VmError()

    pc = 0
    try:
        while True:
            if pc < 0 or pc >= k:
                fail()
            steps += 1
            if steps > _STEP_LIMIT:
                fail()
            instr = program[pc]
            parts = instr.split()
            if not parts:
                fail()
            op = parts[0]
            if op == "PUSH":
                if len(parts) != 2:
                    fail()
                try:
                    n = int(parts[1])
                except ValueError:
                    fail()
                stack.append(n)
                pc += 1
            elif op == "POP":
                if len(parts) != 1:
                    fail()
                if not stack:
                    fail()
                stack.pop()
                pc += 1
            elif op in ("ADD", "SUB", "MUL"):
                if len(parts) != 1:
                    fail()
                if len(stack) < 2:
                    fail()
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
                if len(parts) != 1:
                    fail()
                if not stack:
                    fail()
                stack.append(stack[-1])
                pc += 1
            elif op == "SWAP":
                if len(parts) != 1:
                    fail()
                if len(stack) < 2:
                    fail()
                stack[-1], stack[-2] = stack[-2], stack[-1]
                pc += 1
            elif op == "PRINT":
                if len(parts) != 1:
                    fail()
                if not stack:
                    fail()
                out.append(str(stack.pop()))
                pc += 1
            elif op == "JNZ":
                if len(parts) != 2:
                    fail()
                if not stack:
                    fail()
                v = stack.pop()
                try:
                    a_addr = int(parts[1])
                except ValueError:
                    fail()
                if a_addr < 0 or a_addr >= k:
                    fail()
                pc = a_addr if v != 0 else pc + 1
            elif op == "HALT":
                if len(parts) != 1:
                    fail()
                break
            else:
                fail()
    except _VmError:
        return "ERR"

    return "\n".join(out)


class _VmError(Exception):
    pass
