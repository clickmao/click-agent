#!/usr/bin/env bash
# R623 复现件：DoD 面 4「上下文精排」四值读数（NDCG@k / MRR / Precision@k / Recall@N）+ 生效遥测
#
# 用法: bash eval/rover/r623/repro-r623.sh [输出目录]
#   - 默认输出目录 = eval/rover/r623/
#   - 逐跑次落盘 rerank-face-readings-fusion-k50.json（器具自身写盘 = 唯一权威读数件）
#   - 本脚本只做「构建一次 + 按形态跑 n 次 + 确定性比对」，不改任何阈值
#
# 形态环境变量（测量形态，非阈值）:
#   AGENTFRAMEWORK_R623_SHAPE=fusion|legacy   缺省 fusion（= 生产 DI 形状）
#   AGENTFRAMEWORK_R623_TOPK=<int>            缺省 50（召回池 = 精排可重排空间；精排在 Take(TopK) 之后执行）
set -u
cd "$(dirname "$0")/../../.." || exit 1
OUT="${1:-eval/rover/r623}"
N="${R623_RUNS:-3}"

export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$PATH"

dotnet build src/agent.tests/agentframework.tests.csproj --nologo -v q || { echo "BUILD_FAIL"; exit 2; }

rc=0
for i in $(seq 1 "$N"); do
  line=$(dotnet test src/agent.tests/agentframework.tests.csproj --no-build \
      --filter "FullyQualifiedName~RerankFaceTests" --nologo -v q 2>&1 | grep -E '^(Passed!|Failed!)')
  echo "run$i: $line"
  case "$line" in
    Passed!*) ;;
    *) rc=1 ;;
  esac
  mkdir -p "$OUT/runs"
  cp eval/rover/r623/rerank-face-readings-fusion-k50.json "$OUT/runs/run$i.json" 2>/dev/null
done

python3 - "$OUT" "$N" <<'PY'
import json, io, sys, pathlib
out, n = pathlib.Path(sys.argv[1]), int(sys.argv[2])
def load(p):
    d = json.load(io.open(p, encoding='utf-8')); d.pop('ts', None); return d
files = [out / 'runs' / f'run{i}.json' for i in range(1, n + 1)]
files = [f for f in files if f.exists()]
uniq = {json.dumps(load(f), sort_keys=True, ensure_ascii=False) for f in files}
print('DET_RUNS=%d DET_UNIQUE=%d' % (len(files), len(uniq)))
d = load(out / 'rerank-face-readings-fusion-k50.json')
print('CRITERIA=', json.dumps(d['criteria'], ensure_ascii=False))
print('TELEMETRY=', json.dumps(d['telemetry'], ensure_ascii=False))
for arm in ('C', 'T', 'NEG', 'POS'):
    a = d['aggregates'][arm]
    print(arm, ' '.join('%s=%.4f' % (k.replace('median_', ''), v) for k, v in a.items() if k.startswith('median')))
sys.exit(0 if len(uniq) == 1 else 3)
PY
echo "R623_REPRO_RC=$rc"
exit "$rc"
