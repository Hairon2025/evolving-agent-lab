# Experiment Status

## 项目目标

研究基于 OpenAI Agents SDK 的自进化 Agent。

## 当前实验对象

Triage Agent 的首次分流能力。

## 已完成

- 建立 development 和 holdout 评测集
- 保存 v0 基线
- 创建 TRIAGE_INSTRUCTIONS_V1
- Agent 工厂支持 Prompt 注入
- 评估脚本支持 v0/v1 对照

## 第一轮结果

| Prompt | Development | Holdout |
|---|---:|---:|
| v0 | 10/11 | 4/5 |
| v1 | 11/11 | 5/5 |

## 当前结论

v1 优于 v0，具备晋升资格。

## 下一步

1. 增加 ACTIVE_TRIAGE_INSTRUCTIONS
2. 将 v1 晋升为默认版本
3. 保存版本晋升记录
4. 设计 Reviewer 和 Prompt Optimizer
5. 将人工迭代逐步自动化