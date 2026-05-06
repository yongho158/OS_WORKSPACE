from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
from typing import Iterable

from models import BUSINESS, CLASS_NAMES, ECONOMY, FIRST, Passenger, SimulationResult
from report_utils import write_att_comparison_png
from simulation import SimulationEngine
from strategies import BaselineA_FCFS, BaselineB_Priority, BaselineC_SJF, OurScheduler, SchedulerStrategy


SCHEDULER_ORDER = ("fcfs", "priority", "sjf", "ours")


def parse_input_file(input_path: Path) -> list[Passenger]:
    """Parse passenger rows: passenger_id arrival_time passenger_class service_time."""
    passengers: list[Passenger] = []

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.partition("#")[0].strip()
            if not line:
                continue

            parts = re.split(r"[\s,]+", line)
            if len(parts) != 4:
                raise ValueError(
                    f"{input_path}:{line_number}: expected 4 columns "
                    "(passenger_id arrival_time class service_time)."
                )

            passenger_id_token, arrival_token, class_token, service_token = parts
            passenger_id = _parse_passenger_id(passenger_id_token)
            arrival_time = _parse_non_negative_int(input_path, line_number, "arrival_time", arrival_token)
            passenger_class = _parse_passenger_class(input_path, line_number, class_token)
            service_time = _parse_positive_int(input_path, line_number, "service_time", service_token)

            passengers.append(
                Passenger(
                    passenger_id=passenger_id,
                    arrival_time=arrival_time,
                    passenger_class=passenger_class,
                    service_time=service_time,
                )
            )

    if not passengers:
        raise ValueError(f"{input_path}: no passenger rows found.")

    return sorted(passengers, key=lambda passenger: passenger.sort_key())


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run airport check-in scheduling simulations.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="input.txt path. Each row: passenger_id arrival_time class service_time",
    )
    parser.add_argument(
        "--scheduler",
        choices=(*SCHEDULER_ORDER, "all"),
        default="all",
        help="scheduler to run: fcfs, priority, sjf, ours, or all. Default: all",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="output directory. Default: output",
    )
    return parser


def selected_scheduler_names(selection: str) -> list[str]:
    if selection == "all":
        return list(SCHEDULER_ORDER)
    return [selection]


def create_scheduler(name: str) -> SchedulerStrategy:
    if name == "fcfs":
        return BaselineA_FCFS()
    if name == "priority":
        return BaselineB_Priority()
    if name == "sjf":
        return BaselineC_SJF()
    if name == "ours":
        return OurScheduler()

    raise ValueError(f"Unsupported scheduler: {name}")


def run_scheduler(passengers: list[Passenger], scheduler_name: str) -> SimulationResult:
    scheduler = create_scheduler(scheduler_name)
    engine = SimulationEngine(passengers=passengers, enable_log=True)
    result = engine.run(scheduler)
    _validate_result(result)
    return result


