import subprocess
import sys


case_id, game_id = sys.argv[1], sys.argv[2]
with open('cases/' + case_id + '.in', 'r') as f_in:
    data = f_in.read()
proc = subprocess.run(
    [sys.executable, '-m', 'games', game_id],
    input=data,
    capture_output=True,
    text=True,
)
with open('cases/' + case_id + '.out', 'r') as f_out:
    expected = f_out.read()
sys.stdout.write('STDERR=' + repr(proc.stderr) + '\n')
sys.stdout.write('MATCH=' + str(proc.stdout == expected) + '\n')
