from __future__ import annotations

import csv
import struct
import zlib
from collections import OrderedDict
from numbers import Real
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CLASS_NAME_BY_VALUE = {
    1: "First",
    2: "Business",
    3: "Economy",
    "1": "First",
    "2": "Business",
    "3": "Economy",
}

CLASS_ORDER = {
    "First": 1,
    "Business": 2,
    "Economy": 3,
}

PASSENGER_HEADERS = [
    "passenger_id",
    "class",
    "arrival_time",
    "service_time",
    "service_start_time",
    "completion_time",
    "turnaround_time",
    "assigned_counter_id",
]

CLASS_SUMMARY_HEADERS = [
    "class",
    "passenger_count",
    "average_turnaround_time",
]

COUNTER_SUMMARY_HEADERS = [
    "counter_id",
    "counter_type",
    "processed_count",
    "total_service_time",
    "idle_time",
]

ATT_COMPARISON_HEADERS = [
    "scheduler_name",
    "ATT",
    "improvement_rate",
]


def ensure_output_dir(output_dir: str | Path = "output") -> Path:
    """Create and return the output directory."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def calculate_att(passengers: Iterable[Any]) -> float:
    """Calculate average turnaround time for passengers."""
    passenger_list = list(passengers)
    if not passenger_list:
        return 0.0
    total_turnaround_time = sum(_turnaround_time(passenger) for passenger in passenger_list)
    return total_turnaround_time / len(passenger_list)


def calculate_class_summary(passengers: Iterable[Any]) -> list[dict[str, Any]]:
    """Calculate passenger count and average turnaround time by class."""
    groups: "OrderedDict[str, list[float]]" = OrderedDict()

    for passenger in passengers:
        passenger_class = _passenger_class(passenger)
        groups.setdefault(passenger_class, []).append(_turnaround_time(passenger))

    rows = [
        {
            "class": passenger_class,
            "passenger_count": len(turnaround_times),
            "average_turnaround_time": sum(turnaround_times) / len(turnaround_times),
        }
        for passenger_class, turnaround_times in groups.items()
    ]
    rows.sort(key=lambda row: (CLASS_ORDER.get(str(row["class"]), 99), str(row["class"])))
    return rows


def calculate_counter_summary(counters: Iterable[Any]) -> list[dict[str, Any]]:
    """Calculate processed count, total service time, and idle time by counter."""
    rows = []

    for counter in counters:
        processed_passengers = _get(counter, "processed_passengers", default=None)
        processed_count = _get(counter, "processed_count", default=None)
        if processed_count is None:
            processed_count = len(processed_passengers or [])

        total_service_time = _get(counter, "total_service_time", default=None)
        if total_service_time is None:
            total_service_time = sum(
                _number(_get(passenger, "service_time", default=0))
                for passenger in (processed_passengers or [])
            )

        counter_id = _get(counter, "counter_id", "id", default="")
        counter_type = _get(counter, "counter_type", "type", default=None)

        rows.append({
            "counter_id": counter_id,
            "counter_type": counter_type if counter_type is not None else _infer_counter_type(counter_id),
            "processed_count": int(processed_count),
            "total_service_time": total_service_time,
            "idle_time": _get(counter, "idle_time", default=0),
        })

    rows.sort(key=lambda row: _sort_key(row["counter_id"]))
    return rows


def calculate_att_comparison(
    scheduler_results: Mapping[str, Any] | Iterable[Any],
    our_scheduler_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build ATT comparison rows.

    Values may be ATT numbers, passenger lists, dicts, tuples, or result objects.
    improvement_rate follows:
    (baseline_ATT - our_ATT) / baseline_ATT * 100
    """
    att_rows = _normalise_scheduler_results(scheduler_results)
    if not att_rows:
        return []

    comparison_att = _select_comparison_att(att_rows, our_scheduler_name)

    rows = []
    for scheduler_name, att in att_rows:
        improvement_rate = 0.0
        if att:
            improvement_rate = (att - comparison_att) / att * 100
        rows.append({
            "scheduler_name": scheduler_name,
            "ATT": att,
            "improvement_rate": improvement_rate,
        })

    return rows


