from pydantic import BaseModel


class Booking(BaseModel):
    confirmation_number: str
    passenger_name: str
    seat_number: str | None = None
    flight_number: str

