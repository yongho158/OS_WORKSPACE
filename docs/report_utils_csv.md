# report_utils.py CSV 생성 코드 설명

## 파일의 역할

이 문서는 `report_utils.py` 중 CSV 생성과 계산 흐름을 초보자 관점에서 자세히 설명한다.

`report_utils.py`의 CSV 관련 코드는 다음 일을 한다.

1. 원본 승객/카운터/스케줄러 결과를 받는다.
2. 필요한 값이 이미 계산되어 있으면 그대로 사용한다.
3. 필요한 값이 없으면 helper 함수로 계산한다.
4. 정해진 헤더 순서대로 CSV 파일에 저장한다.

## 주요 출력 파일

| 파일 | 함수 | 입력 데이터 | 저장되는 내용 |
| --- | --- | --- | --- |
| `output/passenger_results.csv` | `write_passenger_results_csv()` | 승객 목록 | 승객별 처리 결과 |
| `output/class_summary.csv` | `write_class_summary_csv()` | 승객 목록 또는 class summary 목록 | 등급별 승객 수, 평균 turnaround time |
| `output/counter_summary.csv` | `write_counter_summary_csv()` | 카운터 목록 또는 counter summary 목록 | 카운터별 처리 통계 |
| `output/att_comparison.csv` | `write_att_comparison_csv()` | 스케줄러 결과 또는 ATT 비교표 | 스케줄러별 ATT, 개선율 |

## 코드 설명

### CSV 헤더 상수

CSV는 열 이름과 열 순서가 중요하다. 그래서 파일 위쪽에 헤더 목록을 상수로 정의한다.

```python
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
```

이 목록은 `passenger_results.csv`의 열 순서가 된다.

```python
CLASS_SUMMARY_HEADERS = [
    "class",
    "passenger_count",
    "average_turnaround_time",
]
```

등급별 요약은 등급 이름, 승객 수, 평균 turnaround time만 저장한다.

```python
COUNTER_SUMMARY_HEADERS = [
    "counter_id",
    "counter_type",
    "processed_count",
    "total_service_time",
    "idle_time",
]
```

카운터별 요약은 카운터 ID, 카운터 타입, 처리한 승객 수, 총 서비스 시간, 쉬고 있던 시간을 저장한다.

```python
ATT_COMPARISON_HEADERS = [
    "scheduler_name",
    "ATT",
    "improvement_rate",
]
```

ATT 비교 CSV는 스케줄러 이름, ATT, 개선율을 저장한다.

### 출력 폴더 만들기

```python
def ensure_output_dir(output_dir: str | Path = "output") -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
```

`Path(output_dir)`는 문자열 경로를 `Path` 객체로 바꾼다.

`path.mkdir(parents=True, exist_ok=True)`의 의미는 다음과 같다.

| 옵션 | 의미 |
| --- | --- |
| `parents=True` | 중간 폴더가 없어도 함께 만든다 |
| `exist_ok=True` | 이미 폴더가 있어도 에러를 내지 않는다 |

이 함수가 `Path`를 반환하기 때문에 아래처럼 `/` 연산자로 파일명을 붙일 수 있다.

```python
output_path = ensure_output_dir(output_dir) / "passenger_results.csv"
```

## CSV 저장 함수 설명

### 1. 승객별 CSV: write_passenger_results_csv

```python
def write_passenger_results_csv(
    passengers: Iterable[Any],
    output_dir: str | Path = "output",
) -> Path:
    output_path = ensure_output_dir(output_dir) / "passenger_results.csv"
    rows = [_passenger_row(passenger) for passenger in passengers]
    rows.sort(key=lambda row: _sort_key(row["passenger_id"]))
    _write_dict_csv(output_path, PASSENGER_HEADERS, rows)
    return output_path
```

한 줄씩 보면 다음과 같다.

```python
output_path = ensure_output_dir(output_dir) / "passenger_results.csv"
```

출력 폴더를 만들고, 그 안의 `passenger_results.csv` 경로를 만든다.

```python
rows = [_passenger_row(passenger) for passenger in passengers]
```

승객 객체나 딕셔너리 목록을 CSV에 저장하기 좋은 딕셔너리 목록으로 바꾼다.

```python
rows.sort(key=lambda row: _sort_key(row["passenger_id"]))
```

