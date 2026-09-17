using System.Net.Http.Json;
using System.Text.Json;
using agent.modelqueue;   // R430: LocalInputFingerprint (共享层; 不引入反向依赖)

namespace agent.llamacpp;


/// <summary>生成口径。Reconciliation=关前缀缓存(可复现优先, 对账用); Session=开前缀缓存(K2b 优先, 生产用)。</summary>
public enum CompletionReuse
{
    Reconciliation,
    Session,
}
