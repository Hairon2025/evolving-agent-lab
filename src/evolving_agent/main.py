from __future__ import annotations as _annotations

import asyncio
import random
import uuid

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    handoff,
    trace,
)

from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from evolving_agent.auto_model import input_with_fallback, is_auto_mode
### CONTEXT
from evolving_agent.models.simple_model import AirlineAgentContext
from evolving_agent.shared.config import MODEL_NAME

### TOOLS
from evolving_agent.agent_runtime.tools.booking import update_seat
from evolving_agent.agent_runtime.tools.faq import faq_lookup_tool

### HOOKS


async def on_seat_booking_handoff(context: RunContextWrapper[AirlineAgentContext]) -> None:
    """
    在座位预订智能体接管时设置航班号。
    """
    flight_number = f"FLT-{random.randint(100, 999)}"
    context.context.flight_number = flight_number

### AGENTS

faq_agent = Agent[AirlineAgentContext](
    name="FAQ Agent",
    model=MODEL_NAME,
    handoff_description="A helpful agent that can answer questions about the airline.",
    # handoff_description="一个可以回答航空公司相关问题的有帮助的智能体。",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the faq lookup tool to answer the question. Do not rely on your own knowledge.
    3. If you cannot answer the question, transfer back to the triage agent.""",
    # instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    # 你是一个FAQ智能体。如果你正在与客户交谈，你可能是从分诊智能体转接过来的。
    # 使用以下流程来支持客户。
    # # 流程
    # 1. 识别客户最后提出的问题。
    # 2. 使用FAQ查询工具来回答问题。不要依赖你自己的知识。
    # 3. 如果你无法回答问题，转回分诊智能体。""",
    tools=[faq_lookup_tool],
)

seat_booking_agent = Agent[AirlineAgentContext](
    name="Seat Booking Agent",
    model=MODEL_NAME,
    handoff_description="A helpful agent that can update a seat on a flight.",
    # handoff_description="一个可以更新航班座位的有帮助的智能体。",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a seat booking agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Ask for their confirmation number.
    2. Ask the customer what their desired seat number is.
    3. Use the update seat tool to update the seat on the flight.
    If the customer asks a question that is not related to the routine, transfer back to the triage agent. """,
    # instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    # 你是一个座位预订智能体。如果你正在与客户交谈，你可能是从分诊智能体转接过来的。
    # 使用以下流程来支持客户。
    # # 流程
    # 1. 询问他们的确认号码。
    # 2. 询问客户他们想要的座位号。
    # 3. 使用更新座位工具来更新航班上的座位。
    # 如果客户提出与流程无关的问题，请转回分诊智能体。""",
    tools=[update_seat],
)

triage_agent = Agent[AirlineAgentContext](
    name="Triage Agent",
    model=MODEL_NAME,
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    # handoff_description="一个分诊智能体，可以将客户的请求委派给合适的智能体。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    # instructions=(
    #     f"{RECOMMENDED_PROMPT_PREFIX} "
    #     "你是一个有帮助的分诊智能体。你可以使用你的工具将问题委派给其他合适的智能体。"
    # ),

    handoffs=[
        handoff(agent=faq_agent, tool_name_override="transfer_to_faq_agent"),
        handoff(
            agent=seat_booking_agent,
            on_handoff=on_seat_booking_handoff,
            tool_name_override="transfer_to_seat_booking_agent",
        ),
    ],
)

faq_agent.handoffs.append(
    handoff(agent=triage_agent, tool_name_override="transfer_to_triage_agent")
)
seat_booking_agent.handoffs.append(
    handoff(agent=triage_agent, tool_name_override="transfer_to_triage_agent")
)


### RUN


async def main():
    current_agent: Agent[AirlineAgentContext] = triage_agent # 启动时从分诊智能体开始
    input_items: list[TResponseInputItem] = [] # 初始化输入项列表为空
    context = AirlineAgentContext() # 初始化上下文对象
    auto_mode = is_auto_mode() # 检查是否处于自动模式

    # 通常，用户的每个输入都是对您的应用程序的API请求，您可以将请求包装在trace()中
    # 在这里，我们将使用一个随机的UUID作为会话ID
    conversation_id = uuid.uuid4().hex[:16]

    while True:
        user_input = input_with_fallback(
            "Enter your message: ",
            "What are your store hours?",
        )
        with trace("Customer service", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(current_agent, input_items, context=context)

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            input_items = result.to_input_list()
            current_agent = result.last_agent
        if auto_mode:
            break


if __name__ == "__main__":
    asyncio.run(main())