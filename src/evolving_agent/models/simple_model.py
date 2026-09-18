from pydantic import BaseModel

class Booking(BaseModel):
    confirmation_number: str
    passenger_name: str
    seat_number: str | None = None
    flight_number: str

class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None