# report_utils.py 초보자용 설명

## 파일의 역할

`report_utils.py`는 시뮬레이션이 끝난 뒤 결과 데이터를 사람이 읽기 좋은 파일로 바꾸는 유틸리티 파일이다.

주요 역할은 네 가지다.

1. 승객별 결과를 CSV로 저장한다.
2. 좌석 등급별 평균 turnaround time을 계산하고 CSV로 저장한다.
3. 카운터별 처리 통계를 계산하고 CSV로 저장한다.
4. 스케줄러별 ATT(Average Turnaround Time)를 비교해 CSV와 PNG 막대그래프로 저장한다.

여기서 ATT는 전체 승객의 `turnaround_time` 평균이다.

```text
turnaround_time = completion_time - arrival_time
ATT = 모든 승객 turnaround_time의 평균
```

이 파일은 특정 클래스(`Passenger`, `Counter`, `SimulationResult`)에만 강하게 묶이지 않도록 만들어져 있다. 딕셔너리, 객체, 튜플, 이미 계산된 요약 행 등 여러 형태의 데이터를 받아서 내부 helper 함수로 정리한 뒤 저장한다.

## 주요 출력 파일

`report_utils.py`가 직접 생성하도록 설계된 출력 파일은 다음과 같다.

| 파일 | 생성 함수 | 내용 |
| --- | --- | --- |
| `output/passenger_results.csv` | `write_passenger_results_csv()` | 승객별 도착, 서비스 시작, 완료, turnaround time, 배정 카운터 |
| `output/class_summary.csv` | `write_class_summary_csv()` | 등급별 승객 수와 평균 turnaround time |
| `output/counter_summary.csv` | `write_counter_summary_csv()` | 카운터별 처리 수, 총 서비스 시간, idle time |
| `output/att_comparison.csv` | `write_att_comparison_csv()` | 스케줄러별 ATT와 개선율 |
| `output/att_comparison.png` | `write_att_comparison_png()` | 스케줄러별 ATT 막대그래프 |

주의할 점이 있다. 현재 프로젝트의 CLI 실행 흐름에서는 `scheduler.py`가 CSV 파일을 자체 함수로 생성하고, `report_utils.py`에서는 `write_att_comparison_png()`만 직접 가져와 사용한다. 즉 `report_utils.py`의 CSV 함수들은 재사용 가능한 별도 유틸리티로 존재하지만, 현재 `scheduler.py`의 기본 실행에서는 CSV 저장에 직접 호출되지 않는다.

## 코드 설명

### import 구문

파일 앞부분은 필요한 표준 라이브러리와 타입 힌트를 가져온다.

```python
from __future__ import annotations

import csv
import struct
import zlib
from collections import OrderedDict
from numbers import Real
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
```

`from __future__ import annotations`는 타입 힌트를 즉시 평가하지 않고 문자열처럼 늦게 처리하게 해준다. 예를 들어 `str | Path` 같은 타입 표기를 더 편하게 쓸 수 있다.

`csv`는 CSV 파일을 쓰기 위해 사용한다. 이 파일에서는 `csv.DictWriter`로 딕셔너리 데이터를 행 단위로 저장한다.

`struct`와 `zlib`는 fallback PNG 생성에 사용한다. `matplotlib`이 없을 때 직접 PNG 파일 구조를 만들기 위해 바이너리 데이터를 포장하고 압축한다.

`OrderedDict`는 입력 순서를 유지하는 딕셔너리다. Python 3.7 이후 일반 `dict`도 순서를 유지하지만, 이 코드는 "순서 유지가 중요하다"는 의도를 분명하게 보여주기 위해 `OrderedDict`를 사용한다.

`Real`은 숫자인지 확인할 때 사용한다. `int`, `float`처럼 실제 숫자 타입이면 `isinstance(value, Real)`이 참이 된다.

`Path`는 파일 경로를 문자열보다 안전하고 읽기 좋게 다루기 위한 클래스다.

`Any`, `Iterable`, `Mapping`, `Sequence`는 타입 힌트다.

