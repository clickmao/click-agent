def solve(text: str) -> str:
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    if p >= len(lines):
        return 'ERR'
    try:
        k = int(lines[p].strip())
    except ValueError:
        return 'ERR'
    p += 1
    prog = []
    for i in range(k):
        if p >= len(lines):
            return 'ERR'
        parts = lines[p].strip().split()
        p += 1
        if not parts:
            return 'ERR'
        op = parts[0]
        if op == 'PUSH':
            if len(parts) != 2:
                return 'ERR'
            try:
                n = int(parts[1])
            except ValueError:
                return 'ERR'
            prog.append(('PUSH', n))
        elif op in ('POP', 'ADD', 'SUB', 'MUL', 'DUP', 'SWAP', 'PRINT', 'HALT'):
            if len(parts) != 1:
                return 'ERR'
            prog.append((op, None))
        elif op == 'JNZ':
            if len(parts) != 2:
                return 'ERR'
            try:
                a = int(parts[1])
            except ValueError:
                return 'ERR'
            prog.append(('JNZ', a))
        else:
            return 'ERR'
    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        steps += 1
        if steps > 10000:
            return 'ERR'
        if pc < 0 or pc >= k:
            return 'ERR'
        op, arg = prog[pc]
        if op == 'PUSH':
            stack.append(arg)
            pc += 1
        elif op == 'POP':
            if not stack:
                return 'ERR'
            stack.pop()
            pc += 1
        elif op in ('ADD', 'SUB', 'MUL'):
            if len(stack) < 2:
                return 'ERR'
            a = stack.pop()
            b = stack.pop()
            if op == 'ADD':
                stack.append(b + a)
            elif op == 'SUB':
                stack.append(b - a)
            else:
                stack.append(b * a)
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
                if arg < 0 or arg >= k:
                    return 'ERR'
                pc = arg
            else:
                pc += 1
        elif op == 'HALT':
            break
    return '\n'.join(out)
