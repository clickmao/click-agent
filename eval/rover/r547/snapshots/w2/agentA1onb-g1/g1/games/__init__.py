"""games: 多款经典博弈/演化游戏的纯函数求解包。

子模块（各自导出 solve(text: str) -> str）:
  - life      康威生命游戏, k 代演化
  - sub       取石子子游戏, 必胜/必败判定
  - nim       多堆 Nim, 输出必胜着法
  - wythoff   Wythoff 博弈, 输出必败判定/字典序最小必胜着法

CLI: python3 -m games <life|sub|nim|wythoff>
"""
