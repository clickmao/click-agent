#!/usr/bin/env python3
"""R423 形态闸 V0 — 被测二进制必须是 AOT 原生（fail-closed）。

判据（预注册 §3 V0）: `env -i <bin> --version` 必须打印 CLI 横幅。
  · 理由: 原生 AOT 不需要 dotnet 运行时 ⇒ 清空环境仍能启动;
          IL apphost 壳在无运行时 ⇒ 「You must install .NET to run this application.」
  · 成对负控: 对 IL apphost 路径同命令必须**拒绝执行**, 否则该判据无判别力（不许只测正控）。
用法: python3 prov_check.py [--json out.json] <bin_under_test> [negctl_bin ...]
退出码: 0 = 形态闸通过（被测 AOT 且负控确实失败）; 3 = 形态闸红。
"""
import hashlib
import json
import os
import subprocess
import sys

NEG_DEFAULT = "src/agent.host/bin/Release/net10.0/agenthost"  # 历史 harness 路径 = IL apphost
ROOT = "/home/agentuser/AgentFramework"


def run_bare(bin_path, timeout=30):
    """env -i ⇒ 无 DOTNET_ROOT / 无 PATH 注入; 返回 (rc, out)。"""
    try:
        # R429 器具修正 (承重): `--version` 只打印横幅, 之后**进入交互 REPL 等 stdin**
        # ⇒ 不给 stdin 兜底会被自己的 timeout 杀掉 (bare_rc=-9) 而把 AOT 原生误判成不合格 (假红)。
        # 兜底 = 立刻喂 "/exit" (R405 教训: 交互式 CLI 关不掉 ⇒ printf '/exit\n' 兜底)。
        p = subprocess.run(["env", "-i", os.path.abspath(bin_path), "--version"],
                           capture_output=True, text=True, timeout=timeout,
                           input="/exit\n",
                           cwd=os.path.dirname(os.path.abspath(bin_path)) or ".")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, "<timeout>"
    except Exception as e:  # noqa: BLE001
        return -1, f"<exec_error {e}>"


def probe(bin_path):
    ap = os.path.abspath(bin_path)
    d = {"path": ap, "exists": os.path.exists(ap)}
    if not d["exists"]:
        return d
    b = open(ap, "rb").read()
    d["bytes"] = len(b)
    d["sha256"] = hashlib.sha256(b).hexdigest()
    rc, out = run_bare(ap)
    d["bare_rc"] = rc
    d["bare_stdout_head"] = out.strip().splitlines()[0] if out.strip() else ""
    d["needs_runtime"] = "You must install .NET" in out
    d["native_ok"] = ("AgentFramework CLI" in out) and not d["needs_runtime"]
    try:
        d["file"] = subprocess.run(["file", "-b", ap], capture_output=True, text=True,
                                   timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        d["file"] = ""
    return d


def main():
    args = sys.argv[1:]
    out_json = None
    if args and args[0] == "--json":
        out_json = args[1]
        args = args[2:]
    if not args:
        print("用法: prov_check.py [--json out.json] <bin> [negctl ...]")
        return 2
    ut = args[0]
    negs = args[1:] or [os.path.join(ROOT, NEG_DEFAULT)]

    print("=== V0 形态闸（env -i 自证; 无运行时可用）===")
    u = probe(ut)
    print(json.dumps(u, ensure_ascii=False, indent=1))
    neg = [probe(n) for n in negs]
    for n in neg:
        print(json.dumps(n, ensure_ascii=False, indent=1))

    pos_ok = bool(u.get("native_ok"))
    neg_ok = all(n.get("exists") and (n.get("needs_runtime") or not n.get("native_ok")) for n in neg)
    print(f"\nV0-a 被测为 AOT 原生 : {pos_ok}   (native_ok={u.get('native_ok')}, bytes={u.get('bytes')})")
    print(f"V0-b 负控确有判别力 : {neg_ok}   (IL apphost 在 env -i 下拒绝执行)")
    verdict = pos_ok and neg_ok
    print(f"V0 形态闸: {'PASS' if verdict else 'RED（不得据该二进制出判据）'}")
    if out_json:
        json.dump({"under_test": u, "negative_controls": neg,
                   "pos_ok": pos_ok, "neg_ok": neg_ok, "verdict": "PASS" if verdict else "RED"},
                  open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[written] {out_json}")
    return 0 if verdict else 3


if __name__ == "__main__":
    sys.exit(main())