| 타입 힌트 | 쉬운 의미 |
| --- | --- |
| `Any` | 어떤 타입이든 올 수 있음 |
| `Iterable[Any]` | 반복할 수 있는 값. 예: list, tuple, generator |
| `Mapping[str, Any]` | 딕셔너리처럼 key로 값을 찾을 수 있는 값 |
| `Sequence[...]` | 순서가 있고 인덱스로 접근 가능한 값. 예: list, tuple |

### 상수 목록

상수는 여러 함수에서 공통으로 쓰는 고정값이다.

```python
CLASS_NAME_BY_VALUE = {
    1: "First",
    2: "Business",
    3: "Economy",
    "1": "First",
    "2": "Business",
    "3": "Economy",
}
```

승객 등급이 숫자 `1`, `2`, `3`으로 들어올 수도 있고 문자열 `"1"`, `"2"`, `"3"`으로 들어올 수도 있다. 이 상수는 둘 다 사람이 읽기 쉬운 이름으로 바꿔준다.

```python
CLASS_ORDER = {
    "First": 1,
    "Business": 2,
    "Economy": 3,
}
```

등급별 요약을 정렬할 때 `First`, `Business`, `Economy` 순서로 보이게 하기 위한 기준이다.

CSV 헤더 상수들은 파일의 열 순서를 고정한다.

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

`csv.DictWriter`는 `fieldnames`에 적힌 순서대로 열을 쓴다. 그래서 헤더를 상수로 빼두면 함수마다 열 순서가 흔들리지 않는다.

나머지 헤더도 같은 목적이다.

| 상수 | 사용 파일 |
| --- | --- |
| `CLASS_SUMMARY_HEADERS` | `class_summary.csv` |
| `COUNTER_SUMMARY_HEADERS` | `counter_summary.csv` |
| `ATT_COMPARISON_HEADERS` | `att_comparison.csv` |

### 공개 함수와 내부 helper 함수

Python에서는 이름 앞에 `_`가 붙은 함수는 관례적으로 "파일 내부에서만 쓰는 helper"라는 뜻이다. 강제로 막히는 것은 아니지만, 다른 파일에서는 되도록 호출하지 말라는 신호다.

공개 함수는 다음과 같다.

| 함수 | 역할 |
| --- | --- |
| `ensure_output_dir()` | 출력 폴더 생성 |
| `calculate_att()` | 전체 ATT 계산 |
| `calculate_class_summary()` | 등급별 요약 계산 |
| `calculate_counter_summary()` | 카운터별 요약 계산 |
| `calculate_att_comparison()` | 스케줄러별 ATT 비교표 계산 |
| `write_passenger_results_csv()` | 승객별 CSV 저장 |
| `write_class_summary_csv()` | 등급별 CSV 저장 |
| `write_counter_summary_csv()` | 카운터별 CSV 저장 |
| `write_att_comparison_csv()` | ATT 비교 CSV 저장 |
| `write_att_comparison_png()` | ATT 비교 PNG 그래프 저장 |
| `generate_reports()` | CSV와 PNG 전체 생성 |

호환용 별칭도 있다.

```python
create_reports = generate_reports
generate_all_reports = generate_reports
export_reports = generate_reports
calculate_average_turnaround_time = calculate_att
save_passenger_results_csv = write_passenger_results_csv
plot_att_comparison = write_att_comparison_png
```

이런 별칭은 다른 코드나 테스트가 예전 함수명을 기대해도 같은 기능을 사용할 수 있게 해준다.

내부 helper 함수는 데이터를 정리하거나 실제 저장 세부 작업을 담당한다.

