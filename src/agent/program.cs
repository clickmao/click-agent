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
            var configuration = new ConfigurationBuilder()
                .SetBasePath(Directory.GetCurrentDirectory())
                .AddJsonFile("appsettings.json", optional: true)
                .AddEnvironmentVariables()
                .AddCommandLine(args)
                .Build();
            
            // 构建服务容器
            var services = new ServiceCollection();
            ConfigureServices(services, configuration);
            
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
    
    static void ConfigureServices(IServiceCollection services, IConfiguration configuration)
    {
        // 添加日志
        services.AddLogging(builder =>
        {
            builder.AddConsole();
            builder.SetMinimumLevel(LogLevel.Information);
        });
        
        // 添加配置
        services.AddSingleton(configuration);
        
        // 添加AgentFramework
        services.AddAgentFramework(options =>
        {
            options.AgentName = configuration["Agent:Name"] ?? "MainAgent";
            options.MaxSubAgents = int.Parse(configuration["Agent:MaxSubAgents"] ?? "4");
            options.EnableMAF = bool.Parse(configuration["Agent:EnableMAF"] ?? "false");
            options.EnableSearchCache = bool.Parse(configuration["Agent:EnableSearchCache"] ?? "true");
            options.SummarizeAfterTurns = int.Parse(configuration["Agent:SummarizeAfterTurns"] ?? "10");
            options.DataStoragePath = configuration["Storage:Path"] ?? "./data";
        });
        
        // ✅ 添加 OpenAI LLM Caller（需要配置 API Key）
        var openAiKey = configuration["OpenAI:ApiKey"];
        if (!string.IsNullOrEmpty(openAiKey))
        {
            services.AddSingleton<ILLMCaller>(sp =>
            {
                var httpClientFactory = sp.GetRequiredService<IHttpClientFactory>();
                return new OpenAILLMCaller(
                    httpClientFactory.CreateClient("openai"),
                    openAiKey,
                    configuration["OpenAI:Model"] ?? "gpt-4");
            });
        }
        else
        {
            // 未配置 API Key: 注册 fallback，保证 DI 图完整、程序可启动
            services.AddSingleton<ILLMCaller, NullLLMCaller>();
            Console.WriteLine("[WARN] OpenAI:ApiKey 未配置, LLM 调用将返回错误提示 (NullLLMCaller)");
        }
        
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
