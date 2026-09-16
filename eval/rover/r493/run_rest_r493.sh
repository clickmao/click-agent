#!/usr/bin/env bash
# R493 臂矩阵 (同一二进制 / 同一**新**夹具 / 同一窗; 唯一差异 = 开关组合):
#   B = Arole  (门关, 重复跳过关)          + pair_trim off   ⇒ 对照 (生产现状)
#   R = R      (门开, 重复跳过开)          + pair_trim off   ⇒ r1 本地通道**独立**增益
#   T = T      (门开, 重复跳过开, 声明门开) + pair_trim on    ⇒ 全链候选形态 (主 KPI)
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r492/agenthost   # R492 冻结产物 (R493 不改链代码)
# key 只进中继进程 env, 不落文件/日志: 从 .env.local 就地取值到变量 (值不打印)
R493_UPSTREAM_KEY="$(python3 - <<'PY'
import io
for line in io.open('.env.local', encoding='utf-8', errors='replace'):
    s = line.strip()
    if s.startswith('AGENTFRAMEWORK_KEYS_DEEPSEEK='):
        print(s.split('=', 1)[1].strip().strip('"').strip("'")); break
PY
)"
export R493_UPSTREAM_KEY
[ -n "${R493_UPSTREAM_KEY:-}" ] || { echo "[致命] 未取到上游 key"; exit 9; }

run() { # arm tag relay_port api_port pair_trim
  echo "=== $(date '+%T') arm=$1 tag=$2 ports=$3/$4 pair_trim=$5 ==="
  bash eval/rover/r493/run_arm_real_r493.sh "$1" "$2" "$3" "$4" "$5"
  local rc=$?; echo "[rc=$rc] arm=$1$2 $(date '+%T')"
  [ "$rc" -eq 0 ] || { echo "[致命] 臂 $1$2 失败 rc=$rc ⇒ 中止矩阵 (禁带残留续跑)"; exit "$rc"; }
}
run Arole b  49310 49312 off
run R     '' 49314 49316 off
run T     '' 49318 49320 on
echo "ALLDONE $(date '+%T')"