승객 ID 기준으로 정렬한다. `_sort_key()`를 쓰는 이유는 `1`, `2`, `10` 같은 숫자 정렬과 `P01`, `P02` 같은 문자열 ID를 함께 다루기 위해서다.

```python
_write_dict_csv(output_path, PASSENGER_HEADERS, rows)
```

실제 파일 쓰기는 공통 helper인 `_write_dict_csv()`에 맡긴다.

`_passenger_row()`는 승객 하나를 다음 모양의 딕셔너리로 바꾼다.

```python
def _passenger_row(passenger: Any) -> dict[str, Any]:
    return {
        "passenger_id": _get(passenger, "passenger_id", "id", default=""),
        "class": _passenger_class(passenger),
        "arrival_time": _get(passenger, "arrival_time", default=""),
        "service_time": _get(passenger, "service_time", default=""),
        "service_start_time": _get(passenger, "service_start_time", "start_time", default=""),
        "completion_time": _get(passenger, "completion_time", "finish_time", "end_time", default=""),
        "turnaround_time": _turnaround_time(passenger),
        "assigned_counter_id": _get(passenger, "assigned_counter_id", "counter_id", default=""),
    }
```

`_get(passenger, "passenger_id", "id", default="")`는 `passenger_id`라는 이름이 있으면 쓰고, 없으면 `id`라는 이름을 찾아본다. 둘 다 없으면 빈 문자열을 쓴다.

이렇게 하는 이유는 입력 데이터가 항상 같은 이름을 쓰지 않을 수 있기 때문이다.

### 2. class summary CSV: write_class_summary_csv

```python
def write_class_summary_csv(
    passengers_or_summary: Iterable[Any],
    output_dir: str | Path = "output",
) -> Path:
    output_path = ensure_output_dir(output_dir) / "class_summary.csv"
    rows = _normalise_class_summary(passengers_or_summary)
    _write_dict_csv(output_path, CLASS_SUMMARY_HEADERS, rows)
    return output_path
```

이 함수의 핵심은 `_normalise_class_summary()`다.

입력이 두 종류일 수 있기 때문이다.

1. 원본 승객 목록
2. 이미 계산된 class summary 목록

`_normalise_class_summary()`는 먼저 전체 입력을 리스트로 바꾼다.

```python
rows = list(rows_or_passengers)
if not rows:
    return []
```

`Iterable`은 한 번만 반복 가능한 경우도 있다. 그래서 `list()`로 바꿔두면 여러 번 검사할 수 있다.

그 다음 각 행이 이미 summary처럼 생겼는지 확인한다.

```python
if all(_looks_like_class_summary_row(row) for row in rows):
    ...
```

`all(...)`은 안의 조건이 모두 참이면 참이다.

`_looks_like_class_summary_row()`는 `passenger_count`와 `average_turnaround_time` 같은 값이 있는지 본다.

이미 summary라면 필요한 열 이름으로 정리한다.

```python
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
```

summary가 아니라면 원본 승객 목록으로 보고 `calculate_class_summary()`를 호출한다.

```python
return calculate_class_summary(rows)
```

`calculate_class_summary()`의 계산 흐름은 다음과 같다.

```python
groups = OrderedDict()

for passenger in passengers:
    passenger_class = _passenger_class(passenger)
    groups.setdefault(passenger_class, []).append(_turnaround_time(passenger))
```

등급별로 turnaround time을 모은다.

```python
rows = [
    {
        "class": passenger_class,
        "passenger_count": len(turnaround_times),
        "average_turnaround_time": sum(turnaround_times) / len(turnaround_times),
    }
    for passenger_class, turnaround_times in groups.items()
]
```

각 등급별 승객 수와 평균을 만든다.

```python
rows.sort(key=lambda row: (CLASS_ORDER.get(str(row["class"]), 99), str(row["class"])))
```

정렬 기준은 `First`, `Business`, `Economy` 순서다. 모르는 등급은 `99`가 되어 뒤로 간다.

### 3. counter summary CSV: write_counter_summary_csv

```python
def write_counter_summary_csv(
    counters_or_summary: Iterable[Any],
    output_dir: str | Path = "output",
) -> Path:
    output_path = ensure_output_dir(output_dir) / "counter_summary.csv"
    rows = _normalise_counter_summary(counters_or_summary)
    _write_dict_csv(output_path, COUNTER_SUMMARY_HEADERS, rows)
    return output_path
```

