from agents.decorators import tool


@tool(
    name_override="faq_lookup_tool",
    description_override="Lookup frequently asked questions.",
)
async def faq_lookup_tool(question: str) -> str:
    """查找航空公司相关的常见问题。"""

    question_lower = question.lower()

    if any(
        keyword in question_lower
        for keyword in [
            "bag",
            "baggage",
            "luggage",
            "carry-on",
            "hand luggage",
            "hand carry",
            "行李",
            "随身行李",
            "手提行李",
            "托运行李",
        ]
    ):
        return (
            "您可以携带一件行李上飞机。"
            "它必须在50磅以下，尺寸为22英寸 x 14英寸 x 9英寸。"
        )

    if any(
        keyword in question_lower
        for keyword in [
            "seat",
            "seats",
            "seating",
            "plane",
            "座位",
            "飞机",
            "座位安排",
            "座位分配",
            "座位选择",
        ]
    ):
        return (
            "飞机上有120个座位。"
            "有22个商务舱座位和98个经济舱座位。"
            "出口座位是第4排和第16排。"
            "第5排到第8排是经济PLUS，有额外的腿部空间。"
        )

    if any(
        keyword in question_lower
        for keyword in [
            "wifi",
            "internet",
            "wireless",
            "connectivity",
            "network",
            "online",
            "网络",
            "无线",
            "连接",
            "上网",
        ]
    ):
        return "飞机上有免费WiFi，请连接 Airline-Wifi"

    return "抱歉，我不知道这个问题的答案。"