import sys
sys.modules.pop('toolkit', None)
from toolkit import vm
code = open(vm.__file__).read()
code = code.replace('op, arg = prog[pc]',
                    'op, arg = prog[pc]\n            print("TRACE pc=", pc, "op=", op, "stack=", stack)')
ns = {}
exec(code, ns)
print("RESULT:", repr(ns['solve']('3\nPUSH 0\nJNZ 5\nPRINT\n')))
