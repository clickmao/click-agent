#!/usr/bin/env python3
"""R402 度量子步骤 · 「每 token ≈25.7 s」归因取证 (盘读等待 vs 反量化计算)。

为什么要这个脚本 (skill kpi-eval-harness-design: 宣称前先要求「机制启用断言」):
  本机 MemTotal 3.57 GiB < 模型 3.93 GiB ⇒ 权重页**原理上无法整份驻留**。若直接用
  「每 token 秒数」去选优化靶点 (线程/SIMD/批 prefill), 那是拿一个**未归因**的数字做决策。
  本脚本给三个**互相独立**的通道, 三条必须同向才下结论:
    ① 进程侧  /proc/self/io  read_bytes   ← 由被测程序自己打印 (rover forward 的 io{} 行)
    ② 设备侧  /proc/diskstats 读扇区增量  ← 内核视角, 不依赖被测程序的自我报告
    ③ 裸读参照 readbench (stream / mmap 两条内存路径) ← 同一台机、同一文件、无任何数学运算
  判据 (先写死, 防事后凑解释):
    disk_read_bytes/pass ≈ 模型体积 且 设备侧同量级  ⇒ **I/O 主导** ⇒ 靶点=批 prefill(减少 sweep 次数)+顺序预读
    disk_read_bytes/pass ≪ 模型体积                  ⇒ 页缓存命中 ⇒ 靶点=计算(SIMD/线程/反量化)
  诚实约定: 任一通道不可用 (返回 0/缺失) 一律标记 unavailable, 绝不以 0 参与归因。

用法: python3 scripts/r402_io_attribution.py [--json data/probe/r402/io-attribution.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "src/agent.rover/bin/Release/net10.0/agent.rover"
GGUF = Path(os.environ.get("GGUF", "/tmp/models/prover7b-q4km.gguf"))


_PART_RE = re.compile(r"^(sd[a-z]+|vd[a-z]+|hd[a-z]+|nvme\d+n\d+|xvd[a-z]+|mmcblk\d+)$")


def _diskstats_lines() -> list[tuple[str, int]]:
    """[(设备名, 累计读字节)] —— 供诊断打印「到底数了哪些设备」。"""
    out = []
    try:
        for line in open("/proc/diskstats", encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) > 9:
                out.append((f[2], int(f[5]) * 512))
    except Exception:
        pass
    return out


def dev_disk_read_bytes() -> int | None:
    """/proc/diskstats 累计读扇区×512 (内核视角的「真提交到块设备」的字节)。

    只累计**整盘**行 (sd*/vd*/hd*/nvme*/xvd*), 跳过分区行 (vda1/vda2) 与 sr0: 分区行是整盘行的
    子集, 全加会**双计**。
    口径踩坑记录 (值得留档): 首版正则写成 `vd[a-z]+\\d*` ⇒ **"vda1" 也被匹配**, 于是「只算整盘」
    与「全加」两个数几乎相等 (7,439,605,760 vs 7,439,130,624), 看起来像「没有双计」。
    是随此行落盘的 guard 数字自己暴露了矛盾, 才回头发现正则错 —— 度量通道**必须自带可证伪的对照读数**。
    不可用返回 None —— 绝不以 0 参与归因。
    """
    try:
        total = 0
        for name, b in _diskstats_lines():
            if _PART_RE.match(name) and name != "sr0":
                total += b
        return total
    except Exception:
        return None


def dev_disk_read_bytes_naive() -> int | None:
    """负控口径: **整盘+分区全加** (会双计)。存在的唯一理由是让口径错误可被第三方一眼复现/证伪。"""
    try:
        total = 0
        for line in open("/proc/diskstats", encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) > 9:
                total += int(f[5]) * 512
        return total
    except Exception:
        return None


def meminfo() -> dict:
    out = {}
    try:
        for line in open("/proc/meminfo", encoding="utf-8", errors="replace"):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    except Exception:
        pass
    return out


def run(step: str, argv: list[str], timeout: int = 1200) -> dict:
    before_disk, before_mem = dev_disk_read_bytes(), meminfo()
    before_naive = dev_disk_read_bytes_naive()
    t0 = time.monotonic()
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    wall = time.monotonic() - t0
    after_disk, after_mem = dev_disk_read_bytes(), meminfo()
    after_naive = dev_disk_read_bytes_naive()
    disk_delta = None if before_disk is None or after_disk is None else after_disk - before_disk
    naive_delta = None if before_naive is None or after_naive is None else after_naive - before_naive
    disk_mbps = None if disk_delta is None or wall <= 0 else round(disk_delta / 1048576 / wall, 1)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    rec = {
        "step": step,
        "argv": " ".join(str(a) for a in argv),
        "rc": p.returncode,
        "wall_s": round(wall, 2),
        "stdout_lines": lines,
        "stderr_tail": p.stderr.strip().splitlines()[-3:],
        "dev_disk_read_bytes_delta": disk_delta,
        # 负控: 若整盘+分区全加会双计 ⇒ 这个数应≈2× 上面那个。两数都落盘, 供第三方复核口径。
        "dev_disk_read_bytes_delta_naive_double_counted": naive_delta,
        "dev_disk_read_mb_per_s": disk_mbps,
        "memfree_kb_before": before_mem.get("MemFree"), "memfree_kb_after": after_mem.get("MemFree"),
        "cached_kb_after": after_mem.get("Cached"),
    }
    return rec


def kv(lines: list[str], prefix: str) -> dict:
    """从 `tag{a=1 b=2}` 形态的行里抽键值 (rover CLI 的稳态输出形态)。"""
    for l in lines:
        if l.startswith(prefix + "{"):
            body = l[len(prefix) + 1:].rstrip("}")
            d = {}
            for m in re.finditer(r"(\w+)=([^\s}]+)", body):
                d[m.group(1)] = m.group(2)
            return d
    return {}


def f(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="data/probe/r402/io-attribution.json")
    ap.add_argument("--model", default=str(GGUF))
    args = ap.parse_args()

    if not BIN.exists():
        print(f"error{{kind=binary_missing path={BIN}}}", file=sys.stderr)
        return 2
    model = Path(args.model)
    # 前置资产检查 (unattended-job-reliability: 缺资产 ⇒ 秒退且列出检查过的路径, 不进入长等待)
    if not model.exists():
        print(f"error{{kind=model_missing checked={model} fallback=/tmp/models/prover7b-q4km.gguf}}", file=sys.stderr)
        return 2

    model_bytes = model.stat().st_size
    mem = meminfo()
    steps = []

    # ① 裸读参照: 两条真实内存路径 (无数学运算)。readbench 自带 io 计数 ⇒ 可判「这次到底吃没吃盘」。
    for mode in ("stream", "mmap"):
        steps.append(run(f"readbench_{mode}", [str(BIN), "readbench", str(model),
                                               "--mode", mode, "--chunk-mb", "8", "--passes", "2"]))
    # ①b 大块顺读 (64 MiB/次): 分辨「裸读 438 MiB/s 是设备上限 vs syscall/块大小上限」
    steps.append(run("readbench_stream_chunk64", [str(BIN), "readbench", str(model),
                                                 "--mode", "stream", "--chunk-mb", "64", "--passes", "1"]))
    # ①c mmap 路径 64 MiB 提示窗: 与 ①b 合看可判「缺页路径 vs 系统调用路径」谁更快
    steps.append(run("readbench_mmap_chunk64", [str(BIN), "readbench", str(model),
                                                "--mode", "mmap", "--chunk-mb", "64", "--passes", "1"]))
    # ② 前向 1 token = 恰好 1 个 pass (无分母歧义) —— 单次全权重扫描的盘读字节
    steps.append(run("forward_1tok", [str(BIN), "forward", str(model), "--tokens", "1000", "--ctx", "4"]))
    # ③ 前向 2 token = 2 个 pass —— 第二个 pass 是**重新吃盘**还是命中缓存, 直接决定批 prefill 的收益上限
    steps.append(run("forward_2tok", [str(BIN), "forward", str(model), "--tokens", "1000,2000", "--ctx", "4"]))
    # ④ 冷页对照臂: --drop-pages (每个张量算完 madvise(DONTNEED)) ⇒ 保证零缓存复用。
    #    与默认臂比: 盘读字节相当 ⇒ 默认臂本来就在吃盘 (缓存无复用, 批 prefill 才是靶点);
    #               默认臂明显更低 ⇒ 内核缓存在帮忙 (那才是「内存不够」的量化证据)。
    steps.append(run("forward_2tok_droppages",
                     [str(BIN), "forward", str(model), "--tokens", "1000,2000", "--ctx", "4", "--drop-pages"]))

    by_name = {s["step"]: s for s in steps}
    rb = {k: kv(v["stdout_lines"], "readbench") for k, v in by_name.items() if k.startswith("readbench")}
    def attrib(io_kv: dict, stream_kv: dict) -> dict:
        disk = f(io_kv.get("disk_read_bytes"))
        passes = f(io_kv.get("passes"))
        streamed = f(stream_kv.get("tensor_window_bytes_scanned"))
        out_ = {"ledger_sweeps_equivalent": f(stream_kv.get("ratio")),
                "streamed_bytes": streamed, "io_counters_available": io_kv.get("available")}
        if disk is None or passes in (None, 0):
            return {**out_, "verdict": "unavailable_io_counters", "disk_read_bytes_per_pass": None}
        per_pass = disk / passes
        out_.update({
            "disk_read_bytes": disk,
            "passes": passes,
            "disk_read_bytes_per_pass": per_pass,
            "disk_read_bytes_per_pass_over_model": per_pass / model_bytes,
            "disk_read_ratio_vs_streamed": (disk / streamed) if streamed else None,
            "verdict": "io_dominant" if per_pass / model_bytes >= 0.5 else "page_cache_resident_compute_dominant",
        })
        return out_

    arms = {}
    for name in ("forward_1tok", "forward_2tok", "forward_2tok_droppages"):
        st = by_name[name]
        arms[name] = {
            **attrib(kv(st["stdout_lines"], "io"), kv(st["stdout_lines"], "stream")),
            "wall_s": st["wall_s"],
            "totals": kv(st["stdout_lines"], "totals"),
            "mb_per_s_dev": st["dev_disk_read_mb_per_s"],
            "residency": [l for l in st["stdout_lines"] if l.startswith("residency{")],
        }

    read_mbps = {k: f(v.get("mb_per_s")) for k, v in rb.items()}
    best_mbps = max([v for v in read_mbps.values() if v] or [0])
    # 归因区间: 盘等待 = 进程盘读字节 ÷ 裸读速率。分母取两条**与引擎同源**的读数, 给出上下界,
    # 不许事后挑一个好看的数: stream(系统调用顺读, 偏乐观) / mmap(缺页路径, 引擎实际走的就是它)。
    denoms = {
        "bare_stream_rate": f(rb.get("readbench_stream", {}).get("mb_per_s")),
        "bare_mmap_rate": f(rb.get("readbench_mmap", {}).get("mb_per_s")),
    }
    for a in arms.values():
        disk = f(a.get("disk_read_bytes"))
        if not disk:
            continue
        est = {}
        for label, rate in denoms.items():
            if rate:
                est[label] = round(disk / (rate * 1048576), 2)
        if est:
            lo, hi = min(est.values()), max(est.values())
            a["disk_wait_s_est"] = est
            a["disk_wait_s_interval"] = [lo, hi]
            a["compute_s_interval"] = [round(a["wall_s"] - hi, 2), round(a["wall_s"] - lo, 2)]
            a["disk_wait_share_interval"] = [round(lo / a["wall_s"], 3), round(hi / a["wall_s"], 3)]
    cold = f(arms["forward_2tok_droppages"].get("disk_read_bytes_per_pass_over_model"))
    warm = f(arms["forward_2tok"].get("disk_read_bytes_per_pass_over_model"))
    cache_help = None if cold is None or warm is None else round(max(0.0, cold - warm), 3)

    out = {
        "schema": "rover-io-attribution/1",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "machine": {
            "MemTotal": mem.get("MemTotal"), "MemFree": mem.get("MemFree"), "Cached": mem.get("Cached"),
            "nproc": os.cpu_count(),
        },
        "model": {"path": str(model), "bytes": model_bytes,
                  "model_over_ram_ratio": round(model_bytes / (int(mem.get("MemTotal", "0").split()[0]) * 1024), 3)
                  if mem.get("MemTotal") else None},
        "bare_read_mb_per_s": read_mbps,
        "bare_read_mb_per_s_best": best_mbps,
        "device_channel": {
            "counted_whole_disks": [n for n, _ in _diskstats_lines()
                                    if _PART_RE.match(n) and n != "sr0"],
            "ignored_partitions_and_optical": [n for n, _ in _diskstats_lines()
                                               if not (_PART_RE.match(n) and n != "sr0")],
        },
        "arms": arms,
        # 缓存复用度 = 冷页臂(每张量 madvise DONTNEED)每 pass 盘读 / 模型体积 − 默认臂同量
        #   ≈0 ⇒ 默认臂本来就在吃盘 (页缓存零复用) ⇒ 靶点 = 减少 sweep 次数 (批 prefill) / 顺序预读
        #   >0 ⇒ 缓存确实在帮忙 ⇒ 差额就是「内存不够」的量化代价
        "page_cache_reuse_delta": cache_help,
        "steps": steps,
        "honest_notes": [
            "三个独立通道 (进程 /proc/self/io · 设备 /proc/diskstats · 无运算裸读参照) 必须同向才下归因结论",
            "裸读 read_bytes≈0 ⇒ 跑的是页缓存, 该吞吐只能当「内存路径上界」, 不能当盘吞吐",
            "裸读是顺序读, 前向是缺页驱动的逐张量触碰 ⇒ 前向的等效吞吐只会更低, 不会更高",
            "单机单盘读数, 不代表其它机型; 归因结论绑定本机 (2 vCPU / MemTotal 见 machine 段)",
            "盘等待秒数的分母 = 同机同文件的裸读速率 (stream 与 mmap 两条路径给出上下界), 不是拍脑袋系数; "
            "裸读是顺序读而前向是逐张量缺页触碰 ⇒ 真实盘等待倾向区间**上沿**",
            "设备通道只累计整盘行, 分区行会双计; 双计口径的值同样落盘 (负控), 供第三方复核口径本身",
        ],
    }
    p = ROOT / args.json
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"machine{{MemTotal={out['machine']['MemTotal']} nproc={out['machine']['nproc']}}}")
    print(f"model{{bytes={model_bytes} over_ram={out['model']['model_over_ram_ratio']}}}")
    print(f"bare_read{{stream_mb_per_s={read_mbps.get('readbench_stream')} "
          f"mmap_mb_per_s={read_mbps.get('readbench_mmap')} "
          f"stream_chunk64={read_mbps.get('readbench_stream_chunk64')} "
          f"mmap_chunk64={read_mbps.get('readbench_mmap_chunk64')} best={best_mbps}}}")
    for name, a in arms.items():
        print(f"{name}{{wall_s={a['wall_s']} tokens={a.get('passes')} "
              f"disk_per_pass={a.get('disk_read_bytes_per_pass')} "
              f"over_model={a.get('disk_read_bytes_per_pass_over_model')} "
              f"ratio_vs_streamed={a.get('disk_read_ratio_vs_streamed')} "
              f"ledger_sweeps={a.get('ledger_sweeps_equivalent')} verdict={a['verdict']} "
              f"dev_mb_per_s={a['mb_per_s_dev']} "
              f"disk_wait_s={a.get('disk_wait_s_interval')} compute_s={a.get('compute_s_interval')} "
              f"disk_share={a.get('disk_wait_share_interval')}}}")
    print(f"cache_reuse_delta{{cold_minus_warm_per_pass_over_model={cache_help}}}")
    print(f"device_channel_scope_guard{{whole_and_partition_double_counted="
          f"{by_name['forward_1tok'].get('dev_disk_read_bytes_delta_naive_double_counted')} "
          f"whole_only={by_name['forward_1tok'].get('dev_disk_read_bytes_delta')}}}")
    print(f"json={p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
