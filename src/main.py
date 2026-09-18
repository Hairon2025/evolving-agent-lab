from __future__ import annotations as _annotations

import asyncio
import random
import uuid

from pydantic import BaseModel

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
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
)
from agents.decorators import tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from auto_model import confirm_with_fallback, input_with_fallback, is_auto_mode

from openai import AsyncOpenAI
import os

deepseek_client = AsyncOpenAI(
    api_key= os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

set_default_openai_client(deepseek_client) # 设置默认的OpenAI客户端为DeepSeek
set_default_openai_api("chat_completions") # 设置默认的OpenAI API为聊天补全
set_tracing_disabled(True) # 禁用跟踪以避免在DeepSeek中记录敏感信息

### CONTEXT


class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


### TOOLS


@tool(name_override="faq_lookup_tool", description_override="Lookup frequently asked questions.")
async def faq_lookup_tool(question: str) -> str:
    """
    查找航空公司相关的常见问题。

    Args:
        question: 客户提出的问题。
    Returns:
        对问题的答案，如果无法回答，则返回默认消息。
    """
    question_lower = question.lower()
    if any(
        keyword in question_lower
        for keyword in ["bag", "baggage", "luggage", "carry-on", "hand luggage", "hand carry", "行李", "随身行李", "手提行李", "托运行李"]
    ):
        return (
            "您可以携带一件行李上飞机。 "
            "它必须在50磅以下，尺寸为22英寸 x 14英寸 x 9英寸。"
        )
    elif any(keyword in question_lower for keyword in ["seat", "seats", "seating", "plane","座位", "飞机", "座位安排", "座位分配", "座位选择"]):
        return (
            "飞机上有120个座位。"
            "有22个商务舱座位和98个经济舱座位。 "
            "出口座位是第4排和第16排。 "
            "第5排到第8排是经济PLUS，有额外的腿部空间。 "
        )
    elif any(
        keyword in question_lower
        for keyword in ["wifi", "internet", "wireless", "connectivity", "network", "online", "网络", "无线", "连接", "上网"]
    ):
        return "飞机上有免费WiFi，请连接 Airline-Wifi"
    return "抱歉，我不知道这个问题的答案。"


@tool
async def update_seat(
    context: RunContextWrapper[AirlineAgentContext], confirmation_number: str, new_seat: str
) -> str:
    """
    更新指定确认号码的座位。

    参数：
        confirmation_number: 航班的确认号码。
        new_seat: 要更新到的新座位。

    Update the seat for a given confirmation number.

    Args:
        confirmation_number: The confirmation number for the flight.
        new_seat: The new seat to update to.
    """
    # Update the context based on the customer's input
    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat
    # Ensure that the flight number has been set by the incoming handoff
    assert context.context.flight_number is not None, "Flight number is required"
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}"


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
    model="deepseek-flash",
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
    model="deepseek-flash",
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
    model="deepseek-flash",
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