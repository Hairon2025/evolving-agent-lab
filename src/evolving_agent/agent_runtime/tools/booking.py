from agents import RunContextWrapper
from agents.decorators import tool

from evolving_agent.agent_runtime.context import AirlineAgentContext


@tool
async def update_seat(
    context: RunContextWrapper[AirlineAgentContext],
    confirmation_number: str,
    new_seat: str,
) -> str:
    """更新指定确认号的座位。"""

    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat

    if context.context.flight_number is None:
        return "ERROR: Flight number is required."

    return (
        f"Updated seat to {new_seat} "
        f"for confirmation number {confirmation_number}"
    )