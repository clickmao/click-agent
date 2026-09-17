"""vm_run 子命令: 一个极简栈式虚拟机的解释器。

规格:
  输入: 第一行整数 k (1<=k<=64, 指令条数); 随后 k 行, 每行一条指令 (地址 0 起)。
  指令:
    PUSH n   压入整数 n
    POP      弹出丢弃
    ADD      a=栈顶, b=次顶, 压入 b-a  ... 见下 (实际语义见 add)
    SUB      弹出 a=栈顶, b=次顶, 压入 b-a
    MUL      弹出 a=栈顶, b=次顶, 压入 b*a
    DUP      复制栈顶
    SWAP     交换栈顶两元素
    PRINT    弹出栈顶并输出一行
    JNZ a    弹出栈顶, 非 0 则跳到地址 a, 否则继续
    HALT     结束
  出错 (栈空弹栈/操作数不足/跳转越界/超 10000 步未 HALT/越过最后一条) => 只输出 "ERR"
"""

_LIMIT = 10000


def _parse(text):
    """把输入文本解析成 (指令列表, None) 或 (None, 错误原因)。

    指令以元组表示: (op, operand)  operand 对大部分指令为 None。
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return None, "no-header"
    head = lines[0].strip()
    if head == "":
        return None, "empty-k"
    try:
        k = int(head)
    except ValueError:
        return None, "bad-k"
    if k < 1 or k > 64:
        return None, "k-range"
    body = lines[1:]
    if len(body) != k:
        return None, "count-mismatch"
    prog = []
    for raw in body:
        s = raw.strip()
        if s == "":
            return None, "empty-instr"
        parts = s.split()
        op = parts[0].upper()
        if op == "PUSH":
            if len(parts) != 2:
                return None, "bad-push"
            try:
                n = int(parts[1])
            except ValueError:
                return None, "bad-push-num"
            prog.append(("PUSH", n))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return None, "trailing"
            prog.append((op, None))
        elif op == "JNZ":
            if len(parts) != 2:
                return None, "bad-jnz"
            try:
                a = int(parts[1])
            except ValueError:
                return None, "bad-jnz-num"
            prog.append(("JNZ", a))
        else:
            return None, "unknown-op"
    return prog, None


def _run(prog):
    """执行程序, 返回输出行列表, 出错返回 None。"""
    out = []
    st = []
    pc = 0
    steps = 0
    n = len(prog)
    while True:
        if pc < 0 or pc >= n:
            return None  # 执行流越过最后一条 / 越界陷入
        op, arg = prog[pc]
        steps += 1
        if steps > _LIMIT:
            return None
        if op == "PUSH":
            st.append(arg)
            pc += 1
        elif op == "POP":
            if not st:
                return None
            st.pop()
            pc += 1
        elif op == "DUP":
            if not st:
                return None
            st.append(st[-1])
            pc += 1
        elif op == "SWAP":
            if len(st) < 2:
                return None
            st[-1], st[-2] = st[-2], st[-1]
            pc += 1
        elif op == "ADD":
            if len(st) < 2:
                return None
            a = st.pop()
            b = st.pop()
            st.append(b + a)
            pc += 1
        elif op == "SUB":
            if len(st) < 2:
                return None
            a = st.pop()
            b = st.pop()
            st.append(b - a)
            pc += 1
        elif op == "MUL":
            if len(st) < 2:
                return None
            a = st.pop()
            b = st.pop()
            st.append(b * a)
            pc += 1
        elif op == "PRINT":
            if not st:
                return None
            out.append(str(st.pop()))
            pc += 1
        elif op == "JNZ":
            if not st:
                return None
            v = st.pop()
            if v != 0:
                if arg < 0 or arg >= n:
                    return None
                pc = arg
            else:
                pc += 1
        elif op == "HALT":
            return out
        else:
            return None


def solve(text):
    """纯函数: 输入完整 stdin 文本, 返回应写出的 stdout 文本 (末尾不含换行)。"""
    prog, err = _parse(text)
    if err is not None:
        return "ERR"
    out = _run(prog)
    if out is None:
        return "ERR"
    return "\n".join(out)
