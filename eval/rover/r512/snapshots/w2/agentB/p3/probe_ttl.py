import subprocess, sys, os, tempfile, json, http.client
d = tempfile.mkdtemp(); wal = os.path.join(d, 'w.log')
p = subprocess.Popen([sys.executable, '-m', 'kvsvc.server', '--port', '8802', '--wal', wal],
                     stdout=subprocess.PIPE, text=True)
print('READY:', repr(p.stdout.readline()))
c = http.client.HTTPConnection('127.0.0.1', 8802, timeout=5)
c.request('PUT', '/kv/short', body=json.dumps({'value': 'x', 'ttl': 0.2}).encode(),
          headers={'Content-Type': 'application/json'})
r = c.getresponse(); print('status', r.status); print('body', r.read().decode())
p.terminate(); p.wait()
