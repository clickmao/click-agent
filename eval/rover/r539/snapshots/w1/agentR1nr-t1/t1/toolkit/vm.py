def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines:
        return 'ERR'
    try:
        k = int(lines[0].strip())
    except Exception:
        return 'ERR'
    if k < 1 or k > 64:
        return 'ERR'
    prog = []
    for i in range(1, k + 1):
        if i >= len(lines):
            return 'ERR'
        prog.append(lines[i])

    def parse_instr(line):
        parts = line.split()
        if not parts:
            return (None, None)
        op = parts[0]
        if op in ('ADD', 'SUB', 'MUL', 'DUP', 'SWAP', 'PRINT', 'HALT', 'POP'):
            if len(parts) != 1:
                return (None, None)
            return (op, None)
        if op in ('PUSH', 'JNZ'):
            if len(parts) != 2:
                return (None, None)
            try:
                n = int(parts[1])
            except Exception:
                return (None, None)
            return (op, n)
        return (None, None)

    parsed = []
    for line in prog:
        op, arg = parse_instr(line)
        parsed.append((op, arg))

    out = []
    stack = []
    pc = 0
    steps = 0
    n = len(parsed)
    while True:
        if pc < 0 or pc >= n:
            if pc == n:
                return 'ERR'
            return 'ERR'
        steps += 1
        if steps > 10000:
            return 'ERR'
        op, arg = parsed[pc]
        if op is None:
            return 'ERR'
        if op == 'PUSH':
            stack.append(arg)
            pc += 1
        elif op == 'POP':
            if not stack:
                return 'ERR'
            stack.pop()
            pc += 1
        elif op == 'DUP':
            if not stack:
                return 'ERR'
            stack.append(stack[-1])
            pc += 1
        elif op == 'SWAP':
            if len(stack) < 2:
                return 'ERR'
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op in ('ADD', 'SUB', 'MUL'):
            if len(stack) < 2:
                return 'ERR'
            a = stack.pop()
            b = stack.pop()
            if op == 'ADD':
                r = b + a
            elif op == 'SUB':
                r = b - a
            else:
                r = b * a
            stack.append(r)
            pc += 1
        elif op == 'PRINT':
            if not stack:
                return 'ERR'
            out.append(str(stack.pop()))
            pc += 1
        elif op == 'JNZ':
            if not stack:
                return 'ERR'
            v = stack.pop()
            if v != 0:
                if arg is None or arg < 0 or arg >= n:
                    return 'ERR'
                pc = arg
            else:
                pc += 1
        elif op == 'HALT':
            break
        else:
            return 'ERR'
    return '\n'.join(out)
