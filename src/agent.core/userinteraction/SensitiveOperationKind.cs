namespace agent.userinteraction;


/// <summary>敏感操作类型 flag</summary>
public enum SensitiveOperationKind
{
    /// <summary>创建文件/目录</summary>
    CreateFile,

    /// <summary>删除文件/目录 (不可逆)</summary>
    DeleteFile,

    /// <summary>修改/覆盖既有文件</summary>
    ModifyFile,

    /// <summary>执行外部程序/进程</summary>
    ExecuteProcess,

    /// <summary>网络请求到非白名单地址</summary>
    ExternalNetwork,

    /// <summary>写入系统配置 (env/全局配置)</summary>
    SystemConfig,
}
