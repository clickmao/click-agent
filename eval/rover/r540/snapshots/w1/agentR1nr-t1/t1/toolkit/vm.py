def solve(text: str) -> str:
    lines = text.split('\n')
    try:
        k = int(lines[0].strip())
    except Exception:
        return 'ERR'
    prog = []
    for i in range(1, k + 1):
        prog.append(lines[i].strip())
    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        steps += 1
        if steps > 10000 or pc < 0 or pc >= len(prog):
            return 'ERR'
        parts = prog[pc].split()
        op = parts[0]
        if op == 'PUSH':
            stack.append(int(parts[1]))
            pc += 1
        elif op == 'POP':
            if not stack:
                return 'ERR'
            stack.pop()
            pc += 1
        elif op == 'ADD':
            if len(stack) < 2:
                return 'ERR'
            a = stack.pop()
            b = stack.pop()
            stack.append(b + a)
            pc += 1
        elif op == 'SUB':
            if len(stack) < 2:
                return 'ERR'
            a = stack.pop()
            b = stack.pop()
            stack.append(b - a)
            pc += 1
        elif op == 'MUL':
            if len(stack) < 2:
                return 'ERR'
            a = stack.pop()
            b = stack.pop()
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
            t = int(parts[1])
            if v != 0:
                if t < 0 or t >= len(prog):
                    return 'ERR'
                pc = t
            else:
                pc += 1
        elif op == 'HALT':
            break
        else:
            return 'ERR'
    return '\n'.join(out)