| helper | 역할 |
| --- | --- |
| `_normalise_class_summary()` | 원본 승객 목록인지 이미 계산된 class summary인지 판단해 통일 |
| `_normalise_counter_summary()` | 원본 카운터 목록인지 이미 계산된 counter summary인지 판단해 통일 |
| `_normalise_att_comparison()` | ATT 비교 입력을 통일 |
| `_normalise_scheduler_results()` | 스케줄러 결과를 `(이름, ATT)` 목록으로 통일 |
| `_att_from_result()` | 숫자, 결과 객체, 승객 목록 등에서 ATT 추출 |
| `_select_comparison_att()` | 개선율 계산 기준이 되는 우리 스케줄러 ATT 선택 |
| `_passenger_row()` | 승객 객체/딕셔너리를 CSV 한 행으로 변환 |
| `_passenger_class()` | 등급 값을 `First`, `Business`, `Economy`로 변환 |
| `_turnaround_time()` | 승객의 turnaround time 계산 |
| `_write_dict_csv()` | 딕셔너리 목록을 CSV로 저장 |
| `_write_att_chart_with_matplotlib()` | matplotlib으로 PNG 그래프 저장 |
| `_write_att_chart_with_builtin_png()` | matplotlib 없이 직접 PNG 저장 |
| `_draw_rect()`, `_draw_line()`, `_draw_text()` | fallback PNG에 도형과 글자를 그림 |
| `_write_png_rgb()` | RGB 픽셀 배열을 PNG 파일로 저장 |
| `_get()` | 딕셔너리와 객체에서 같은 방식으로 값 읽기 |
| `_number()` | 문자열/숫자를 float로 변환 |
| `_sort_key()` | 숫자 ID와 문자열 ID를 자연스럽게 정렬 |

## CSV 저장 함수 설명

### 출력 폴더 생성

```python
def ensure_output_dir(output_dir: str | Path = "output") -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
```

`output_dir`가 문자열이어도 `Path` 객체로 바꾼다. `mkdir(parents=True, exist_ok=True)`는 중간 폴더까지 만들고, 이미 폴더가 있어도 에러를 내지 않는다.

### 승객별 CSV

```python
def write_passenger_results_csv(passengers, output_dir="output") -> Path:
    output_path = ensure_output_dir(output_dir) / "passenger_results.csv"
    rows = [_passenger_row(passenger) for passenger in passengers]
    rows.sort(key=lambda row: _sort_key(row["passenger_id"]))
    _write_dict_csv(output_path, PASSENGER_HEADERS, rows)
    return output_path
```

흐름은 간단하다.

1. `output/passenger_results.csv` 경로를 만든다.
2. 각 승객을 `_passenger_row()`로 CSV 한 행 딕셔너리로 바꾼다.
3. `passenger_id` 기준으로 정렬한다.
4. `_write_dict_csv()`로 저장한다.
5. 생성한 파일 경로를 반환한다.

`[_passenger_row(passenger) for passenger in passengers]`는 list comprehension이다. 반복문으로 쓰면 아래와 같은 의미다.

```python
rows = []
for passenger in passengers:
    rows.append(_passenger_row(passenger))
```

### class summary

```python
def calculate_class_summary(passengers):
    groups = OrderedDict()

    for passenger in passengers:
        passenger_class = _passenger_class(passenger)
        groups.setdefault(passenger_class, []).append(_turnaround_time(passenger))
```

`groups`는 등급별 turnaround time 목록이다.

```text
{
  "First": [12, 17, 30],
  "Business": [9, 21],
  "Economy": [7, 5, 4]
}
```

`setdefault(passenger_class, [])`는 해당 등급 key가 없으면 빈 리스트를 만들어 넣고, 이미 있으면 기존 리스트를 반환한다. 그 뒤 `.append()`로 turnaround time을 추가한다.

이후 각 등급별 평균을 만든다.

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

`write_class_summary_csv()`는 입력이 원본 승객 목록일 수도 있고 이미 계산된 summary 목록일 수도 있다고 보고 `_normalise_class_summary()`로 정리한 뒤 저장한다.

### counter summary

```python
processed_passengers = _get(counter, "processed_passengers", default=None)
processed_count = _get(counter, "processed_count", default=None)
if processed_count is None:
    processed_count = len(processed_passengers or [])
```

카운터 객체에 `processed_count`가 있으면 그대로 쓰고, 없으면 `processed_passengers` 목록 길이로 계산한다.

```python
total_service_time = _get(counter, "total_service_time", default=None)
if total_service_time is None:
    total_service_time = sum(
        _number(_get(passenger, "service_time", default=0))
        for passenger in (processed_passengers or [])
    )
```

총 서비스 시간도 이미 있으면 그대로 쓰고, 없으면 처리한 승객들의 `service_time`을 합산한다.

`write_counter_summary_csv()`는 `_normalise_counter_summary()`를 통해 원본 카운터 목록과 이미 계산된 요약 목록을 둘 다 처리한다.

