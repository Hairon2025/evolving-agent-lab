from dataclasses import dataclass

from agents import Agent, handoff

# 从钩子模块导入：转接到座位预订 Agent 时触发的副作用函数
from evolving_agent.agent_runtime.agents.hooks import (
    on_seat_booking_handoff,
)

# 从提示词模块导入：三个 Agent 各自的 instructions，集中管理便于维护
from evolving_agent.agent_runtime.agents.prompts import (
    FAQ_INSTRUCTIONS,
    SEAT_BOOKING_INSTRUCTIONS,
    TRIAGE_INSTRUCTIONS,
)
from evolving_agent.agent_runtime.tools.booking import update_seat
from evolving_agent.agent_runtime.tools.faq import faq_lookup_tool
from evolving_agent.agent_runtime.context import AirlineAgentContext
from evolving_agent.shared.config import MODEL_NAME


@dataclass(frozen=True)
class AgentRegistry:
    """
    三个 Agent 的聚合容器。
    """
    triage: Agent[AirlineAgentContext]
    faq: Agent[AirlineAgentContext]
    seat_booking: Agent[AirlineAgentContext]


def build_agent_registry() -> AgentRegistry:
    """
    构建并返回三个 Agent 的注册表。

    拆成工厂函数而非模块级变量，好处：
    - 可以延迟构建（导入时不会立刻创建 Agent）
    - 便于测试（每次调用返回一组全新实例）
    - 便于将来注入依赖（比如传入不同的工具或模型）
    """

    # ---------- 1. FAQ Agent：回答常见问题 ----------
    faq_agent = Agent[AirlineAgentContext](
        name="FAQ Agent",
        model=MODEL_NAME,                           # 从 config 统一取模型名
        handoff_description=(
            "Answers airline FAQ and policy questions."
            # 该描述会在转接时提供给上游 Agent 判断，是否要把请求交给它
        ),
        instructions=FAQ_INSTRUCTIONS,              # prompt 从 prompts 模块导入
        tools=[faq_lookup_tool],                    # 只挂 FAQ 查询工具
    )

    # ---------- 2. Seat Booking Agent：处理座位变更 ----------
    seat_booking_agent = Agent[AirlineAgentContext](
        name="Seat Booking Agent",
        model=MODEL_NAME,
        handoff_description=(
            "Handles booking lookup and seat changes."
        ),
        instructions=SEAT_BOOKING_INSTRUCTIONS,
        tools=[update_seat],                        # 只挂座位更新工具
    )

    # ---------- 3. Triage Agent：入口分诊，决定把请求转给谁 ----------
    triage_agent = Agent[AirlineAgentContext](
        name="Triage Agent",
        model=MODEL_NAME,
        handoff_description=(
            "Routes customer requests to the appropriate agent."
        ),
        instructions=TRIAGE_INSTRUCTIONS,
        # handoffs 是分诊 Agent 的出边：根据用户意图转给下游 Agent
        handoffs=[
            # 转接到 FAQ Agent
            handoff(
                agent=faq_agent,
                tool_name_override="transfer_to_faq_agent",
            ),
            # 转接到 Seat Booking Agent
            handoff(
                agent=seat_booking_agent,
                on_handoff=on_seat_booking_handoff,
                tool_name_override="transfer_to_seat_booking_agent",
            ),
        ],
    )

    # ---------- 4. 添加回边：让下游 Agent 能转回分诊 ----------
    # 形成闭环：Triage -> FAQ / SeatBooking -> Triage
    # 否则 FAQ 遇到不会的问题就无法交回分诊处理
    faq_agent.handoffs.append(
        handoff(
            agent=triage_agent,
            tool_name_override="transfer_to_triage_agent",
        )
    )

    seat_booking_agent.handoffs.append(
        handoff(
            agent=triage_agent,
            tool_name_override="transfer_to_triage_agent",
        )
    )

    # ---------- 5. 打包返回 ----------
    return AgentRegistry(
        triage=triage_agent,
        faq=faq_agent,
        seat_booking=seat_booking_agent,
    )