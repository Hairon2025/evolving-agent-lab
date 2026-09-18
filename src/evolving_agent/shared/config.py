import os
from openai import AsyncOpenAI
from agents import (
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
)

deepseek_client = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/v1",
)

set_default_openai_client(deepseek_client)
set_default_openai_api("chat_completions")
set_tracing_disabled(True)

# 模型名集中管理，改一处生效
MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
