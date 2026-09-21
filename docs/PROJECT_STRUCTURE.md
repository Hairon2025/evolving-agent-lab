# 项目结构与模块边界

本文以当前仓库为准，区分**已实现**与**计划扩展**。目录是为了表达职责；代码量少时优先保持模块简单，不为了架构图预建空目录。

## 当前结构

```text
evolving-agent-lab/
├── README.md
├── docs/
│   ├── PROJECT_STRUCTURE.md
│   └── CODING_STANDARDS.md
├── src/
│   └── evolving_agent/
│       ├── main.py                         # 当前 CLI 入口及对话循环
│       ├── auto_model.py                   # 示例自动输入辅助函数
│       ├── agent_runtime/
│       │   ├── context.py                  # 当前会话的 Agent Context
│       │   ├── agents/
│       │   │   ├── factory.py              # 构造三类 Agent 和 Handoff 图
│       │   │   ├── hooks.py                # Handoff 回调
│       │   │   └── prompts.py              # Agent instructions
│       │   └── tools/
│       │       ├── booking.py              # 当前座位变更演示工具
│       │       └── faq.py                  # 当前 FAQ 演示工具
│       ├── models/
│       │   └── booking/
│       │       ├── entities.py             # Booking 业务数据模型
│       │       └── repository.py           # 空文件；尚无仓库实现
│       ├── shared/
│       │   └── config.py                   # 当前模型客户端与模型名配置
│       ├── interfaces/cli/main.py         # 空文件；入口尚未迁移
│       └── infrastructure/                # 预留目录；尚无实现
├── tests/                                  # 预留目录；尚无测试
└── deploy/                                 # 预留目录；尚无部署配置
```

`evolution/` 目录也已预留，但目前没有评估或自进化代码。上面的树只列出有实际职责的文件与重要的预留目录，省略 `__init__.py` 和缓存文件。

## 当前调用链

```text
用户输入
  → main.py 的对话循环
  → Triage Agent
  → FAQ Agent 或 Seat Booking Agent
  → 对应 Tool
  → Tool 结果
  → Agent 回复
```

`main.py` 保存本次会话的输入历史、当前 Agent 和 `AirlineAgentContext`。`factory.py` 一次性构建 Agent 与 Handoff 的连接关系；`prompts.py` 提供各 Agent 的指令；Tool 是模型接触业务能力的入口。

当前的 `Booking` 模型**尚未参与座位变更流程**。`hooks.py` 会生成演示用随机航班号，`tools/booking.py` 仅修改会话 Context，没有验证确认号、座位库存或更新预订。因此工具的成功文本不能视为真实业务成功。这是接入预订数据前需要优先修复的限制。

## 模块边界

| 模块 | 负责 | 不负责 |
| --- | --- | --- |
| `agent_runtime/agents/` | Agent 职责、指令、Handoff 图及回调 | 直接读写数据库、保存业务事实 |
| `agent_runtime/tools/` | 将模型参数转成受控业务调用，并返回明确结果 | 自己充当数据库或绕过校验承诺成功 |
| `agent_runtime/context.py` | 本次会话中已验证的标识与工作状态 | 充当预订或座位库存的事实来源 |
| `models/booking/` | 当前预订业务模型；以后可在这里增加少量业务规则 | 数据库连接、SQL、Agent SDK 运行逻辑 |
| `shared/config.py` | 读取配置和组装模型客户端 | 散落的业务判断和密钥常量 |
| `infrastructure/` | 未来跨模块复用的技术设施，如数据库连接 | 预订专属业务规则 |
| `interfaces/` | CLI 或未来的 HTTP 请求/响应适配 | 业务规则与持久化细节 |

这里的“模型”有不同含义：`Booking` 是业务模型，`AirlineAgentContext` 是会话模型；未来若接入 SQLAlchemy，数据库表映射是 ORM 模型，应放在持久化适配代码中。不要因为它们都叫 model 就放进同一个文件。

## 数据库接入时的目标调用链

```text
Agent → Tool → 预订业务操作 → BookingRepository 接口
                                      ↓
                         数据库实现 → 数据库连接 → PostgreSQL
```

按实际需要渐进增加：

1. 先定义预订查询、空座查询和换座的行为与错误结果，用内存实现和测试建立基线。
2. Tool 只调用这些业务操作；Handoff 不再产生随机业务数据，只有业务操作成功才回复成功。
3. 接数据库时，在跨模块 `infrastructure/` 中管理连接和事务；在预订模块的适配代码中实现预订专属查询与保存。
4. 把运行轨迹、工具结果和 Prompt 版本保存下来，之后才加入离线评估与候选版本比较。

当前不要求创建 `domain/` 子目录。`models/booking/` 随业务增长后可以再按实体、规则、仓库接口与适配器细分。Repository 接口描述“需要什么操作”，数据库实现负责“如何执行 SQL”；两者都不应由 Agent 直接实现。

## 扩展目录的时机

- `interfaces/cli/`：当 `main.py` 的输入输出逻辑与 Runner 分离时启用。
- `infrastructure/database/`：确定数据库选型并需要共享连接、事务管理时启用。
- 预订模块的 `adapters/`：出现具体的内存或 SQLAlchemy Repository 实现时启用。
- `evolution/`：已有固定评估案例、可记录轨迹和成功判据后启用。
- `deploy/`：确定运行方式后再加入容器和部署配置。

新增目录前先说明它解决了什么现有问题；一个小模块能清晰承载职责时，不必再拆文件夹。
