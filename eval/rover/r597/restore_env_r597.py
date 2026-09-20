#!/usr/bin/env python3
"""R597 · 主线器具环境**持久化恢复**（零产品源码改动 / 零新夹具语义）。

背景（实测，非推断）: 主线对照 harness 的两个前置件原先**只存在于 /tmp**
  · 被测件  /tmp/pub_r556/agenthost/agenthost        (R556 交付件, sha 320d0eb1…)
  · 夹具配置 /tmp/r455_env/agent/cfg                  (r455 期冻结的 config 快照)
两个路径在 R597 起手时**均已不存在**（`ls` 缺失；同目录下 r562..r571 运行目录仍在
⇒ 年龄策略可排除: /usr/lib/tmpfiles.d/tmp.conf = `D /tmp 1777 root root 30d`）。
⇒ 主线对照轮结构性无法起臂（runner 前置闸 fail-closed 会 exit 3）。

本器具做三件事（均为**恢复**，不新增语义）:
  1. 等价性证明: 从 6 份**独立归档运行副本**(r563/r565-attempt1/r566/r567/r570/r571 的
     `agent-cfg`) 取 cfg, 端口归一化后断言逐字节相等 ⇒ 丢失的源件**唯一可重建**。
  2. 落盘到**非 /tmp 稳定路径** `$HOME/.agentframework/harness/agent/cfg`（端口哨兵 48600,
     与既有 runner 的 `s/486[0-9][0-9]/$PORT/` 替换契约一致）。
  3. 落盘读数 `readings-restore-r597.json`（源 sha / 派生 sha / 等价副本数 / 负控）。

负控（判别力自证, 缺则本器具空心）: 对副本施加 1 字节扰动后归一化 sha **必须**不同
（证明 sha 判据不是恒真门）。任一项失败 ⇒ rc=2 fail-closed, 不落 cfg。
"""
import glob
import hashlib
import io
import json
import os
import re
import sys

ARCH_GLOB = "/tmp/r5*/agent-cfg"
FILES = ["base/models.yaml", "base/core.yaml", "base/skill.yaml"]
DEST = os.path.expanduser("~/.agentframework/harness/agent/cfg")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "readings-restore-r597.json")
PORT_SENTINEL = 48600


def norm(b: bytes) -> bytes:
    return re.sub(rb"127\.0\.0\.1:\d{4,5}", b"127.0.0.1:PORT", b)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    rec = {"instrument": "restore_env_r597", "dest": DEST, "port_sentinel": PORT_SENTINEL}
    ok, why = True, []

    copies = sorted(glob.glob(ARCH_GLOB))
    rec["archived_copies"] = [c.rsplit("/", 2)[-2] for c in copies]
    if len(copies) < 2:
        print(json.dumps({"rc": 2, "why": "insufficient_archived_copies", "n": len(copies)}))
        return 2

    per_file = {}
    for f in FILES:
        shas = {}
        for c in copies:
            p = os.path.join(c, f)
            if os.path.exists(p):
                shas.setdefault(sha(norm(io.open(p, "rb").read())), []).append(c.rsplit("/", 2)[-2])
        per_file[f] = shas
        if len(shas) != 1:
            ok = False
            why.append(f"equivalence_failed:{f}:{sorted(shas)}")
    rec["normalized_sha_by_file"] = {f: {k: sorted(v) for k, v in d.items()} for f, d in per_file.items()}
    rec["equivalence_ok"] = ok

    # 负控: 扰动 1 字节 ⇒ sha 必变 (否则 sha 判据是恒真门)
    probe_p = os.path.join(copies[-1], FILES[0])
    base = io.open(probe_p, "rb").read()
    seed = norm(base)
    perturbed = norm(base[:-2] + (b"X" if base[-2:-1] != b"X" else b"Y") + base[-1:])
    nc_distinct = sha(seed) != sha(perturbed)
    rec["negative_control_sha_has_teeth"] = nc_distinct
    if not nc_distinct:
        ok = False
        why.append("negative_control_hollow")

    if not ok:
        rec.update({"rc": 2, "why": why})
        json.dump(rec, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"rc": 2, "why": why}, ensure_ascii=False))
        return 2

    # 落盘稳定 cfg (端口哨兵)
    os.makedirs(os.path.join(DEST, "base"), exist_ok=True)
    written = {}
    for f in FILES:
        src = os.path.join(copies[-1], f)
        txt = io.open(src, "rb").read()
        txt = re.sub(rb"127\.0\.0\.1:\d{4,5}", f"127.0.0.1:{PORT_SENTINEL}".encode(), txt)
        io.open(os.path.join(DEST, f), "wb").write(txt)
        written[f] = sha(txt)
    rec["written_sha"] = written
    # 回读校验 (不采信写入返回)
    rb = {f: sha(io.open(os.path.join(DEST, f), "rb").read()) for f in FILES}
    rec["readback_equal"] = rb == written
    if rb != written:
        rec.update({"rc": 2, "why": ["readback_mismatch"]})
        json.dump(rec, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"rc": 2, "why": ["readback_mismatch"]}))
        return 2

    rec.update({"rc": 0, "why": []})
    json.dump(rec, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": 0, "dest": DEST, "copies": len(copies),
                      "normalized_sha": sorted({k for d in per_file.values() for k in d}),
                      "readback_equal": True, "nc_has_teeth": nc_distinct}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