def write_passenger_results_csv(
    passengers: Iterable[Any],
    output_dir: str | Path = "output",
) -> Path:
    output_path = ensure_output_dir(output_dir) / "passenger_results.csv"
    rows = [_passenger_row(passenger) for passenger in passengers]
    rows.sort(key=lambda row: _sort_key(row["passenger_id"]))
    _write_dict_csv(output_path, PASSENGER_HEADERS, rows)
    return output_path


def write_class_summary_csv(
    passengers_or_summary: Iterable[Any],
    output_dir: str | Path = "output",
) -> Path:
    output_path = ensure_output_dir(output_dir) / "class_summary.csv"
    rows = _normalise_class_summary(passengers_or_summary)
    _write_dict_csv(output_path, CLASS_SUMMARY_HEADERS, rows)
    return output_path


def write_counter_summary_csv(
    counters_or_summary: Iterable[Any],
    output_dir: str | Path = "output",
) -> Path:
    output_path = ensure_output_dir(output_dir) / "counter_summary.csv"
    rows = _normalise_counter_summary(counters_or_summary)
    _write_dict_csv(output_path, COUNTER_SUMMARY_HEADERS, rows)
    return output_path


def write_att_comparison_csv(
    scheduler_results_or_comparison: Mapping[str, Any] | Iterable[Any],
    output_dir: str | Path = "output",
    our_scheduler_name: str | None = None,
) -> Path:
    output_path = ensure_output_dir(output_dir) / "att_comparison.csv"
    rows = _normalise_att_comparison(scheduler_results_or_comparison, our_scheduler_name)
    _write_dict_csv(output_path, ATT_COMPARISON_HEADERS, rows)
    return output_path


def write_att_comparison_png(
    scheduler_results_or_comparison: Mapping[str, Any] | Iterable[Any],
    output_dir: str | Path = "output",
    our_scheduler_name: str | None = None,
) -> Path:
    """Write output/att_comparison.png as an ATT bar chart."""
    output_path = ensure_output_dir(output_dir) / "att_comparison.png"
    rows = _normalise_att_comparison(scheduler_results_or_comparison, our_scheduler_name)

    try:
        _write_att_chart_with_matplotlib(rows, output_path)
    except ImportError:
        _write_att_chart_with_builtin_png(rows, output_path)

    return output_path


def generate_reports(
    passengers: Iterable[Any],
    counters: Iterable[Any],
    scheduler_results: Mapping[str, Any] | Iterable[Any],
    output_dir: str | Path = "output",
    our_scheduler_name: str | None = None,
) -> dict[str, Path]:
    """Generate all CSV and PNG report files."""
    passengers = list(passengers)
    counters = list(counters)
    output_path = ensure_output_dir(output_dir)
    class_summary = calculate_class_summary(passengers)
    counter_summary = calculate_counter_summary(counters)
    att_comparison = calculate_att_comparison(scheduler_results, our_scheduler_name)

    return {
        "passenger_results": write_passenger_results_csv(passengers, output_path),
        "class_summary": write_class_summary_csv(class_summary, output_path),
        "counter_summary": write_counter_summary_csv(counter_summary, output_path),
        "att_comparison": write_att_comparison_csv(att_comparison, output_path),
        "att_comparison_png": write_att_comparison_png(att_comparison, output_path),
    }


create_reports = generate_reports
generate_all_reports = generate_reports
export_reports = generate_reports
calculate_average_turnaround_time = calculate_att
calculate_class_average_turnaround_times = calculate_class_summary
calculate_counter_statistics = calculate_counter_summary
save_passenger_results_csv = write_passenger_results_csv
save_class_summary_csv = write_class_summary_csv
save_counter_summary_csv = write_counter_summary_csv
save_att_comparison_csv = write_att_comparison_csv
save_att_comparison_png = write_att_comparison_png
plot_att_comparison = write_att_comparison_png
create_att_comparison_chart = write_att_comparison_png
generate_att_comparison_chart = write_att_comparison_png
write_att_comparison_graph = write_att_comparison_png


