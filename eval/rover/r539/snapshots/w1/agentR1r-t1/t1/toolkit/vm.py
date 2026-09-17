def solve(text: str) -> str:
    """Execute a small stack VM.

    Input: first line integer k (number of instructions), then k instruction
    lines (addresses start at 0).
    Output: PRINT results one per line; 'ERR' on any fault.
    """
    lines = text.split('\n')
    if not lines:
        return 'ERR'
    head = lines[0].strip()
    if head == '' or not head.isdigit():
        return 'ERR'
    try:
        k = int(head)
    except ValueError:
        return 'ERR'
    if k < 1 or k > 64:
        return 'ERR'
    prog = [ln.rstrip('\r') for ln in lines[1:1 + k]]
    if len(prog) < k:
        return 'ERR'

    def parse_int(s):
        if s == '':
            return None
        b = s[1:] if s[0] == '-' else s
        if b == '' or not b.isdigit():
            return None
        return int(s)

    out = []
    stack = []
    pc = 0
    steps = 0
    while True:
        if pc < 0 or pc >= k:
            return 'ERR'
        steps += 1
        if steps > 10000:
            return 'ERR'
        parts = prog[pc].split()
        if not parts:
            return 'ERR'
        op = parts[0]
        pc += 1
        if op == 'PUSH':
            if len(parts) != 2:
                return 'ERR'
            n = parse_int(parts[1])
            if n is None:
                return 'ERR'
            stack.append(n)
        elif op == 'POP':
            if len(parts) != 1 or not stack:
                return 'ERR'
            stack.pop()
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
        elif op == 'DUP':
            if len(parts) != 1 or not stack:
                return 'ERR'
            stack.append(stack[-1])
        elif op == 'SWAP':
            if len(parts) != 1 or len(stack) < 2:
                return 'ERR'
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == 'PRINT':
            if len(parts) != 1 or not stack:
                return 'ERR'
            out.append(str(stack.pop()))
        elif op == 'JNZ':
            if len(parts) != 2 or not stack:
                return 'ERR'
            target = parse_int(parts[1])
            if target is None or target < 0 or target >= k:
                return 'ERR'
            v = stack.pop()
            if v != 0:
                pc = target
        elif op == 'HALT':
            if len(parts) != 1:
                return 'ERR'
            return '\n'.join(out)
        else:
            return 'ERR'
