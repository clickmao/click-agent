def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines:
        return 'ERR'
    try:
        k = int(lines[0].strip())
    except ValueError:
        return 'ERR'
    if k < 1 or k > 64:
        return 'ERR'
    prog = []
    for i in range(1, k + 1):
        if i >= len(lines):
            return 'ERR'
        prog.append(lines[i].strip())
    if len(lines) > k + 1:
        for extra in lines[k + 1:]:
            if extra.strip() != '':
                return 'ERR'

    stack = []
    out = []
    steps = 0
    pc = 0
    n = len(prog)

    def pop():
        if not stack:
            raise RuntimeError('empty')
        return stack.pop()

    while True:
        if pc < 0 or pc >= n:
            return 'ERR'
        steps += 1
        if steps > 10000:
            return 'ERR'
        parts = prog[pc].split()
        if not parts:
            return 'ERR'
        op = parts[0]
        try:
            if op == 'PUSH':
                if len(parts) != 2:
                    return 'ERR'
                stack.append(int(parts[1]))
                pc += 1
            elif op == 'POP':
                if len(parts) != 1:
                    return 'ERR'
                pop()
                pc += 1
            elif op == 'ADD':
                if len(parts) != 1:
                    return 'ERR'
                a = pop(); b = pop()
                stack.append(b + a)
                pc += 1
            elif op == 'SUB':
                if len(parts) != 1:
                    return 'ERR'
                a = pop(); b = pop()
                stack.append(b - a)
                pc += 1
            elif op == 'MUL':
                if len(parts) != 1:
                    return 'ERR'
                a = pop(); b = pop()
                stack.append(b * a)
                pc += 1
            elif op == 'DUP':
                if len(parts) != 1:
                    return 'ERR'
                if not stack:
                    return 'ERR'
                stack.append(stack[-1])
                pc += 1
            elif op == 'SWAP':
                if len(parts) != 1:
                    return 'ERR'
                if len(stack) < 2:
                    return 'ERR'
                stack[-1], stack[-2] = stack[-2], stack[-1]
                pc += 1
            elif op == 'PRINT':
                if len(parts) != 1:
                    return 'ERR'
                out.append(str(pop()))
                pc += 1
            elif op == 'JNZ':
                if len(parts) != 2:
                    return 'ERR'
                v = pop()
                target = int(parts[1])
                if v != 0:
                    if target < 0 or target >= n:
                        return 'ERR'
                    pc = target
                else:
                    pc += 1
            elif op == 'HALT':
                if len(parts) != 1:
                    return 'ERR'
                break
            else:
                return 'ERR'
        except RuntimeError:
            return 'ERR'
        except ValueError:
            return 'ERR'
        if pc >= n:
            return 'ERR'
    return '\n'.join(out)