def _normalise_class_summary(rows_or_passengers: Iterable[Any]) -> list[dict[str, Any]]:
    rows = list(rows_or_passengers)
    if not rows:
        return []

    if all(_looks_like_class_summary_row(row) for row in rows):
        normalised = []
        for row in rows:
            normalised.append({
                "class": _get(row, "class", "passenger_class", default=""),
                "passenger_count": _get(row, "passenger_count", "count", default=0),
                "average_turnaround_time": _get(
                    row,
                    "average_turnaround_time",
                    "avg_turnaround_time",
                    "ATT",
                    "att",
                    default=0,
                ),
            })
        normalised.sort(key=lambda row: (CLASS_ORDER.get(str(row["class"]), 99), str(row["class"])))
        return normalised

    return calculate_class_summary(rows)


def _normalise_counter_summary(rows_or_counters: Iterable[Any]) -> list[dict[str, Any]]:
    rows = list(rows_or_counters)
    if not rows:
        return []

    if all(_looks_like_counter_summary_row(row) for row in rows):
        normalised = []
        for row in rows:
            normalised.append({
                "counter_id": _get(row, "counter_id", "id", default=""),
                "counter_type": _get(row, "counter_type", "type", default=""),
                "processed_count": _get(row, "processed_count", "count", default=0),
                "total_service_time": _get(row, "total_service_time", default=0),
                "idle_time": _get(row, "idle_time", default=0),
            })
        normalised.sort(key=lambda row: _sort_key(row["counter_id"]))
        return normalised

    return calculate_counter_summary(rows)


def _normalise_att_comparison(
    rows_or_results: Mapping[str, Any] | Iterable[Any],
    our_scheduler_name: str | None,
) -> list[dict[str, Any]]:
    if isinstance(rows_or_results, Mapping):
        rows = list(rows_or_results.values())
        if rows and all(_looks_like_att_comparison_row(row) for row in rows):
            return _normalise_att_rows(rows)
        return calculate_att_comparison(rows_or_results, our_scheduler_name)

    rows = list(rows_or_results)
    if rows and all(_looks_like_att_comparison_row(row) for row in rows):
        return _normalise_att_rows(rows)
    return calculate_att_comparison(rows, our_scheduler_name)


def _normalise_att_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    normalised = []
    for row in rows:
        normalised.append({
            "scheduler_name": _get(row, "scheduler_name", "name", "scheduler", default=""),
            "ATT": _number(_get(row, "ATT", "att", default=0)),
            "improvement_rate": _number(_get(row, "improvement_rate", default=0)),
        })
    return normalised


def _normalise_scheduler_results(
    scheduler_results: Mapping[str, Any] | Iterable[Any],
) -> list[tuple[str, float]]:
    if isinstance(scheduler_results, Mapping):
        return [
            (str(scheduler_name), _att_from_result(result))
            for scheduler_name, result in scheduler_results.items()
        ]

    rows = []
    for index, result in enumerate(scheduler_results, start=1):
        if _is_pair(result):
            scheduler_name, value = result[0], result[1]
            rows.append((str(scheduler_name), _att_from_result(value)))
            continue

        scheduler_name = _get(
            result,
            "scheduler_name",
            "name",
            "scheduler",
            "strategy_name",
            default=f"Scheduler {index}",
        )
        rows.append((str(scheduler_name), _att_from_result(result)))

    return rows


def _att_from_result(result: Any) -> float:
    if _is_number(result):
        return float(result)

    att_value = _get(result, "ATT", "att", "average_turnaround_time", default=None)
    if att_value is not None:
        return _number(att_value)

    passengers = _get(result, "passengers", "passenger_results", "completed_passengers", default=None)
    if passengers is not None:
        return calculate_att(passengers)

    return calculate_att(result)


