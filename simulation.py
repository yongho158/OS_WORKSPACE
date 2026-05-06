from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from models import Counter, Passenger, SimulationResult, create_default_counters


class SchedulerProtocol(Protocol):
    def select_next_passenger(
        self,
        ready_queue: list[Passenger],
        counters: list[Counter],
        current_time: int,
        counter: Counter,
    ) -> Passenger | None:
        ...


class SimulationEngine:
    def __init__(
        self,
        passengers: list[Passenger],
        counters: list[Counter] | None = None,
        enable_log: bool = True,
    ) -> None:
        self.passengers = sorted(deepcopy(passengers), key=lambda passenger: passenger.sort_key())
        self.counters = deepcopy(counters) if counters is not None else create_default_counters()
        self.enable_log = enable_log
        self.current_time = 0
        self.ready_queue: list[Passenger] = []
        self.completed_passengers: list[Passenger] = []
        self.event_log: list[str] = []

    def run(self, scheduler: SchedulerProtocol) -> SimulationResult:
        self._reset()

        next_arrival_index = 0
        total_passenger_count = len(self.passengers)

        while len(self.completed_passengers) < total_passenger_count:
            next_arrival_index = self._move_arrivals_to_ready_queue(next_arrival_index)
            self._complete_due_services()
            self._assign_idle_counters(scheduler)

            if len(self.completed_passengers) >= total_passenger_count:
                break

            next_time = self._next_event_time(next_arrival_index)
            if next_time is None:
                raise RuntimeError("Simulation cannot continue because no future event exists.")

            self._advance_time(next_time)

        return SimulationResult(
            passengers=sorted(self.passengers, key=lambda passenger: passenger.sort_key()),
            counters=self.counters,
            event_log=list(self.event_log),
            finished_at=self.current_time,
        )

    def _reset(self) -> None:
        self.current_time = 0
        self.ready_queue = []
        self.completed_passengers = []
        self.event_log = []

        for passenger in self.passengers:
            passenger.reset_runtime_state()
        for counter in self.counters:
            counter.reset_runtime_state()

    def _move_arrivals_to_ready_queue(self, start_index: int) -> int:
        index = start_index
        while index < len(self.passengers) and self.passengers[index].arrival_time <= self.current_time:
            passenger = self.passengers[index]
            self.ready_queue.append(passenger)
            self._log(
                f"time={self.current_time}: passenger {passenger.passenger_id} arrived "
                f"(class={passenger.passenger_class}, service={passenger.service_time})."
            )
            index += 1

        self.ready_queue.sort(key=lambda passenger: passenger.sort_key())
        return index

    def _complete_due_services(self) -> None:
        for counter in self.counters:
            passenger = counter.complete_current_passenger(self.current_time)
            if passenger is None:
                continue

            self.completed_passengers.append(passenger)
            self._log(
                f"time={self.current_time}: passenger {passenger.passenger_id} completed at "
                f"{counter.counter_id} (turnaround={passenger.turnaround_time})."
            )

    def _assign_idle_counters(self, scheduler: SchedulerProtocol) -> None:
        made_assignment = True
        while made_assignment:
            made_assignment = False

            for counter in self.counters:
                if not counter.is_idle or not self.ready_queue:
                    continue

                selected = scheduler.select_next_passenger(
                    ready_queue=list(self.ready_queue),
                    counters=self.counters,
                    current_time=self.current_time,
                    counter=counter,
                )

                if selected is None:
                    self._log(f"time={self.current_time}: {counter.counter_id} is idle.")
                    continue

                if selected not in self.ready_queue:
                    raise ValueError(
                        "Scheduler returned a passenger that is not in the ready queue: "
                        f"{selected.passenger_id}"
                    )

                self.ready_queue.remove(selected)
                counter.assign_passenger(selected, self.current_time)
                made_assignment = True
                self._log(
                    f"time={self.current_time}: passenger {selected.passenger_id} started at "
                    f"{counter.counter_id}; completes at {counter.busy_until}."
                )

    def _next_event_time(self, next_arrival_index: int) -> int | None:
        candidate_times: list[int] = []

        if next_arrival_index < len(self.passengers):
            candidate_times.append(self.passengers[next_arrival_index].arrival_time)

        for counter in self.counters:
            if not counter.is_idle:
                candidate_times.append(counter.busy_until)

        future_times = [time for time in candidate_times if time > self.current_time]
        if not future_times:
            return None

        return min(future_times)

    def _advance_time(self, next_time: int) -> None:
        if next_time <= self.current_time:
            raise ValueError("Simulation time must move forward.")

        duration = next_time - self.current_time
        for counter in self.counters:
            counter.add_idle_time(duration)

        if self.ready_queue and any(counter.is_idle for counter in self.counters):
            idle_counter_ids = [
                counter.counter_id for counter in self.counters if counter.is_idle
            ]
            self._log(
                f"time={self.current_time}: counters {','.join(idle_counter_ids)} remain idle "
                f"with {len(self.ready_queue)} passenger(s) waiting."
            )
        elif any(counter.is_idle for counter in self.counters):
            idle_counter_ids = [
                counter.counter_id for counter in self.counters if counter.is_idle
            ]
            self._log(
                f"time={self.current_time}: counters {','.join(idle_counter_ids)} idle for "
                f"{duration} time unit(s)."
            )

        self.current_time = next_time

    def _log(self, message: str) -> None:
        if self.enable_log:
            self.event_log.append(message)
