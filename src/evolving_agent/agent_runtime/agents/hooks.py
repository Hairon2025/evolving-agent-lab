import random

from agents import RunContextWrapper

from evolving_agent.models.simple_model import AirlineAgentContext


async def on_seat_booking_handoff(
    context: RunContextWrapper[AirlineAgentContext],
) -> None:
    """座位 Agent 接管时执行的临时回调。"""

    # 当前只是演示数据。
    # 接入 BookingRepository 后必须删除随机航班号。
    context.context.flight_number = f"FLT-{random.randint(100, 999)}"