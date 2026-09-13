using agent.gpu.cli;

// 进程边界: 仅此处的 Console 用法是被允许的 (产品逻辑一律走注入的 TextWriter)。
return GpuCli.Run(args, Console.Out, Console.Error);
