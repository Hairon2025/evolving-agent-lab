from copy import deepcopy

from evolving_agent.models.booking.entities import Booking


class BookingError(ValueError):
    """预订操作中的可预期业务错误。"""

class BookingNotFound(BookingError):
    """确认号不存在。"""


class SeatUnavailable(BookingError):
    """目标座位不可用。"""


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._bookings: dict[str, Booking] = {
            "ABC123": Booking(
                confirmation_number="ABC123",
                passenger_name="张三",
                flight_number="MU5101",
                seat_number="8A",
            )
        }
        self._available_seats: dict[str, set[str]] = {
            "MU5101": {"5A", "5B", "8C"}
        }

    def _find_booking(self, confirmation_number: str) -> Booking:
        number = confirmation_number.strip().upper()
        booking = self._bookings.get(number)

        if booking is None:
            raise BookingNotFound(f"找不到确认号 {number} 对应的预订")

        return booking

    def get_booking(self, confirmation_number: str) -> Booking:
        # 返回副本，避免调用方绕过仓库直接修改内部数据。
        return deepcopy(self._find_booking(confirmation_number))

    def list_available_seats(self, confirmation_number: str) -> list[str]:
        booking = self._find_booking(confirmation_number)
        return sorted(self._available_seats[booking.flight_number])

    def change_seat(
        self,
        confirmation_number: str,
        new_seat: str,
    ) -> Booking:
        booking = self._find_booking(confirmation_number)
        target_seat = new_seat.strip().upper()

        # 重复请求不会再次占用座位。
        if target_seat == booking.seat_number:
            return deepcopy(booking)

        available = self._available_seats[booking.flight_number]
        if target_seat not in available:
            raise SeatUnavailable(f"座位 {target_seat} 不可用")

        old_seat = booking.seat_number
        available.remove(target_seat)

        if old_seat is not None:
            available.add(old_seat)

        booking.seat_number = target_seat
        return deepcopy(booking)