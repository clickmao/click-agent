using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace agent.staging;


/// <summary>v0.17.1 (R335, 用户钦定): 离线变更批次中的单个文件项 — 完整快照存 staging (git index 简化版)。
/// Path=真实目标; BaselineSha=批次创建时目标文件哈希 (apply 时比对 — 用户已改/正编辑 → 冲突拒绝, 绝不覆盖);
/// ContentFile=staging 内完整新内容文件 (不占用真实地址, 编辑器零感知); Applied=逐项应用状态 (批次可 partial)。</summary>
public sealed class StagedItem
{
    public string Path { get; set; } = "";
    public string BaselineSha { get; set; } = "";
    public string ContentFile { get; set; } = "";
    public bool Applied { get; set; }
}