### ATT comparison CSV

`calculate_att_comparison()`의 핵심 계산식은 다음과 같다.

```python
improvement_rate = (att - comparison_att) / att * 100
```

여기서 `comparison_att`는 보통 우리 스케줄러의 ATT다. 기준 스케줄러 ATT가 20이고 우리 스케줄러 ATT가 18이면 다음처럼 계산된다.

```text
(20 - 18) / 20 * 100 = 10%
```

즉 양수면 우리 스케줄러가 해당 스케줄러보다 ATT를 줄였다는 뜻이다. 반대로 음수면 우리 스케줄러의 ATT가 더 크다는 뜻이다.

`write_att_comparison_csv()`는 계산된 비교표 또는 원본 스케줄러 결과를 받아서 `output/att_comparison.csv`로 저장한다.

### 실제 CSV 쓰기

```python
def _write_dict_csv(path: Path, headers: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow({header: _csv_value(row.get(header, "")) for header in headers})
```

`with path.open(...) as file:`은 파일을 열고, 블록이 끝나면 자동으로 닫는다. 중간에 에러가 나도 파일을 닫아주기 때문에 안전하다.

`newline=""`은 CSV 저장 시 빈 줄이 끼는 문제를 막기 위해 자주 사용한다.

`encoding="utf-8-sig"`는 Excel에서 UTF-8 CSV를 더 잘 인식하게 하려고 BOM이 붙은 UTF-8로 저장한다.

`csv.DictWriter`는 딕셔너리를 CSV 행으로 저장하는 도구다. `fieldnames`에 적힌 열만, 그 순서대로 저장한다.

## matplotlib 그래프 생성 설명

`write_att_comparison_png()`는 먼저 matplotlib 방식으로 그래프를 만들려고 시도한다.

```python
try:
    _write_att_chart_with_matplotlib(rows, output_path)
except ImportError:
    _write_att_chart_with_builtin_png(rows, output_path)
```

`try/except`는 "일단 해보고, 특정 에러가 나면 다른 방법을 실행"하는 문법이다. 여기서는 `matplotlib` import에 실패하면 fallback 내장 PNG 생성 함수를 사용한다.

matplotlib 함수는 다음 흐름으로 동작한다.

1. `matplotlib.use("Agg")`로 화면 없이 이미지 파일을 만들 수 있게 설정한다.
2. `names`에는 스케줄러 이름을 담는다.
3. `atts`에는 각 스케줄러의 ATT 숫자를 담는다.
4. `ax.bar()`로 막대그래프를 그린다.
5. x축, y축, 제목, grid를 설정한다.
6. 각 막대 위에 ATT 값을 텍스트로 적는다.
7. `fig.savefig(output_path, dpi=160)`로 PNG 파일을 저장한다.
8. `plt.close(fig)`로 메모리를 정리한다.

## 내장 PNG 생성 fallback 설명

fallback 함수는 matplotlib 없이 직접 PNG 파일을 만든다.

```python
canvas = bytearray([255] * width * height * 3)
```

이미지는 픽셀의 모음이다. RGB 이미지는 한 픽셀마다 빨강, 초록, 파랑 3개 값이 필요하다. 그래서 전체 크기는 `width * height * 3`이다.

`255`는 흰색이다. 처음에는 전체 캔버스를 흰색으로 채운다.

그 뒤 `_draw_line()`, `_draw_rect()`, `_draw_text()`로 축, grid, 막대, 글자를 직접 그린다. 마지막에 `_write_png_rgb()`가 이 픽셀 데이터를 PNG 규격에 맞는 bytes로 바꿔 파일에 쓴다.

fallback 방식은 외부 라이브러리가 없어도 동작한다는 장점이 있다. 대신 matplotlib보다 글꼴, 레이아웃, 그래픽 품질은 단순하다.

## 초보자가 헷갈릴 수 있는 문법

### 타입 힌트의 `|`.

```python
output_dir: str | Path = "output"
```

`str | Path`는 `str` 또는 `Path`가 올 수 있다는 뜻이다.

### `Iterable`

```python
def calculate_att(passengers: Iterable[Any]) -> float:
```

`Iterable`은 `for passenger in passengers:`처럼 반복할 수 있는 값이다. 리스트뿐 아니라 튜플, generator도 가능하다.

