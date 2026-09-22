import unittest

from src.evolving_agent.models.booking.repository import (
    BookingNotFound,
    InMemoryBookingRepository,
    SeatUnavailable,
)


class BookingRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryBookingRepository()

    def test_change_seat_updates_booking_and_inventory(self) -> None:
        booking = self.repository.change_seat("abc123", "5a")

        self.assertEqual(booking.seat_number, "5A")
        self.assertEqual(
            self.repository.get_booking("ABC123").seat_number,
            "5A",
        )
        self.assertIn(
            "8A",
            self.repository.list_available_seats("ABC123"),
        )
        self.assertNotIn(
            "5A",
            self.repository.list_available_seats("ABC123"),
        )

    def test_unknown_confirmation_number(self) -> None:
        with self.assertRaises(BookingNotFound):
            self.repository.get_booking("BAD999")

    def test_unavailable_seat_keeps_original_state(self) -> None:
        with self.assertRaises(SeatUnavailable):
            self.repository.change_seat("ABC123", "99A")

        self.assertEqual(
            self.repository.get_booking("ABC123").seat_number,
            "8A",
        )