import argparse
import asyncio
import json
from pathlib import Path

from agents import HandoffOutputItem, Runner

from evolving_agent.agent_runtime.agents.prompts import (
    TRIAGE_INSTRUCTIONS,
    TRIAGE_INSTRUCTIONS_V1,
)

from evolving_agent.agent_runtime.agents.factory import build_agent_registry
from evolving_agent.agent_runtime.context import AirlineAgentContext

# 项目根目录：__file__ 是当前脚本路径，parents[1] 上跳两级到项目根
# （parents[0] 是脚本所在目录，parents[1] 再往上一层）
ROOT = Path(__file__).resolve().parents[1]

PROMPT_VERSIONS = {
    "v0": TRIAGE_INSTRUCTIONS,
    "v1": TRIAGE_INSTRUCTIONS_V1,
}

async def evaluate_case(
        case: dict,
        triage_instructions: str
    ) -> dict:
    """
    评估单条测试案例，返回结果字典。

    每条案例都会重新构建 Agent 和 context，确保案例之间完全隔离。
    """

    # 每条案例独立运行，避免会话状态互相影响。
    registry = build_agent_registry(triage_instructions = triage_instructions)
    context = AirlineAgentContext()

    try:
        # 从 Triage Agent 作为起点运行，最多 8 轮（防止死循环）
        result = await Runner.run(
            registry.triage,
            case["input"],
            context=context,
            max_turns=8,
        )

        # 找到"第一次从 Triage Agent 发出的转接"，记录目标 Agent 名
        # next(生成器, None) 的写法：找到第一个就返回，没有就返回 None
        first_handoff = next(
            (
                item.target_agent.name
                for item in result.new_items
                if isinstance(item, HandoffOutputItem)
                # 只关心从 Triage 出发的转接，忽略后续 Agent 之间的转接
                and item.source_agent.name == "Triage Agent"
            ),
            None,
        )

        return {
            "id": case["id"],
            "expected": case["expected_first_handoff"],
            "actual": first_handoff,
            # 通过判定：实际首次转接目标 == 期望值
            "passed": first_handoff == case["expected_first_handoff"],
            "error": None,
        }
    except Exception as exc:
        # 运行异常时首次分流暂时无法判定，但记录异常信息便于排查
        return {
            "id": case["id"],
            "expected": case["expected_first_handoff"],
            "actual": None,
            "passed": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

async def main() -> None:
    # 命令行参数：必须指定 --split，值只能是 development 或 holdout
    # development：开发集，可以反复调 prompt 拟合
    # holdout：留出集，调 prompt 时不看，用来检测是否过拟合
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split",
        choices=("development", "holdout"),
        required=True,
    )
    parser.add_argument(
        "--prompt-version",
        choices=tuple(PROMPT_VERSIONS),
        required=True,
        help="选择要评估的 Triage Prompt 版本",
    )
    args = parser.parse_args()
    triage_instructions = PROMPT_VERSIONS[args.prompt_version]

    # 读取所有测试案例
    cases = json.loads(
        (ROOT / "evals" / "cases.json").read_text(encoding="utf-8")
    )
    # 只筛选出当前 split 的案例
    selected = [
        case for case in cases if case["split"] == args.split
    ]

    # 如果这个 split 下没有案例，直接报错退出
    if not selected:
        raise ValueError(f"没有找到 {args.split} 案例")

    results = []
    for case in selected:
        # 逐条评估（串行，方便看输出顺序和排查）
        result = await evaluate_case(
            case,
            triage_instructions=triage_instructions,
        )
        results.append(result)

        # 打印单条结果
        if result["passed"] is None:
            label = "ERROR"
        elif result["passed"]:
            label = "PASS"
        else:
            label = "FAIL"

        print(
            f"{label} {result['id']}: "
            f"expected={result['expected']}, "
            f"actual={result['actual']}"
        )
        # 如果运行报错，额外打印异常信息
        if result["error"]:
            print(f"  error: {result['error']}")

    # 汇总通过数
    passed = sum(item["passed"] is True for item in results)
    failed = sum(item["passed"] is False for item in results)
    unknown = sum(item["passed"] is None for item in results)

    report = {
        "prompt_version": args.prompt_version,
        "split": args.split,
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "total": len(results),
        "cases": results,
    }

    # 把报告写进 eval_results/baseline_<split>.json
    # 文件名带 "baseline" 是惯例：这次跑出来的结果作为后续对比的基线
    output_dir = ROOT / "eval_results"
    output_dir.mkdir(exist_ok=True)
    output_file = (
        output_dir
        / f"{args.prompt_version}_{args.split}.json"
    )
    output_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 最后打印汇总
    print(f"报告：{output_file}")
    print(
        f"\n分流结果：通过 {passed}，失败 {failed}，"
        f"无法判定 {unknown}；总计 {len(results)}"
    )


if __name__ == "__main__":
    asyncio.run(main())

