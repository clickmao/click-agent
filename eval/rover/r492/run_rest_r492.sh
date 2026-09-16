#!/usr/bin/env bash
# R492 臂矩阵 (同一二进制/夹具/窗; 唯一差异 = pair_trim 开关): TC(关, 对照) + TP1..TP3(开)
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r492/agenthost
# key 只进中继进程 env, 不落文件/日志: 从 .env.local 就地取值到变量 (值不打印)
R492_UPSTREAM_KEY="$(python3 - <<'PY'
import io
for line in io.open('.env.local', encoding='utf-8', errors='replace'):
    s = line.strip()
    if s.startswith('AGENTFRAMEWORK_KEYS_DEEPSEEK='):
        print(s.split('=', 1)[1].strip().strip('"').strip("'")); break
PY
)"
export R492_UPSTREAM_KEY
[ -n "${R492_UPSTREAM_KEY:-}" ] || { echo "[致命] 未取到上游 key"; exit 9; }

run() { # arm tag relay_port api_port pair_trim
  echo "=== $(date '+%T') arm=$1 tag=$2 ports=$3/$4 pair_trim=$5 ==="
  bash eval/rover/r492/run_arm_real_r492.sh "$1" "$2" "$3" "$4" "$5"
  local rc=$?; echo "[rc=$rc] arm=$1$2 $(date '+%T')"
  [ "$rc" -eq 0 ] || { echo "[致命] 臂 $1$2 失败 rc=$rc ⇒ 中止矩阵 (禁带残留续跑)"; exit "$rc"; }
}
run T C  49210 49212 off
run T P1 49214 49216 on
run T P2 49218 49220 on
run T P3 49222 49224 on
echo "ALLDONE $(date '+%T')"
