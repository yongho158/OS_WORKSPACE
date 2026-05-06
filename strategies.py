from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
import re
from typing import Any, Iterable, Optional


FIRST = 1
BUSINESS = 2
ECONOMY = 3

CLASS_WEIGHTS = {
    FIRST: 1.5,
    BUSINESS: 1.1,
    ECONOMY: 1.0,
}


def _get_value(obj: Any, names: Iterable[str], default: Any = None) -> Any:
    """Read a value from either an object model or a dict-like model."""
    if obj is None:
        return default

    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
        return default

    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    return default


def _passenger_id(passenger: Any) -> Any:
    return _get_value(passenger, ("passenger_id", "pid", "id"), "")


def _passenger_id_key(passenger: Any) -> tuple[int, Any]:
    raw_id = _passenger_id(passenger)
    if isinstance(raw_id, int):
        return (0, raw_id)

    text_id = str(raw_id)
    match = re.search(r"\d+", text_id)
    if match:
        return (0, int(match.group()))
    return (1, text_id)


def _arrival_time(passenger: Any) -> int:
    return int(_get_value(passenger, ("arrival_time", "arrival", "arrived_at"), 0))


def _passenger_class(passenger: Any) -> int:
    return int(
        _get_value(
            passenger,
            ("passenger_class", "class_type", "travel_class", "cls", "class"),
            ECONOMY,
        )
    )


def _service_time(passenger: Any) -> int:
    return int(_get_value(passenger, ("service_time", "burst_time", "service", "burst"), 0))


def _counter_id(counter: Any) -> str:
    raw_id = _get_value(counter, ("counter_id", "id", "cid"), "")
    return str(raw_id).upper()


def _counter_type(counter: Any) -> str:
    raw_type = _get_value(counter, ("counter_type", "type", "kind"), "")
    return str(raw_type).upper()


def _counter_preferred_class(counter: Any) -> Optional[int]:
    """Return the counter's preferred class, if it is a dedicated counter."""
    raw_preference = _get_value(
        counter,
        ("preferred_class", "dedicated_class", "assigned_class", "counter_class"),
        None,
    )
    if raw_preference is not None:
        try:
            return int(raw_preference)
        except (TypeError, ValueError):
            text = str(raw_preference).upper()
            if "FIRST" in text:
                return FIRST
            if "BUSINESS" in text:
                return BUSINESS
            if "ECONOMY" in text:
                return ECONOMY

    counter_type = _counter_type(counter)
    if "FLEX" in counter_type:
        return None
    if "FIRST" in counter_type:
        return FIRST
    if "BUSINESS" in counter_type:
        return BUSINESS
    if "ECONOMY" in counter_type:
        return ECONOMY

    counter_id = _counter_id(counter)
    if counter_id in {"1", "C1"}:
        return FIRST
    if counter_id in {"2", "C2"}:
        return BUSINESS
    if counter_id in {"3", "C3"}:
        return ECONOMY

    return None


class SchedulerStrategy(ABC):
    """Base interface for all non-preemptive scheduler strategies."""

    name = "SchedulerStrategy"

    @abstractmethod
    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        """Return one passenger to assign to counter, or None if no passenger is ready."""
        raise NotImplementedError

    def select_next(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        """Compatibility alias for engines that call select_next()."""
        return self.select_next_passenger(ready_queue, counters, current_time, counter)


class BaselineA_FCFS(SchedulerStrategy):
    """Baseline A: single ready queue, first-come first-served."""

    name = "Baseline A: FCFS"

    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        if not ready_queue:
            return None

        return min(ready_queue, key=lambda passenger: (_arrival_time(passenger), _passenger_id_key(passenger)))


class BaselineB_Priority(SchedulerStrategy):
    """Baseline B: fixed class priority, then FCFS within the same class."""

    name = "Baseline B: Priority"

    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        if not ready_queue:
            return None

        return min(
            ready_queue,
            key=lambda passenger: (
                _passenger_class(passenger),
                _arrival_time(passenger),
                _passenger_id_key(passenger),
            ),
        )


class BaselineC_SJF(SchedulerStrategy):
    """Baseline C: non-preemptive shortest-job-first."""

    name = "Baseline C: Non-preemptive SJF"

    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        if not ready_queue:
            return None

        return min(
            ready_queue,
            key=lambda passenger: (
                _service_time(passenger),
                _arrival_time(passenger),
                _passenger_id_key(passenger),
            ),
        )


class OurScheduler(SchedulerStrategy):
    """
    Hybrid Multi-Level Queue scheduler.

    Selection combines:
    - Multi-Level Queue: passengers are separated by class.
    - Priority Weight: First/Business receive higher class weights.
    - HRRN/Aging: waiting time increases the response ratio.
    - SJF tie-break: shorter service time wins when scores are equal.
    - FCFS tie-break: earlier arrival and lower ID win after that.
    """

    name = "Our Scheduler: MLQ + Weighted HRRN + SJF"

    def __init__(
        self,
        class_weights: dict[int, float] | None = None,
        allow_dedicated_counter_borrowing: bool = True,
    ) -> None:
        self.class_weights = dict(CLASS_WEIGHTS if class_weights is None else class_weights)
        self.allow_dedicated_counter_borrowing = allow_dedicated_counter_borrowing

    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        if not ready_queue:
            return None

        class_queues = self._build_class_queues(ready_queue)
        candidate_pool = self._candidate_pool_for_counter(class_queues, ready_queue, counter)
        if not candidate_pool:
            return None

        return max(candidate_pool, key=lambda passenger: self._selection_key(passenger, current_time))

    def _build_class_queues(self, ready_queue: list[Any]) -> dict[int, list[Any]]:
        class_queues: dict[int, list[Any]] = defaultdict(list)
        for passenger in ready_queue:
            class_queues[_passenger_class(passenger)].append(passenger)
        return class_queues

    def _candidate_pool_for_counter(
        self,
        class_queues: dict[int, list[Any]],
        ready_queue: list[Any],
        counter: Any,
    ) -> list[Any]:
        preferred_class = _counter_preferred_class(counter)
        if preferred_class is None:
            return list(ready_queue)

        preferred_queue = class_queues.get(preferred_class, [])
        if preferred_queue:
            return list(preferred_queue)

        if self.allow_dedicated_counter_borrowing:
            return list(ready_queue)

        return []

    def _selection_key(self, passenger: Any, current_time: int) -> tuple[float, int, int, tuple[int, Any]]:
        waiting_time = max(0, current_time - _arrival_time(passenger))
        service_time = max(1, _service_time(passenger))
        passenger_class = _passenger_class(passenger)
        class_weight = self.class_weights.get(passenger_class, 1.0)

        response_ratio = (waiting_time + service_time) / service_time
        weighted_hrrn_score = response_ratio * class_weight

        return (
            weighted_hrrn_score,
            -service_time,
            -_arrival_time(passenger),
            _reverse_id_key(passenger),
        )


def _reverse_id_key(passenger: Any) -> tuple[int, Any]:
    order, value = _passenger_id_key(passenger)
    if isinstance(value, int):
        return (-order, -value)
    return (-order, _reverse_text(value))


def _reverse_text(value: Any) -> tuple[int, ...]:
    return tuple(-ord(char) for char in str(value))


# Common aliases for slightly different naming conventions.
FCFSStrategy = BaselineA_FCFS
PriorityStrategy = BaselineB_Priority
SJFStrategy = BaselineC_SJF
BaselineAFCFS = BaselineA_FCFS
BaselineBPriority = BaselineB_Priority
BaselineCSJF = BaselineC_SJF
