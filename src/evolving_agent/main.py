from __future__ import annotations as _annotations

import asyncio
import uuid

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    trace,
)

from evolving_agent.auto_model import input_with_fallback, is_auto_mode
### CONTEXT
from evolving_agent.models.simple_model import AirlineAgentContext

### AGENTS
from evolving_agent.agent_runtime.agents.factory import (
    build_agent_registry,
)

### RUN


async def main():
    agent_registry = build_agent_registry()

    current_agent: Agent[AirlineAgentContext] = (
        agent_registry.triage
    )
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