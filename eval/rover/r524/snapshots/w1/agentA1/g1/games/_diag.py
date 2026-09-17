import os, sys, subprocess

cwd = os.getcwd()
print("cwd =", cwd)
print("listing =", sorted(os.listdir(cwd)))
print("games/__main__.py exists:", os.path.exists(os.path.join(cwd, "games", "__main__.py")))

p = subprocess.run([sys.executable, "-m", "games.wythoff"], capture_output=True, text=True)
print("run rc =", p.returncode)
print("run out =", repr(p.stdout))
print("run err =", repr(p.stderr))

# Check for the -m machinery finding the package
import importlib.util
spec = importlib.util.find_spec("games.wythoff")
print("spec =", spec)
code = "import games.wythoff as m; print('loaded', m.__file__)"
p2 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
print("child -c rc =", p2.returncode)
print("child -c out =", repr(p2.stdout))
print("child -c err =", repr(p2.stderr))
