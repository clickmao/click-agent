_OPS = ('PUSH', 'POP', 'ADD', 'SUB', 'MUL', 'DUP', 'SWAP', 'PRINT', 'JNZ', 'HALT')


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    lines = [ln.strip() for ln in lines if ln.strip() != '']
    if not lines:
        return 'ERR'
    try:
        k = int(lines[0])
    except ValueError:
        return 'ERR'
    if k < 1 or k > 64:
        return 'ERR'
    body = lines[1:]
    if len(body) != k:
        return 'ERR'

    prog = []
    for raw in body:
        parts = raw.split(' ')
        if parts[0] not in _OPS:
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
        elif op == 'JNZ':
            if len(parts) != 2:
                return 'ERR'
            try:
                a = int(parts[1])
            except ValueError:
                return 'ERR'
            prog.append(('JNZ', a))
        else:
            if len(parts) != 1:
                return 'ERR'
            prog.append((op, None))

    out = []
    st = []
    pc = 0
    steps = 0
    n = len(prog)
    while steps < 10000:
        if pc < 0 or pc >= n:
            return 'ERR'
        op, arg = prog[pc]
        steps += 1
        if op == 'PUSH':
            st.append(arg)
        elif op == 'POP':
            if not st:
                return 'ERR'
            st.pop()
        elif op == 'DUP':
            if not st:
                return 'ERR'
            st.append(st[-1])
        elif op == 'SWAP':
            if len(st) < 2:
                return 'ERR'
            st[-1], st[-2] = st[-2], st[-1]
        elif op == 'ADD':
            if len(st) < 2:
                return 'ERR'
            a = st.pop()
            b = st.pop()
            st.append(b + a)
        elif op == 'SUB':
            if len(st) < 2:
                return 'ERR'
            a = st.pop()
            b = st.pop()
            st.append(b - a)
        elif op == 'MUL':
            if len(st) < 2:
                return 'ERR'
            a = st.pop()
            b = st.pop()
            st.append(b * a)
        elif op == 'PRINT':
            if not st:
                return 'ERR'
            out.append(str(st.pop()))
        elif op == 'JNZ':
            if not st:
                return 'ERR'
            v = st.pop()
            if v != 0:
                if arg < 0 or arg >= n:
                    return 'ERR'
                pc = arg
                continue
        elif op == 'HALT':
            return '\n'.join(out)
        pc += 1
    return 'ERR'