def write_outputs(
    results: dict[str, SimulationResult],
    output_dir: Path,
    canonical_scheduler: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for scheduler_name, result in results.items():
        prefix = f"{scheduler_name}_"
        _write_passenger_results(result, output_dir / f"{prefix}passenger_results.csv")
        _write_class_summary(result, output_dir / f"{prefix}class_summary.csv")
        _write_counter_summary(result, output_dir / f"{prefix}counter_summary.csv")
        _write_simulation_log(result, output_dir / f"{prefix}simulation_log.txt")

    canonical_result = results[canonical_scheduler]
    _write_passenger_results(canonical_result, output_dir / "passenger_results.csv")
    _write_class_summary(canonical_result, output_dir / "class_summary.csv")
    _write_counter_summary(canonical_result, output_dir / "counter_summary.csv")
    _write_simulation_log(canonical_result, output_dir / "simulation_log.txt")
    _write_att_comparison(results, output_dir / "att_comparison.csv")
    write_att_comparison_png(results, output_dir, our_scheduler_name="ours")


def print_summary(results: dict[str, SimulationResult]) -> None:
    for scheduler_name, result in results.items():
        averages = result.average_turnaround_by_class()
        print(f"[{scheduler_name}]")
        print(f"finished_at: {result.finished_at}")
        print(f"completed: {len(result.completed_passengers)}/{len(result.passengers)}")
        print(f"average_turnaround_time: {result.average_turnaround_time:.2f}")
        print(
            "class_average_turnaround_time: "
            f"First={averages[FIRST]:.2f}, "
            f"Business={averages[BUSINESS]:.2f}, "
            f"Economy={averages[ECONOMY]:.2f}"
        )


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    passengers = parse_input_file(args.input)
    scheduler_names = selected_scheduler_names(args.scheduler)
    results = {
        scheduler_name: run_scheduler(passengers, scheduler_name)
        for scheduler_name in scheduler_names
    }

    canonical_scheduler = "ours" if "ours" in results else scheduler_names[-1]
    write_outputs(results, args.output, canonical_scheduler)
    print_summary(results)
    print(f"output_dir: {args.output}")

    return 0


def _parse_passenger_id(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def _parse_non_negative_int(path: Path, line_number: int, field_name: str, value: str) -> int:
    number = _parse_int(path, line_number, field_name, value)
    if number < 0:
        raise ValueError(f"{path}:{line_number}: {field_name} must be non-negative.")
    return number


def _parse_positive_int(path: Path, line_number: int, field_name: str, value: str) -> int:
    number = _parse_int(path, line_number, field_name, value)
    if number <= 0:
        raise ValueError(f"{path}:{line_number}: {field_name} must be positive.")
    return number


def _parse_passenger_class(path: Path, line_number: int, value: str) -> int:
    passenger_class = _parse_int(path, line_number, "class", value)
    if passenger_class not in CLASS_NAMES:
        valid_classes = ", ".join(str(class_id) for class_id in sorted(CLASS_NAMES))
        raise ValueError(f"{path}:{line_number}: class must be one of {valid_classes}.")
    return passenger_class


def _parse_int(path: Path, line_number: int, field_name: str, value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_number}: {field_name} must be an integer.") from exc


def _validate_result(result: SimulationResult) -> None:
    if len(result.completed_passengers) != len(result.passengers):
        raise RuntimeError("Simulation finished without completing every passenger.")

    for passenger in result.passengers:
        if passenger.service_start_time is None:
            raise RuntimeError(f"Passenger {passenger.passenger_id} has no service_start_time.")
        if passenger.completion_time is None:
            raise RuntimeError(f"Passenger {passenger.passenger_id} has no completion_time.")
        if passenger.turnaround_time is None:
            raise RuntimeError(f"Passenger {passenger.passenger_id} has no turnaround_time.")
        if passenger.completion_time != passenger.service_start_time + passenger.service_time:
            raise RuntimeError(f"Passenger {passenger.passenger_id} has an invalid completion_time.")
        if passenger.turnaround_time != passenger.completion_time - passenger.arrival_time:
            raise RuntimeError(f"Passenger {passenger.passenger_id} has an invalid turnaround_time.")


def _write_passenger_results(result: SimulationResult, output_path: Path) -> None:
    fieldnames = [
        "passenger_id",
        "class",
        "class_name",
        "arrival_time",
        "service_time",
        "service_start_time",
        "completion_time",
        "turnaround_time",
        "assigned_counter_id",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for passenger in result.passengers:
            row = passenger.to_result_dict()
            row["class"] = row.pop("passenger_class")
            row["class_name"] = CLASS_NAMES.get(passenger.passenger_class, str(passenger.passenger_class))
            writer.writerow(row)


def _write_class_summary(result: SimulationResult, output_path: Path) -> None:
    averages = result.average_turnaround_by_class()

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "class",
                "class_name",
                "passenger_count",
                "average_turnaround_time",
            ],
        )
        writer.writeheader()
        for passenger_class in (FIRST, BUSINESS, ECONOMY):
            writer.writerow(
                {
                    "class": passenger_class,
                    "class_name": CLASS_NAMES[passenger_class],
                    "passenger_count": sum(
                        1 for passenger in result.passengers if passenger.passenger_class == passenger_class
                    ),
                    "average_turnaround_time": f"{averages[passenger_class]:.2f}",
                }
            )


def _write_counter_summary(result: SimulationResult, output_path: Path) -> None:
    fieldnames = [
        "counter_id",
        "counter_type",
        "processed_count",
        "total_service_time",
        "idle_time",
        "processed_passenger_ids",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for counter in result.counters:
            row = counter.to_summary_dict()
            row["processed_passenger_ids"] = " ".join(str(passenger_id) for passenger_id in row["processed_passenger_ids"])
            writer.writerow(row)


def _write_simulation_log(result: SimulationResult, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        file.write("\n".join(result.event_log))
        if result.event_log:
            file.write("\n")


def _write_att_comparison(results: dict[str, SimulationResult], output_path: Path) -> None:
    our_att = results["ours"].average_turnaround_time if "ours" in results else None

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "scheduler",
                "scheduler_name",
                "ATT",
                "improvement_rate",
            ],
        )
        writer.writeheader()
        for scheduler_name, result in results.items():
            att = result.average_turnaround_time
            improvement = ""
            if our_att is not None and att:
                improvement = f"{((att - our_att) / att * 100):.2f}"

            writer.writerow(
                {
                    "scheduler": scheduler_name,
                    "scheduler_name": create_scheduler(scheduler_name).name,
                    "ATT": f"{att:.2f}",
                    "improvement_rate": improvement,
                }
            )


if __name__ == "__main__":
    raise SystemExit(main())
