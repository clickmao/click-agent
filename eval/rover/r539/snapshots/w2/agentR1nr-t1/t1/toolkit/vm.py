ERR = 'ERR'


def solve(text):
    lines = text.split('\n')
    if not lines:
        return ERR
    try:
        k = int(lines[0].strip())
    except ValueError:
        return ERR
    if k < 1 or k > 64:
        return ERR
    if len(lines) - 1 < k:
        return ERR
    program = []
    for i in range(k):
        program.append(lines[i + 1].strip())

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if pc < 0 or pc >= k:
            return ERR
        if steps >= 10000:
            return ERR
        steps += 1
        parts = program[pc].split()
        if not parts:
            return ERR
        op = parts[0]
        args = parts[1:]
        if op == 'PUSH':
            if len(args) != 1:
                return ERR
            try:
                n = int(args[0])
            except ValueError:
                return ERR
            stack.append(n)
            pc += 1
        elif op == 'POP':
            if len(args) != 0:
                return ERR
            if not stack:
                return ERR
            stack.pop()
            pc += 1
        elif op == 'ADD':
            if len(args) != 0:
                return ERR
            if len(stack) < 2:
                return ERR
            a = stack.pop()
            b = stack.pop()
            stack.append(b + a)
            pc += 1
        elif op == 'SUB':
            if len(args) != 0:
                return ERR
            if len(stack) < 2:
                return ERR
            a = stack.pop()
            b = stack.pop()
            stack.append(b - a)
            pc += 1
        elif op == 'MUL':
            if len(args) != 0:
                return ERR
            if len(stack) < 2:
                return ERR
            a = stack.pop()
            b = stack.pop()
            stack.append(b * a)
            pc += 1
        elif op == 'DUP':
            if len(args) != 0:
                return ERR
            if not stack:
                return ERR
            stack.append(stack[-1])
            pc += 1
        elif op == 'SWAP':
            if len(args) != 0:
                return ERR
            if len(stack) < 2:
                return ERR
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == 'PRINT':
            if len(args) != 0:
                return ERR
            if not stack:
                return ERR
            out.append(str(stack.pop()))
            pc += 1
        elif op == 'JNZ':
            if len(args) != 1:
                return ERR
            if not stack:
                return ERR
            try:
                a = int(args[0])
            except ValueError:
                return ERR
            if a < 0 or a >= k:
                return ERR
            v = stack.pop()
            if v != 0:
                pc = a
            else:
                pc += 1
        elif op == 'HALT':
            if len(args) != 0:
                return ERR
            return '\n'.join(out)
        else:
            return ERR