class summary와 구조가 비슷하다. 입력이 원본 카운터 목록인지 이미 계산된 summary인지 판단한다.

원본 카운터 목록이면 `calculate_counter_summary()`를 사용한다.

```python
for counter in counters:
    processed_passengers = _get(counter, "processed_passengers", default=None)
    processed_count = _get(counter, "processed_count", default=None)
    if processed_count is None:
        processed_count = len(processed_passengers or [])
```

`processed_count`가 있으면 그대로 쓰고, 없으면 `processed_passengers` 목록 길이를 사용한다.

```python
total_service_time = _get(counter, "total_service_time", default=None)
if total_service_time is None:
    total_service_time = sum(
        _number(_get(passenger, "service_time", default=0))
        for passenger in (processed_passengers or [])
    )
```

`total_service_time`이 없으면 처리한 승객들의 `service_time`을 모두 더한다.

```python
counter_type = _get(counter, "counter_type", "type", default=None)
```

카운터 타입은 `counter_type` 또는 `type` 이름으로 찾는다.

```python
"counter_type": counter_type if counter_type is not None else _infer_counter_type(counter_id)
```

카운터 타입이 없으면 카운터 ID로 추정한다. 예를 들어 `C1`은 `First`, `C4`는 `Flex`로 추정한다.

### 4. ATT comparison CSV: write_att_comparison_csv

```python
def write_att_comparison_csv(
    scheduler_results_or_comparison: Mapping[str, Any] | Iterable[Any],
    output_dir: str | Path = "output",
    our_scheduler_name: str | None = None,
) -> Path:
    output_path = ensure_output_dir(output_dir) / "att_comparison.csv"
    rows = _normalise_att_comparison(scheduler_results_or_comparison, our_scheduler_name)
    _write_dict_csv(output_path, ATT_COMPARISON_HEADERS, rows)
    return output_path
```

입력은 크게 두 종류다.

1. 이미 계산된 ATT 비교 행
2. 아직 ATT를 뽑아야 하는 스케줄러 실행 결과

`_normalise_att_comparison()`은 입력이 `Mapping`인지 먼저 확인한다.

```python
if isinstance(rows_or_results, Mapping):
    rows = list(rows_or_results.values())
    if rows and all(_looks_like_att_comparison_row(row) for row in rows):
        return _normalise_att_rows(rows)
    return calculate_att_comparison(rows_or_results, our_scheduler_name)
```

`Mapping`은 딕셔너리 같은 자료형이다.

예:

```python
{
    "fcfs": result1,
    "priority": result2,
    "sjf": result3,
    "ours": result4,
}
```

이미 비교표처럼 생겼으면 `_normalise_att_rows()`로 열 이름과 숫자 형식을 통일한다. 아니라면 `calculate_att_comparison()`으로 계산한다.

## ATT 계산 흐름

### calculate_att

```python
def calculate_att(passengers: Iterable[Any]) -> float:
    passenger_list = list(passengers)
    if not passenger_list:
        return 0.0
    total_turnaround_time = sum(_turnaround_time(passenger) for passenger in passenger_list)
    return total_turnaround_time / len(passenger_list)
```

`passenger_list = list(passengers)`는 입력을 리스트로 바꾼다. 그래야 `len(passenger_list)`로 개수를 셀 수 있다.

승객이 없으면 0으로 반환한다.

```python
total_turnaround_time = sum(_turnaround_time(passenger) for passenger in passenger_list)
```

각 승객의 turnaround time을 구해서 모두 더한다.

마지막으로 평균을 낸다.

```python
return total_turnaround_time / len(passenger_list)
```

### _turnaround_time

```python
value = _get(passenger, "turnaround_time", default=None)
if value is not None and value != "":
    return _number(value)
```

이미 `turnaround_time`이 있으면 그 값을 사용한다.

없으면 `completion_time - arrival_time`으로 계산한다.

```python
arrival_time = _get(passenger, "arrival_time", default=None)
completion_time = _get(passenger, "completion_time", "finish_time", "end_time", default=None)
if arrival_time is not None and completion_time is not None:
    return _number(completion_time) - _number(arrival_time)
```

`completion_time`도 없으면 `service_start_time + service_time - arrival_time`으로 계산한다.

```python
service_start_time = _get(passenger, "service_start_time", "start_time", default=None)
service_time = _get(passenger, "service_time", default=None)
if arrival_time is not None and service_start_time is not None and service_time is not None:
    return (_number(service_start_time) + _number(service_time)) - _number(arrival_time)
```