def _select_comparison_att(
    att_rows: Sequence[tuple[str, float]],
    our_scheduler_name: str | None,
) -> float:
    if our_scheduler_name:
        for scheduler_name, att in att_rows:
            if scheduler_name == our_scheduler_name:
                return att

    for scheduler_name, att in att_rows:
        normalised_name = scheduler_name.strip().lower()
        if normalised_name in {"ours", "our", "our scheduler", "ourscheduler", "team", "team scheduler"}:
            return att
        if "our" in normalised_name:
            return att

    return att_rows[-1][1]


def _passenger_row(passenger: Any) -> dict[str, Any]:
    return {
        "passenger_id": _get(passenger, "passenger_id", "id", default=""),
        "class": _passenger_class(passenger),
        "arrival_time": _get(passenger, "arrival_time", default=""),
        "service_time": _get(passenger, "service_time", default=""),
        "service_start_time": _get(
            passenger,
            "service_start_time",
            "start_time",
            default="",
        ),
        "completion_time": _get(
            passenger,
            "completion_time",
            "finish_time",
            "end_time",
            default="",
        ),
        "turnaround_time": _turnaround_time(passenger),
        "assigned_counter_id": _get(
            passenger,
            "assigned_counter_id",
            "counter_id",
            default="",
        ),
    }


def _passenger_class(passenger: Any) -> str:
    value = _get(passenger, "passenger_class", "class", "class_id", default="")
    if value in CLASS_NAME_BY_VALUE:
        return CLASS_NAME_BY_VALUE[value]

    text = str(value).strip()
    if text in CLASS_NAME_BY_VALUE:
        return CLASS_NAME_BY_VALUE[text]

    lower_text = text.lower()
    aliases = {
        "first": "First",
        "first class": "First",
        "business": "Business",
        "biz": "Business",
        "economy": "Economy",
        "eco": "Economy",
    }
    return aliases.get(lower_text, text)


def _turnaround_time(passenger: Any) -> float:
    value = _get(passenger, "turnaround_time", default=None)
    if value is not None and value != "":
        return _number(value)

    arrival_time = _get(passenger, "arrival_time", default=None)
    completion_time = _get(passenger, "completion_time", "finish_time", "end_time", default=None)
    if arrival_time is not None and completion_time is not None:
        return _number(completion_time) - _number(arrival_time)

    service_start_time = _get(passenger, "service_start_time", "start_time", default=None)
    service_time = _get(passenger, "service_time", default=None)
    if arrival_time is not None and service_start_time is not None and service_time is not None:
        return (_number(service_start_time) + _number(service_time)) - _number(arrival_time)

    passenger_id = _get(passenger, "passenger_id", "id", default="<unknown>")
    raise ValueError(f"Cannot calculate turnaround_time for passenger {passenger_id}")


