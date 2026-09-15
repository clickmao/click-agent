#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R465 ③ 机制演示: 「删掉锁文件」如何破坏 flock 互斥 (两个持有者同时进临界区)。

与 FileLocking.Release() 旧实现同形的最小重演 (确定性, 不依赖竞态时序):
  1. B 打开路径 → inode I1, 拿到 I1 的 flock (B = 老持有者)
  2. 旧 Release 的动作: unlink 该路径 (B 仍持有 I1)
  3. C 打开**同一路径** ⇒ 内核给出**新 inode I2** ⇒ C 拿到 I2 的 flock 成功
  ⇒ B 与 C 同时持有「同名锁」⇒ 临界区互斥失效 (实测表现: 120 段得 119 = 丢一次读改写)
对照组 (R465 新纪律): 不 unlink ⇒ C 的 flock(LOCK_NB) 必须失败 ⇒ 互斥成立。

用法: python3 mech_unlink_race.py   → 打印并落盘 JSON
"""
import fcntl, json, multiprocessing as mp, os, time

D = "/tmp/r465_mech"

def holder(path, flag, hold_s):
    f = open(path, "a+")
    fcntl.flock(f, fcntl.LOCK_EX)
    open(flag, "w").write("held")      # 跨进程信号 (普通 dict 不跨进程)
    time.sleep(hold_s)
    try:
        f.flush()
    finally:
        f.close()

def run(unlink: bool, tag: str):
    os.makedirs(D, exist_ok=True)
    path = os.path.join(D, tag + ".lock")
    flag = os.path.join(D, tag + ".flag")
    for p in (path, flag):
        if os.path.exists(p):
            os.remove(p)
    open(path, "a").close()

    b = mp.Process(target=holder, args=(path, flag, 3.0))
    b.start()
    waited = 0
    while not os.path.exists(flag) and waited < 5000:
        time.sleep(0.02); waited += 20
    if not os.path.exists(flag):
        b.terminate()
        return {"b_holds": False, "c_holds": False, "both_inside": False, "err": "B 未持锁"}

    if unlink:
        os.remove(path)                 # ← 旧 Release 的关键动作

    f2 = open(path, "a+")               # C: 同一路径
    try:
        fcntl.flock(f2, fcntl.LOCK_EX | fcntl.LOCK_NB)
        c_holds = True
    except BlockingIOError:
        c_holds = False
    same_inode = os.stat(path).st_ino == os.stat(os.path.join(D, tag + ".lock")).st_ino
    b.join(6)
    if b.is_alive():
        b.terminate()
    try:
        if c_holds:
            fcntl.flock(f2, fcntl.LOCK_UN)
    except Exception:
        pass
    f2.close()
    return {"b_holds": True, "c_holds": c_holds, "both_inside": bool(c_holds),
            "path_exists_after": os.path.exists(path), "same_inode_after": same_inode}

if __name__ == "__main__":
    unlink_case = run(True, "u")
    keep_case = run(False, "n")
    out = {
        "unlink_race": unlink_case,
        "no_unlink": keep_case,
        "verdict": {
            "旧机理可复现": bool(unlink_case["both_inside"]),
            "新纪律互斥成立": (not keep_case["both_inside"]) and (not unlink_case["b_holds"] ^ True),
        },
        "note": "unlink_race.both_inside=True ⇒ 「删锁文件」放进了第二个持有者; no_unlink.both_inside=False ⇒ 不删则互斥成立",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mech_unlink_race.json"), "w",
         encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