셋 다 안 되면 계산할 수 없으므로 에러를 낸다.

```python
raise ValueError(f"Cannot calculate turnaround_time for passenger {passenger_id}")
```

### calculate_att_comparison

```python
att_rows = _normalise_scheduler_results(scheduler_results)
if not att_rows:
    return []

comparison_att = _select_comparison_att(att_rows, our_scheduler_name)
```

먼저 여러 형태의 스케줄러 결과를 `(scheduler_name, att)` 목록으로 통일한다. 그리고 비교 기준이 되는 ATT를 고른다.

```python
for scheduler_name, att in att_rows:
    improvement_rate = 0.0
    if att:
        improvement_rate = (att - comparison_att) / att * 100
```

각 스케줄러의 ATT와 우리 스케줄러 ATT를 비교한다.

```text
개선율 = (비교 대상 ATT - 우리 ATT) / 비교 대상 ATT * 100
```

예를 들어 `fcfs` ATT가 20, `ours` ATT가 18이면 개선율은 10%다.

## class summary 계산 흐름

class summary는 등급별로 승객을 묶고 평균을 낸다.

```text
승객 목록
-> 승객마다 class 이름 확인
-> class별 turnaround_time 목록 만들기
-> class별 passenger_count 계산
-> class별 average_turnaround_time 계산
-> First, Business, Economy 순서로 정렬
-> class_summary.csv 저장
```

`CLASS_NAME_BY_VALUE`가 필요한 이유는 입력 등급이 `1`, `"1"`, `"first"`, `"First"`처럼 다르게 들어올 수 있기 때문이다. `_passenger_class()`가 이런 값을 `First`, `Business`, `Economy`로 통일한다.

## counter summary 계산 흐름

counter summary는 카운터별 처리량과 시간을 모은다.

```text
카운터 목록
-> processed_count 확인
-> 없으면 processed_passengers 길이로 계산
-> total_service_time 확인
-> 없으면 처리 승객들의 service_time 합계로 계산
-> idle_time 확인
-> counter_type 확인
-> 없으면 counter_id로 추정
-> counter_id 순서로 정렬
-> counter_summary.csv 저장
```

`_infer_counter_type()`은 카운터 ID만 있는 경우를 대비한다.

```python
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
```

## att comparison 계산 흐름

ATT 비교는 입력이 다양해서 helper가 많다.

```text
scheduler_results
-> _normalise_scheduler_results()
-> [(scheduler_name, ATT), ...]
-> _select_comparison_att()
-> 기준 ATT 선택
-> calculate_att_comparison()
-> [{"scheduler_name": ..., "ATT": ..., "improvement_rate": ...}, ...]
-> write_att_comparison_csv()
-> att_comparison.csv 저장
```

`_normalise_scheduler_results()`는 딕셔너리 입력이면 key를 스케줄러 이름으로 사용한다.

```python
if isinstance(scheduler_results, Mapping):
    return [
        (str(scheduler_name), _att_from_result(result))
        for scheduler_name, result in scheduler_results.items()
    ]
```

`_att_from_result()`는 ATT를 찾는 순서가 있다.

1. 결과 자체가 숫자면 그 숫자를 ATT로 사용한다.
2. 결과에 `ATT`, `att`, `average_turnaround_time` 속성/키가 있으면 사용한다.
3. 결과에 `passengers`, `passenger_results`, `completed_passengers`가 있으면 그 승객 목록으로 ATT를 계산한다.
4. 마지막으로 결과 자체를 승객 목록으로 보고 ATT를 계산한다.

## matplotlib 그래프 생성 설명

CSV 문서의 중심은 파일 저장이다. 그래프 생성은 `docs/report_utils_png.md`에서 자세히 설명한다.

간단히 말하면 `write_att_comparison_png()`는 같은 ATT 비교 데이터를 사용해서 `att_comparison.png`를 만든다. 먼저 matplotlib을 시도하고, matplotlib import가 실패하면 내장 PNG 생성 함수로 넘어간다.

## 내장 PNG 생성 fallback 설명

fallback 그래프 생성은 CSV 저장과 직접 관련은 없지만 같은 ATT 비교 행을 입력으로 사용한다.

