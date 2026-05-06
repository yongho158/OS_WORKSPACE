from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


FIRST = 1
BUSINESS = 2
ECONOMY = 3

CLASS_NAMES = {
    FIRST: "First",
    BUSINESS: "Business",
    ECONOMY: "Economy",
}

COUNTER_FIRST = "First"
COUNTER_BUSINESS = "Business"
COUNTER_ECONOMY = "Economy"
COUNTER_FLEX = "Flex"


def passenger_id_sort_key(passenger_id: Any) -> tuple[int, Any]:
    """Return a stable sort key for numeric ids and ids such as P01."""
    text = str(passenger_id)
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return (0, int(digits))
    return (1, text)


@dataclass
class Passenger:
    passenger_id: Any
    arrival_time: int
    passenger_class: int
    service_time: int
    service_start_time: Optional[int] = None
    completion_time: Optional[int] = None
    turnaround_time: Optional[int] = None
    assigned_counter_id: Optional[str] = None

    @property
    def class_name(self) -> str:
        return CLASS_NAMES.get(self.passenger_class, str(self.passenger_class))

    @property
    def has_started(self) -> bool:
        return self.service_start_time is not None

    @property
    def is_completed(self) -> bool:
        return self.completion_time is not None

    def sort_key(self) -> tuple[int, tuple[int, Any]]:
        return (self.arrival_time, passenger_id_sort_key(self.passenger_id))

    def reset_runtime_state(self) -> None:
        self.service_start_time = None
        self.completion_time = None
        self.turnaround_time = None
        self.assigned_counter_id = None

    def start_service(self, current_time: int, counter_id: str) -> None:
        if self.has_started:
            raise ValueError(f"Passenger {self.passenger_id} has already started service.")

        self.service_start_time = current_time
        self.assigned_counter_id = counter_id

    def complete_service(self, completion_time: int) -> None:
        if self.service_start_time is None:
            raise ValueError(f"Passenger {self.passenger_id} cannot complete before service starts.")

        expected_completion = self.service_start_time + self.service_time
        if completion_time != expected_completion:
            raise ValueError(
                f"Passenger {self.passenger_id} completion_time={completion_time} "
                f"does not match start + service_time={expected_completion}."
            )

        self.completion_time = completion_time
        self.turnaround_time = self.completion_time - self.arrival_time

    def to_result_dict(self) -> dict[str, Any]:
        return {
            "passenger_id": self.passenger_id,
            "passenger_class": self.passenger_class,
            "arrival_time": self.arrival_time,
            "service_time": self.service_time,
            "service_start_time": self.service_start_time,
            "completion_time": self.completion_time,
            "turnaround_time": self.turnaround_time,
            "assigned_counter_id": self.assigned_counter_id,
        }


@dataclass
class Counter:
    counter_id: str
    counter_type: str
    current_passenger: Optional[Passenger] = None
    busy_until: int = 0
    processed_passengers: list[Passenger] = field(default_factory=list)
    total_service_time: int = 0
    idle_time: int = 0

    @property
    def is_idle(self) -> bool:
        return self.current_passenger is None

    @property
    def preferred_passenger_class(self) -> Optional[int]:
        if self.counter_type == COUNTER_FIRST:
            return FIRST
        if self.counter_type == COUNTER_BUSINESS:
            return BUSINESS
        if self.counter_type == COUNTER_ECONOMY:
            return ECONOMY
        return None

    def reset_runtime_state(self) -> None:
        self.current_passenger = None
        self.busy_until = 0
        self.processed_passengers.clear()
        self.total_service_time = 0
        self.idle_time = 0

    def assign_passenger(self, passenger: Passenger, current_time: int) -> None:
        if not self.is_idle:
            active_id = self.current_passenger.passenger_id if self.current_passenger else None
            raise RuntimeError(
                f"Counter {self.counter_id} is busy with passenger {active_id} until {self.busy_until}."
            )

        passenger.start_service(current_time=current_time, counter_id=self.counter_id)
        self.current_passenger = passenger
        self.busy_until = current_time + passenger.service_time
        self.total_service_time += passenger.service_time

    def complete_current_passenger(self, current_time: int) -> Optional[Passenger]:
        if self.current_passenger is None or self.busy_until > current_time:
            return None

        passenger = self.current_passenger
        passenger.complete_service(self.busy_until)
        self.processed_passengers.append(passenger)
        self.current_passenger = None
        return passenger

    def add_idle_time(self, duration: int) -> None:
        if duration < 0:
            raise ValueError("Idle duration cannot be negative.")
        if self.is_idle:
            self.idle_time += duration

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "counter_id": self.counter_id,
            "counter_type": self.counter_type,
            "processed_count": len(self.processed_passengers),
            "total_service_time": self.total_service_time,
            "idle_time": self.idle_time,
            "processed_passenger_ids": [p.passenger_id for p in self.processed_passengers],
        }


@dataclass
class SimulationResult:
    passengers: list[Passenger]
    counters: list[Counter]
    event_log: list[str]
    finished_at: int

    @property
    def completed_passengers(self) -> list[Passenger]:
        return [passenger for passenger in self.passengers if passenger.is_completed]

    @property
    def average_turnaround_time(self) -> float:
        completed = self.completed_passengers
        if not completed:
            return 0.0
        return sum(passenger.turnaround_time or 0 for passenger in completed) / len(completed)

    def average_turnaround_by_class(self) -> dict[int, float]:
        averages: dict[int, float] = {}
        for passenger_class in (FIRST, BUSINESS, ECONOMY):
            class_passengers = [
                passenger
                for passenger in self.completed_passengers
                if passenger.passenger_class == passenger_class
            ]
            if class_passengers:
                averages[passenger_class] = sum(
                    passenger.turnaround_time or 0 for passenger in class_passengers
                ) / len(class_passengers)
            else:
                averages[passenger_class] = 0.0
        return averages


def create_default_counters() -> list[Counter]:
    return [
        Counter("C1", COUNTER_FIRST),
        Counter("C2", COUNTER_BUSINESS),
        Counter("C3", COUNTER_ECONOMY),
        Counter("C4", COUNTER_FLEX),
        Counter("C5", COUNTER_FLEX),
    ]