### `Mapping`

```python
def calculate_att_comparison(scheduler_results: Mapping[str, Any] | Iterable[Any])
```

`Mapping`은 딕셔너리처럼 `key -> value` 구조를 가진 값이다.

예:

```python
{
    "fcfs": result1,
    "ours": result2,
}
```

### `Sequence`

`Sequence`는 순서가 있고 길이를 알 수 있으며 인덱스로 접근 가능한 자료형이다. `list`와 `tuple`이 대표적이다.

### `OrderedDict`

```python
groups: "OrderedDict[str, list[float]]" = OrderedDict()
```

등급이 처음 등장한 순서를 유지하면서 데이터를 모으려는 의도다.

### `try/except`

```python
try:
    import matplotlib
except ImportError:
    ...
```

에러가 날 수 있는 코드를 `try` 안에 넣고, 특정 에러가 발생했을 때 대체 동작을 `except`에 쓴다.

### `with open`

```python
with path.open("w", newline="", encoding="utf-8-sig") as file:
    ...
```

파일을 열고 자동으로 닫는 문법이다.

### `csv.DictWriter`

```python
writer = csv.DictWriter(file, fieldnames=list(headers))
writer.writeheader()
writer.writerow(row)
```

딕셔너리를 CSV 한 행으로 저장한다. `fieldnames`는 열 이름과 열 순서를 정한다.

### list comprehension

```python
atts = [_number(row["ATT"]) for row in rows]
```

반복문으로 리스트를 만드는 짧은 문법이다.

### `bytes`와 `bytearray`

`bytes`는 변경할 수 없는 바이너리 데이터다. `bytearray`는 변경 가능한 바이너리 데이터다.

fallback PNG 생성에서는 픽셀 색을 계속 바꿔야 하므로 `bytearray`로 캔버스를 만들고, 최종 압축할 때 `bytes(raw)`처럼 변경 불가능한 bytes로 바꾼다.

## 다른 파일과의 관계

### models.py

`models.py`에는 `Passenger`, `Counter`, `SimulationResult`가 정의되어 있다. `report_utils.py`는 이 클래스들을 직접 import하지 않지만, `_get()` helper 덕분에 이 객체들의 속성을 읽을 수 있다.

예를 들어 `Passenger` 객체에는 다음 속성이 있다.

```python
passenger.passenger_id
passenger.arrival_time
passenger.service_time
passenger.completion_time
passenger.turnaround_time
```

`report_utils.py`의 `_get(passenger, "turnaround_time")`는 이런 객체 속성을 읽는다. 입력이 딕셔너리라면 `passenger["turnaround_time"]`처럼 읽는다.

### simulation.py

`simulation.py`의 `SimulationEngine.run()`은 `SimulationResult`를 반환한다. 이 결과 안에 승객 목록, 카운터 목록, 로그, 종료 시간이 들어 있다.

`report_utils.py`는 이 결과에서 ATT, class summary, counter summary, graph를 만들 수 있게 설계되어 있다.

### scheduler.py

현재 직접 연결된 부분은 이 import다.

```python
from report_utils import write_att_comparison_png
```

그리고 결과 저장 단계에서 호출한다.

```python
write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
```

`results`는 대략 다음 모양이다.

```python
{
    "fcfs": SimulationResult(...),
    "priority": SimulationResult(...),
    "sjf": SimulationResult(...),
    "ours": SimulationResult(...),
}
```

`write_att_comparison_png()`는 이 딕셔너리를 받아 `_normalise_att_comparison()`과 `calculate_att_comparison()`을 거쳐 스케줄러 이름과 ATT 목록으로 바꾼 뒤 PNG 그래프를 만든다.

현재 `scheduler.py`는 CSV 저장을 자체 함수 `_write_passenger_results()`, `_write_class_summary()`, `_write_counter_summary()`, `_write_att_comparison()`으로 처리한다. 따라서 실제 CLI 실행에서 생성된 CSV의 헤더는 `report_utils.py`의 CSV 헤더와 일부 다를 수 있다. 예를 들어 `scheduler.py`의 `passenger_results.csv`에는 `class_name` 열이 추가되어 있다.

