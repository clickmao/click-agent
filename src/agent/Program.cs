using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using agent;
using agent.core;

namespace agent;

/// <summary>
/// Program - AgentFramework入口
/// </summary>
class Program
{
    static async Task<int> Main(string[] args)
    {
        Console.WriteLine("╔══════════════════════════════════════════════════════════╗");
        Console.WriteLine("║           AgentFramework v1.0.0                         ║");
        Console.WriteLine("║  基于微软MAF和WebReaper的企业级智能Agent框架            ║");
        Console.WriteLine("╚══════════════════════════════════════════════════════════╝");
        Console.WriteLine();
        
        try
        {
            // 构建配置
            // v7.15: 配置类文件转 YAML 分层 (config/base ← env ← modules ← runtime, 规范 §3)。
            // appsettings.json 已弃用: 仍读取一版供迁移期兼容 (存在时打弃用告警), 新配置一律进 config/。
            if (File.Exists(Path.Combine(Directory.GetCurrentDirectory(), "appsettings.json")))
                Console.WriteLine("[Config][WARN] appsettings.json 已弃用 (规范: YAML 唯一格式), 配置请迁移至 config/base/core.yaml");
            var configuration = new ConfigurationBuilder()
                .SetBasePath(Directory.GetCurrentDirectory())
                .AddJsonFile("appsettings.json", optional: true)
                .AddEnvironmentVariables()
                .AddCommandLine(args)
                .Build();

            // 分层配置快照 (base+同名 module 覆盖, agent.config 模块)
            var configSnapshot = new agent.config.ConfigSnapshot();
            
            // 构建服务容器
            var services = new ServiceCollection();
            ConfigureServices(services, configuration, configSnapshot);
            
            var serviceProvider = services.BuildServiceProvider();
            
            // 获取Agent
            var agent = serviceProvider.GetRequiredService<IAgent>();
            
            // 创建上下文
            var context = new AgentContext(serviceProvider)
            {
                SessionId = Guid.NewGuid().ToString(),
                UserId = "console-user",
                TokenBudget = 100000
            };
            
            // 初始化Agent
            await agent.InitializeAsync(context);
            
            Console.WriteLine("✓ Agent初始化完成");
            Console.WriteLine($"✓ 配置: {GetConfigSummary(configuration)}");
            Console.WriteLine();
            
            // 交互式循环
            await InteractiveLoop(agent, context);
            
            return 0;
        }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine($"错误: {ex.Message}");
            Console.ResetColor();
            return 1;
        }
    }
    
    static void ConfigureServices(IServiceCollection services, IConfiguration configuration, agent.config.ConfigSnapshot snapshot)
    {
        // 添加日志
        services.AddLogging(builder =>
        {
            builder.AddConsole();
            builder.SetMinimumLevel(LogLevel.Information);
        });
        
        // 添加配置
        services.AddSingleton(configuration);
        services.AddSingleton(snapshot);
        
        // 添加AgentFramework
        // v7.15: 读值链 = YAML 分层 (base←env←modules←runtime) → 旧 IConfiguration 键 → 代码默认
        services.AddAgentFramework(options =>
        {
            options.AgentName = snapshot.Get("agent", "agent_name",
                configuration["Agent:Name"] ?? "MainAgent");
            options.MaxSubAgents = snapshot.Get("agent", "max_sub_agents",
                int.TryParse(configuration["Agent:MaxSubAgents"], out var msa) ? msa : 4);
            options.EnableMAF = bool.TryParse(configuration["Agent:EnableMAF"], out var maf) && maf;
            options.EnableSearchCache = snapshot.Get("agent", "enable_search_cache",
                bool.TryParse(configuration["Agent:EnableSearchCache"], out var sc) ? sc : true);
            options.SummarizeAfterTurns = snapshot.Get("agent", "summarize_after_turns",
                int.TryParse(configuration["Agent:SummarizeAfterTurns"], out var sat) ? sat : 10);
            options.DataStoragePath = configuration["Storage:Path"] ?? "./data";
        });
        
        // ✅ 添加 OpenAI LLM Caller (v7.15: Key 不落配置, 只存环境变量名 — openai.api_key_env)
// 模型队列 DI 见 extensions/ServiceCollectionExtensions.cs (v7.15 单一事实源)

        
        // ✅ HTTP Client 配置
        services.AddHttpClient("openai", client =>
        {
            client.Timeout = TimeSpan.FromSeconds(60);
            client.DefaultRequestHeaders.Add("User-Agent", "AgentFramework/1.0");
        });
        
        // ✅ 配置文件热重载（开发时有用）
        services.Configure<AgentFrameworkOptions>(options =>
        {
            configuration.GetSection("Agent").Bind(options);
        });
    }
    
    static string GetConfigSummary(IConfiguration configuration)
    {
        var parts = new List<string>();
        
        var agentName = configuration["Agent:Name"];
        if (!string.IsNullOrEmpty(agentName))
            parts.Add($"Name={agentName}");
        
        var openAiKey = configuration["OpenAI:ApiKey"];
        parts.Add($"OpenAI={(string.IsNullOrEmpty(openAiKey) ? "❌ Not configured" : "✅ Configured")}");
        
        var storagePath = configuration["Storage:Path"];
        if (!string.IsNullOrEmpty(storagePath))
            parts.Add($"Storage={storagePath}");
        
        return string.Join(", ", parts);
    }
    
    static async Task InteractiveLoop(IAgent agent, IAgentContext context)
    {
        Console.WriteLine("输入消息与Agent对话，输入 'quit' 或 'exit' 退出");
        Console.WriteLine("输入 'help' 获取帮助");
        Console.WriteLine();
        
        while (true)
        {
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.Write("> ");
            Console.ResetColor();
            
            var input = Console.ReadLine()?.Trim();
            
            if (string.IsNullOrEmpty(input))
                continue;
            
            if (input.Equals("quit", StringComparison.OrdinalIgnoreCase) ||
                input.Equals("exit", StringComparison.OrdinalIgnoreCase))
            {
                Console.WriteLine("再见!");
                break;
            }
            
            if (input.Equals("help", StringComparison.OrdinalIgnoreCase))
            {
                ShowHelp();
                continue;
            }
            
            if (input.Equals("clear", StringComparison.OrdinalIgnoreCase))
            {
                Console.Clear();
                continue;
            }
            
            // 处理消息
            var message = new Message
            {
                SessionId = context.SessionId,
                SenderId = context.UserId,
                Content = input,
                Role = MessageRole.User
            };
            
            var response = await agent.ProcessAsync(message);
            
            // 显示响应
            Console.ForegroundColor = response.Success ? ConsoleColor.Green : ConsoleColor.Red;
            Console.WriteLine($"Agent: {response.Content}");
            Console.ResetColor();
            
            if (!string.IsNullOrEmpty(response.Error))
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine($"Error: {response.Error}");
                Console.ResetColor();
            }
            
            Console.WriteLine();
        }
        
        // 关闭Agent
        await agent.ShutdownAsync();
    }
    
    static void ShowHelp()
    {
        Console.WriteLine("可用命令:");
        Console.WriteLine("  quit/exit  - 退出程序");
        Console.WriteLine("  help       - 显示帮助");
        Console.WriteLine("  clear      - 清屏");
        Console.WriteLine();
        Console.WriteLine("直接输入消息与Agent对话");
    }
}
