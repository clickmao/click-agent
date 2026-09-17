def solve(text: str) -> str:
    lines = text.split('\n')
    try:
        k = int(lines[0].strip())
    except Exception:
        return 'ERR'
    prog = []
    for i in range(1, k + 1):
        if i >= len(lines):
            return 'ERR'
        prog.append(lines[i].strip())
    stack = []
    out = []
    pc = 0
    steps = 0
    try:
        while True:
            steps += 1
            if steps > 10000:
                return 'ERR'
            if pc < 0 or pc >= len(prog):
                return 'ERR'
            parts = prog[pc].split()
            if not parts:
                return 'ERR'
            op = parts[0]
            if op == 'PUSH':
                if len(parts) != 2:
                    return 'ERR'
                stack.append(int(parts[1]))
                pc += 1
            elif op == 'POP':
                if len(parts) != 1 or not stack:
                    return 'ERR'
                stack.pop()
                pc += 1
            elif op in ('ADD', 'SUB', 'MUL'):
                if len(parts) != 1 or len(stack) < 2:
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
                if len(parts) != 1 or not stack:
                    return 'ERR'
                stack.append(stack[-1])
                pc += 1
            elif op == 'SWAP':
                if len(parts) != 1 or len(stack) < 2:
                    return 'ERR'
                stack[-1], stack[-2] = stack[-2], stack[-1]
                pc += 1
            elif op == 'PRINT':
                if len(parts) != 1 or not stack:
                    return 'ERR'
                out.append(str(stack.pop()))
                pc += 1
            elif op == 'JNZ':
                if len(parts) != 2 or not stack:
                    return 'ERR'
                t = int(parts[1])
                v = stack.pop()
                if v != 0:
                    if t < 0 or t >= len(prog):
                        return 'ERR'
                    pc = t
                else:
                    pc += 1
            elif op == 'HALT':
                if len(parts) != 1:
                    return 'ERR'
                break
            else:
                return 'ERR'
    except Exception:
        return 'ERR'
    return '\n'.join(out)