def _write_dict_csv(path: Path, headers: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow({header: _csv_value(row.get(header, "")) for header in headers})


def _write_att_chart_with_matplotlib(rows: Sequence[Mapping[str, Any]], output_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [str(row["scheduler_name"]) for row in rows]
    atts = [_number(row["ATT"]) for row in rows]

    figure_width = max(7, len(rows) * 1.6)
    fig, ax = plt.subplots(figsize=(figure_width, 4.8))
    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]
    bars = ax.bar(names, atts, color=[colors[index % len(colors)] for index in range(len(rows))])

    ax.set_xlabel("Scheduler")
    ax.set_ylabel("ATT")
    ax.set_title("Average Turnaround Time Comparison")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    y_max = max(atts, default=0)
    ax.set_ylim(0, y_max * 1.18 if y_max > 0 else 1)

    for bar, att in zip(bars, atts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            _format_metric(att),
            ha="center",
            va="bottom",
            fontsize=9,
        )

    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _write_att_chart_with_builtin_png(rows: Sequence[Mapping[str, Any]], output_path: Path) -> None:
    names = [str(row["scheduler_name"]) for row in rows]
    atts = [_number(row["ATT"]) for row in rows]

    width = max(760, 140 + max(1, len(rows)) * 160)
    height = 520
    canvas = bytearray([255] * width * height * 3)

    left = 82
    right = 42
    top = 66
    bottom = 395
    plot_width = width - left - right
    plot_height = bottom - top
    max_att = max(atts, default=0)
    y_limit = max_att * 1.18 if max_att > 0 else 1

    black = (34, 34, 34)
    grey = (226, 226, 226)
    axis_grey = (95, 95, 95)
    colors = [
        (76, 120, 168),
        (245, 133, 24),
        (84, 162, 75),
        (228, 87, 86),
        (114, 183, 178),
        (178, 121, 162),
    ]

    _draw_text_centered(
        canvas,
        width,
        height,
        width // 2,
        24,
        "Average Turnaround Time Comparison",
        black,
        scale=2,
    )

    tick_count = 5
    for tick in range(tick_count + 1):
        value = y_limit * tick / tick_count
        y = bottom - int((value / y_limit) * plot_height)
        _draw_line(canvas, width, height, left, y, width - right, y, grey)
        _draw_text_right(
            canvas,
            width,
            height,
            left - 10,
            y - 5,
            _format_metric(value),
            axis_grey,
            scale=1,
        )

    _draw_line(canvas, width, height, left, top, left, bottom, black)
    _draw_line(canvas, width, height, left, bottom, width - right, bottom, black)
    _draw_text_centered(canvas, width, height, width // 2, height - 26, "Scheduler", black, scale=1)
    _draw_text(canvas, width, height, 18, top + plot_height // 2 - 6, "ATT", black, scale=1)

    if rows:
        group_width = plot_width / len(rows)
        for index, (name, att) in enumerate(zip(names, atts)):
            bar_width = min(88, int(group_width * 0.56))
            center_x = int(left + group_width * index + group_width / 2)
            bar_left = center_x - bar_width // 2
            bar_right = center_x + bar_width // 2
            bar_height = int((max(0.0, att) / y_limit) * plot_height)
            bar_top = bottom - bar_height
            _draw_rect(
                canvas,
                width,
                height,
                bar_left,
                bar_top,
                bar_right,
                bottom,
                colors[index % len(colors)],
            )
            _draw_text_centered(
                canvas,
                width,
                height,
                center_x,
                max(top + 2, bar_top - 17),
                _format_metric(att),
                black,
                scale=1,
            )

            for line_index, label_line in enumerate(_wrap_label(name, max_chars=14, max_lines=2)):
                _draw_text_centered(
                    canvas,
                    width,
                    height,
                    center_x,
                    bottom + 12 + line_index * 13,
                    label_line,
                    black,
                    scale=1,
                )

    _write_png_rgb(output_path, width, height, canvas)


def _draw_rect(
    canvas: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    x0 = max(0, min(width, x0))
    x1 = max(0, min(width, x1))
    y0 = max(0, min(height, y0))
    y1 = max(0, min(height, y1))
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0

    red, green, blue = color
    for y in range(y0, y1):
        row_start = y * width * 3
        for x in range(x0, x1):
            index = row_start + x * 3
            canvas[index:index + 3] = bytes((red, green, blue))


def _draw_line(
    canvas: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    if y0 == y1:
        _draw_rect(canvas, width, height, min(x0, x1), y0, max(x0, x1) + 1, y0 + 1, color)
        return
    if x0 == x1:
        _draw_rect(canvas, width, height, x0, min(y0, y1), x0 + 1, max(y0, y1) + 1, color)
        return

    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x = x0
    y = y0
    while True:
        _draw_rect(canvas, width, height, x, y, x + 1, y + 1, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _draw_text(
    canvas: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
    scale: int = 1,
) -> None:
    cursor_x = x
    for character in text.upper():
        glyph = FONT_5X7.get(character, FONT_5X7["?"])
        for row_index, row in enumerate(glyph):
            for column_index, bit in enumerate(row):
                if bit == "1":
                    _draw_rect(
                        canvas,
                        width,
                        height,
                        cursor_x + column_index * scale,
                        y + row_index * scale,
                        cursor_x + (column_index + 1) * scale,
                        y + (row_index + 1) * scale,
                        color,
                    )
        cursor_x += 6 * scale


def _draw_text_centered(
    canvas: bytearray,
    width: int,
    height: int,
    center_x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
    scale: int = 1,
) -> None:
    _draw_text(canvas, width, height, center_x - _text_width(text, scale) // 2, y, text, color, scale)


def _draw_text_right(
    canvas: bytearray,
    width: int,
    height: int,
    right_x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
    scale: int = 1,
) -> None:
    _draw_text(canvas, width, height, right_x - _text_width(text, scale), y, text, color, scale)


def _text_width(text: str, scale: int = 1) -> int:
    if not text:
        return 0
    return (len(text) * 6 - 1) * scale


def _wrap_label(text: str, max_chars: int, max_lines: int) -> list[str]:
    words = text.split()
    if not words:
        return [text[:max_chars]]

    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word[:max_chars]
        if len(lines) == max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    if not lines:
        lines.append(text[:max_chars])
    return lines[:max_lines]


def _write_png_rgb(path: Path, width: int, height: int, pixels: bytes | bytearray) -> None:
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        row_start = y * stride
        raw.extend(pixels[row_start:row_start + stride])

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png_bytes)


def _get(record: Any, *names: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        for name in names:
            if name in record:
                return record[name]
        return default

    for name in names:
        if hasattr(record, name):
            return getattr(record, name)

    return default


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, Real):
        return float(value)
    return float(str(value).strip())


def _is_number(value: Any) -> bool:
    if isinstance(value, Real):
        return True
    if isinstance(value, str):
        try:
            float(value)
        except ValueError:
            return False
        return True
    return False


def _is_pair(value: Any) -> bool:
    return (
        isinstance(value, tuple | list)
        and len(value) >= 2
        and not isinstance(value[0], Mapping)
    )


def _looks_like_class_summary_row(row: Any) -> bool:
    return (
        _get(row, "passenger_count", "count", default=None) is not None
        and _get(row, "average_turnaround_time", "avg_turnaround_time", "ATT", "att", default=None) is not None
    )


def _looks_like_counter_summary_row(row: Any) -> bool:
    return (
        _get(row, "counter_id", "id", default=None) is not None
        and _get(row, "processed_count", "count", default=None) is not None
        and _get(row, "total_service_time", default=None) is not None
    )


def _looks_like_att_comparison_row(row: Any) -> bool:
    return (
        _get(row, "scheduler_name", "name", "scheduler", default=None) is not None
        and _get(row, "ATT", "att", default=None) is not None
        and _get(row, "improvement_rate", default=None) is not None
    )


def _infer_counter_type(counter_id: Any) -> str:
    text = str(counter_id).upper().replace("COUNTER", "").strip()
    mapping = {
        "1": "First",
        "C1": "First",
        "2": "Business",
        "C2": "Business",
        "3": "Economy",
        "C3": "Economy",
        "4": "Flex",
        "C4": "Flex",
        "5": "Flex",
        "C5": "Flex",
    }
    return mapping.get(text, "")


def _csv_value(value: Any) -> Any:
    if isinstance(value, float):
        return _format_metric(value)
    return value


def _format_metric(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def _sort_key(value: Any) -> tuple[int, Any]:
    if isinstance(value, Real):
        return (0, value)

    text = str(value)
    digits = "".join(character for character in text if character.isdigit())
    if digits:
        return (0, int(digits))
    return (1, text)


FONT_5X7 = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "01100", "00100", "01000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
    "%": ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
}