CSV는 텍스트 파일이고 PNG는 바이너리 이미지 파일이다. CSV는 `csv.DictWriter`로 행을 쓰지만, fallback PNG는 `bytearray`에 픽셀 색을 직접 채운 뒤 `struct`, `zlib`로 PNG 파일 구조를 만든다.

## 초보자가 헷갈릴 수 있는 문법

### `_get()`

```python
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
```

초보자 입장에서 이 함수가 중요한 이유는 "딕셔너리와 객체를 같은 방식으로 읽기 위해서"다.

딕셔너리는 이렇게 읽는다.

```python
row["arrival_time"]
```

객체는 이렇게 읽는다.

```python
passenger.arrival_time
```

`_get()`을 쓰면 둘을 구분하지 않아도 된다.

### `_number()`

```python
def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, Real):
        return float(value)
    return float(str(value).strip())
```

CSV나 딕셔너리에서 읽은 값은 문자열일 수 있다. `"12.5"`도 계산하려면 숫자로 바꿔야 한다. `_number()`는 `None`, 빈 문자열, 정수, 실수, 숫자 문자열을 모두 float로 정리한다.

### `_sort_key()`

```python
def _sort_key(value: Any) -> tuple[int, Any]:
    if isinstance(value, Real):
        return (0, value)

    text = str(value)
    digits = "".join(character for character in text if character.isdigit())
    if digits:
        return (0, int(digits))
    return (1, text)
```

문자열 정렬만 하면 `"10"`이 `"2"`보다 앞에 올 수 있다. `_sort_key()`는 문자열 안의 숫자를 뽑아 정렬에 사용한다.

예:

```text
"P2" -> 2
"P10" -> 10
```

그래서 `P2`가 `P10`보다 먼저 온다.

### `with open`

```python
with path.open("w", newline="", encoding="utf-8-sig") as file:
    ...
```

파일을 열고 자동으로 닫는다. CSV 저장에서 거의 항상 권장되는 형태다.

### `csv.DictWriter`

```python
writer = csv.DictWriter(file, fieldnames=list(headers))
writer.writeheader()
writer.writerow(...)
```

딕셔너리의 key를 CSV 열 이름으로 사용한다.

### dictionary comprehension

```python
{header: _csv_value(row.get(header, "")) for header in headers}
```

딕셔너리를 짧게 만드는 문법이다. 반복문으로 쓰면 아래와 같다.

```python
new_row = {}
for header in headers:
    new_row[header] = _csv_value(row.get(header, ""))
```

### generator expression

```python
sum(_turnaround_time(passenger) for passenger in passenger_list)
```

리스트를 따로 만들지 않고, 반복하면서 바로 `sum()`에 값을 넘긴다.

## 다른 파일과의 관계

현재 `scheduler.py`는 CSV를 `report_utils.py`의 CSV 함수로 쓰지 않고 자체 helper로 생성한다.

`scheduler.py`의 CSV 함수는 다음과 같다.

| scheduler.py 함수 | 생성 파일 |
| --- | --- |
| `_write_passenger_results()` | `passenger_results.csv`, `{scheduler}_passenger_results.csv` |
| `_write_class_summary()` | `class_summary.csv`, `{scheduler}_class_summary.csv` |
| `_write_counter_summary()` | `counter_summary.csv`, `{scheduler}_counter_summary.csv` |
| `_write_att_comparison()` | `att_comparison.csv` |

그래서 실제 CLI 실행 결과의 CSV 헤더는 `report_utils.py`의 헤더와 일부 다를 수 있다. 예를 들어 `scheduler.py`가 쓰는 `passenger_results.csv`에는 `class_name`이 들어가지만, `report_utils.py`의 `PASSENGER_HEADERS`에는 `class_name`이 없다.

반면 `report_utils.py`의 `generate_reports()`를 직접 사용하면 이 파일의 CSV 함수들이 모두 호출된다.

```python
generate_reports(
    passengers=passengers,
    counters=counters,
    scheduler_results=results,
    output_dir="output",
    our_scheduler_name="ours",
)
```

현재 프로젝트에서 `report_utils.py`를 직접 import하는 실제 코드는 `scheduler.py`의 이 부분이다.

```python
from report_utils import write_att_comparison_png
```

즉 CSV 생성 유틸리티는 준비되어 있지만, 현재 기본 실행 흐름에서는 PNG 그래프 생성 함수만 직접 재사용되고 있다.

