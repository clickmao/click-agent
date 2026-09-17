using System;
using System.IO;
using System.Linq;

namespace agent.skills;


/// <summary>
/// 解析出的 python 解释器 + **来源标签** (T4 决策 v0.22.0 exp9 §11)。
/// 来源必须可对账: "产物跑过了" 这句话只有在知道"跑在哪个解释器上"时才成立。
/// </summary>
public sealed record PythonInterpreter(string Exe, string Source);
