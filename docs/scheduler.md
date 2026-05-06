# scheduler.py 설명

## 파일의 역할

`scheduler.py`는 프로젝트의 **실행 진입점(entry point)** 입니다.

사용자가 터미널에서 다음처럼 명령을 입력하면,

```powershell
python scheduler.py input.txt --scheduler all
```

`scheduler.py`가 다음 일을 순서대로 처리합니다.

1. 명령행 인자 읽기
2. `input.txt`에서 승객 데이터 읽기
3. 실행할 스케줄러 선택
4. `SimulationEngine`으로 시뮬레이션 실행
5. 결과가 정상인지 검증
6. CSV, 로그, PNG 결과 파일 생성
7. 콘솔에 요약 출력

즉 `scheduler.py`는 알고리즘 자체를 구현하는 파일이라기보다, 여러 파일을 연결해서 전체 프로그램을 실행하는 **조립 담당 파일**입니다.

## 전체 구조

```text
scheduler.py
|
|-- import 구문
|-- SCHEDULER_ORDER
|
|-- 입력 처리
|   |-- parse_input_file()
|   |-- _parse_passenger_id()
|   |-- _parse_non_negative_int()
|   |-- _parse_positive_int()
|   |-- _parse_passenger_class()
|   |-- _parse_int()
|
|-- 명령행 인자 처리
|   |-- build_arg_parser()
|   |-- selected_scheduler_names()
|
|-- 스케줄러 실행
|   |-- create_scheduler()
|   |-- run_scheduler()
|   |-- _validate_result()
|
|-- 결과 출력
|   |-- write_outputs()
|   |-- _write_passenger_results()
|   |-- _write_class_summary()
|   |-- _write_counter_summary()
|   |-- _write_simulation_log()
|   |-- _write_att_comparison()
|   |-- print_summary()
|
|-- main()
|-- if __name__ == "__main__"
```

## import 구문 설명

```python
from __future__ import annotations
```

타입 힌트를 더 유연하게 사용할 수 있게 하는 구문입니다.

```python
import argparse
```

명령행 인자를 처리하는 표준 라이브러리입니다.

예:

```powershell
python scheduler.py input.txt --scheduler all
```

여기서 `input.txt`, `--scheduler all` 같은 값을 읽어옵니다.

```python
import csv
```

CSV 파일을 쓰기 위한 표준 라이브러리입니다.

이 프로젝트에서는 `passenger_results.csv`, `class_summary.csv`, `counter_summary.csv`, `att_comparison.csv`를 만들 때 사용합니다.

```python
from pathlib import Path
```

파일 경로를 객체처럼 다루기 위한 표준 라이브러리입니다.

예:

```python
Path("output") / "passenger_results.csv"
```

위 코드는 운영체제에 맞는 경로 구분자를 사용해서 경로를 만듭니다.

```python
import re
```

정규표현식 모듈입니다.

입력 파일의 한 줄을 공백 또는 쉼표 기준으로 나눌 때 사용합니다.

```python
from typing import Iterable
```

타입 힌트입니다.

`Iterable[str]`은 문자열들을 반복할 수 있는 값이라는 뜻입니다. 리스트, 튜플 등이 해당됩니다.

```python
from models import BUSINESS, CLASS_NAMES, ECONOMY, FIRST, Passenger, SimulationResult
```

`models.py`에서 승객 등급 상수와 데이터 클래스를 가져옵니다.

- `FIRST`, `BUSINESS`, `ECONOMY`: 승객 등급 숫자
- `CLASS_NAMES`: 등급 숫자를 이름으로 바꾸는 딕셔너리
- `Passenger`: 승객 데이터 클래스
- `SimulationResult`: 시뮬레이션 결과 데이터 클래스

```python
from report_utils import write_att_comparison_png
```

ATT 비교 그래프 PNG를 만들기 위한 함수입니다.

ATT는 `Average Turnaround Time`, 즉 평균 반환 시간입니다.

```python
from simulation import SimulationEngine
```

실제 시뮬레이션을 진행하는 엔진입니다.

`scheduler.py`는 엔진을 만들고, 엔진에 스케줄러를 넘깁니다.

```python
from strategies import BaselineA_FCFS, BaselineB_Priority, BaselineC_SJF, OurScheduler, SchedulerStrategy
```

스케줄러 알고리즘 클래스를 가져옵니다.

`SchedulerStrategy`는 타입 힌트용 부모 클래스입니다.

## 코드 설명

### 실행 순서 상수

```python
SCHEDULER_ORDER = ("fcfs", "priority", "sjf", "ours")
```

`--scheduler all`을 선택했을 때 실행할 스케줄러 순서입니다.

튜플은 리스트와 비슷하지만 보통 변경하지 않을 값에 사용합니다.

순서는 다음과 같습니다.

1. `fcfs`
2. `priority`
3. `sjf`
4. `ours`

### 입력 파일 읽기: `parse_input_file()`

```python
def parse_input_file(input_path: Path) -> list[Passenger]:
    """Parse passenger rows: passenger_id arrival_time passenger_class service_time."""
    passengers: list[Passenger] = []
```

`input_path`는 입력 파일 경로입니다.

반환값은 `Passenger` 객체들의 리스트입니다.

`passengers: list[Passenger] = []`는 빈 리스트를 만들고, 이 리스트에는 `Passenger` 객체가 들어간다는 타입 힌트를 붙인 것입니다.

```python
    with input_path.open("r", encoding="utf-8") as file:
```

파일을 읽기 모드로 엽니다.

`with` 문을 사용하면 파일 사용이 끝난 뒤 자동으로 닫힙니다.

```python
        for line_number, raw_line in enumerate(file, start=1):
```

파일을 한 줄씩 읽습니다.

`enumerate(file, start=1)`는 줄 내용과 줄 번호를 함께 줍니다.

예:

```python
line_number = 1
raw_line = "1 0 3 7"
```

```python
            line = raw_line.partition("#")[0].strip()
            if not line:
                continue
```

`partition("#")`는 `#` 기준으로 문자열을 나눕니다.

입력 파일에 주석이 있다면 `#` 뒤쪽은 무시합니다.

`strip()`은 앞뒤 공백을 제거합니다.

`if not line:`은 빈 줄인지 확인합니다.

`continue`는 이번 반복을 건너뛰고 다음 줄로 넘어갑니다.

```python
            parts = re.split(r"[\s,]+", line)
            if len(parts) != 4:
                raise ValueError(
                    f"{input_path}:{line_number}: expected 4 columns "
                    "(passenger_id arrival_time class service_time)."
                )
```

`re.split(r"[\s,]+", line)`은 공백 또는 쉼표를 기준으로 문자열을 나눕니다.

예:

```text
1 0 3 7
1,0,3,7
```

둘 다 다음처럼 나뉩니다.

```python
["1", "0", "3", "7"]
```

입력값은 반드시 4개여야 합니다.

```text
passenger_id arrival_time class service_time
```

4개가 아니면 `ValueError`를 발생시켜 프로그램을 중단합니다.

```python
            passenger_id_token, arrival_token, class_token, service_token = parts
```

리스트의 4개 값을 각각 변수에 나눠 담습니다.

이 문법을 **튜플 언패킹** 또는 **시퀀스 언패킹**이라고 합니다.

```python
            passenger_id = _parse_passenger_id(passenger_id_token)
            arrival_time = _parse_non_negative_int(input_path, line_number, "arrival_time", arrival_token)
            passenger_class = _parse_passenger_class(input_path, line_number, class_token)
            service_time = _parse_positive_int(input_path, line_number, "service_time", service_token)
```

문자열로 읽은 값을 실제 사용할 타입으로 변환합니다.

- 승객 ID: 숫자면 `int`, 아니면 문자열
- 도착 시간: 0 이상의 정수
- 승객 등급: `1`, `2`, `3` 중 하나
- 서비스 시간: 1 이상의 정수

```python
            passengers.append(
                Passenger(
                    passenger_id=passenger_id,
                    arrival_time=arrival_time,
                    passenger_class=passenger_class,
                    service_time=service_time,
                )
            )
```

`Passenger(...)`는 `models.py`에 정의된 데이터 객체를 만듭니다.

`append()`는 리스트 끝에 값을 추가합니다.

```python
    if not passengers:
        raise ValueError(f"{input_path}: no passenger rows found.")
```

승객 데이터가 하나도 없으면 에러를 발생시킵니다.

```python
    return sorted(passengers, key=lambda passenger: passenger.sort_key())
```

승객을 정렬해서 반환합니다.

`sorted()`는 새 정렬 리스트를 반환합니다.

정렬 기준은 `passenger.sort_key()`입니다. 이 메서드는 `models.py`의 `Passenger` 클래스에 있습니다.

### 명령행 인자 만들기: `build_arg_parser()`

```python
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run airport check-in scheduling simulations.",
    )
```

`argparse.ArgumentParser`는 명령행 인자를 읽는 파서 객체입니다.

```python
    parser.add_argument(
        "input",
        type=Path,
        help="input.txt path. Each row: passenger_id arrival_time class service_time",
    )
```

`"input"`은 위치 인자입니다.

즉 명령에서 반드시 넣어야 하는 값입니다.

```powershell
python scheduler.py input.txt
```

여기서 `input.txt`가 `input` 인자입니다.

`type=Path`이므로 문자열을 `Path` 객체로 변환합니다.

```python
    parser.add_argument(
        "--scheduler",
        choices=(*SCHEDULER_ORDER, "all"),
        default="all",
        help="scheduler to run: fcfs, priority, sjf, ours, or all. Default: all",
    )
```

`--scheduler`는 선택 인자입니다.

허용값은 다음입니다.

```text
fcfs, priority, sjf, ours, all
```

`choices=(*SCHEDULER_ORDER, "all")`에서 `*SCHEDULER_ORDER`는 튜플을 펼치는 문법입니다.

`SCHEDULER_ORDER`가 다음과 같다면,

```python
("fcfs", "priority", "sjf", "ours")
```

아래와 비슷하게 동작합니다.

```python
("fcfs", "priority", "sjf", "ours", "all")
```

```python
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="output directory. Default: output",
    )
```

결과 파일을 저장할 폴더입니다.

생략하면 `output` 폴더에 저장합니다.

### 선택한 스케줄러 이름 목록 만들기

```python
def selected_scheduler_names(selection: str) -> list[str]:
    if selection == "all":
        return list(SCHEDULER_ORDER)
    return [selection]
```

`--scheduler all`이면 모든 스케줄러 이름을 리스트로 반환합니다.

```python
["fcfs", "priority", "sjf", "ours"]
```

하나만 선택했다면 해당 이름 하나만 리스트로 반환합니다.

예:

```python
["sjf"]
```

### 스케줄러 객체 만들기

```python
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
```

문자열 이름을 실제 스케줄러 객체로 바꿉니다.

예:

```python
create_scheduler("fcfs")
```

결과:

```python
BaselineA_FCFS()
```

지원하지 않는 이름이면 `ValueError`를 발생시킵니다.

### 스케줄러 실행

```python
def run_scheduler(passengers: list[Passenger], scheduler_name: str) -> SimulationResult:
    scheduler = create_scheduler(scheduler_name)
    engine = SimulationEngine(passengers=passengers, enable_log=True)
    result = engine.run(scheduler)
    _validate_result(result)
    return result
```

한 스케줄러를 실행하는 함수입니다.

흐름은 다음과 같습니다.

1. `create_scheduler()`로 스케줄러 객체 생성
2. `SimulationEngine` 생성
3. `engine.run(scheduler)` 실행
4. 결과 검증
5. 결과 반환

`SimulationEngine`은 `simulation.py`에 있고, 실제 시간 진행과 카운터 배정을 담당합니다.

### 결과 파일 쓰기

```python
def write_outputs(
    results: dict[str, SimulationResult],
    output_dir: Path,
    canonical_scheduler: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
```

`results`는 스케줄러 이름과 실행 결과를 담은 딕셔너리입니다.

예:

```python
{
    "fcfs": SimulationResult(...),
    "priority": SimulationResult(...),
    "sjf": SimulationResult(...),
    "ours": SimulationResult(...),
}
```

`mkdir(parents=True, exist_ok=True)`는 출력 폴더를 만듭니다.

- `parents=True`: 중간 폴더도 같이 만듦
- `exist_ok=True`: 이미 폴더가 있어도 에러를 내지 않음

```python
    for scheduler_name, result in results.items():
        prefix = f"{scheduler_name}_"
        _write_passenger_results(result, output_dir / f"{prefix}passenger_results.csv")
        _write_class_summary(result, output_dir / f"{prefix}class_summary.csv")
        _write_counter_summary(result, output_dir / f"{prefix}counter_summary.csv")
        _write_simulation_log(result, output_dir / f"{prefix}simulation_log.txt")
```

각 스케줄러별 결과 파일을 만듭니다.

예:

```text
fcfs_passenger_results.csv
fcfs_class_summary.csv
fcfs_counter_summary.csv
fcfs_simulation_log.txt
```

`results.items()`는 딕셔너리에서 `(키, 값)` 쌍을 하나씩 꺼냅니다.

```python
    canonical_result = results[canonical_scheduler]
    _write_passenger_results(canonical_result, output_dir / "passenger_results.csv")
    _write_class_summary(canonical_result, output_dir / "class_summary.csv")
    _write_counter_summary(canonical_result, output_dir / "counter_summary.csv")
    _write_simulation_log(canonical_result, output_dir / "simulation_log.txt")
```

대표 결과 파일도 별도로 만듭니다.

`all` 실행 시 대표 스케줄러는 보통 `ours`입니다.

그래서 다음 파일들은 `ours` 결과와 같습니다.

```text
passenger_results.csv
class_summary.csv
counter_summary.csv
simulation_log.txt
```

```python
    _write_att_comparison(results, output_dir / "att_comparison.csv")
    write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
```

스케줄러별 평균 반환 시간 비교 CSV와 PNG 그래프를 만듭니다.

### 콘솔 요약 출력

```python
def print_summary(results: dict[str, SimulationResult]) -> None:
    for scheduler_name, result in results.items():
        averages = result.average_turnaround_by_class()
```

각 스케줄러 결과를 순회하면서 평균 반환 시간을 계산합니다.

```python
        print(f"[{scheduler_name}]")
        print(f"finished_at: {result.finished_at}")
        print(f"completed: {len(result.completed_passengers)}/{len(result.passengers)}")
        print(f"average_turnaround_time: {result.average_turnaround_time:.2f}")
```

`f"{값:.2f}"`는 소수점 둘째 자리까지 출력하는 f-string 문법입니다.

```python
        print(
            "class_average_turnaround_time: "
            f"First={averages[FIRST]:.2f}, "
            f"Business={averages[BUSINESS]:.2f}, "
            f"Economy={averages[ECONOMY]:.2f}"
        )
```

등급별 평균 반환 시간을 출력합니다.

### main 함수

```python
def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
```

`main()`은 프로그램의 핵심 실행 함수입니다.

`argv`가 `None`이면 실제 터미널 인자를 사용합니다.

테스트 코드에서는 `argv`에 직접 리스트를 넣어 실행해 볼 수도 있습니다.

```python
    passengers = parse_input_file(args.input)
    scheduler_names = selected_scheduler_names(args.scheduler)
```

입력 파일을 읽고, 실행할 스케줄러 이름 목록을 만듭니다.

```python
    results = {
        scheduler_name: run_scheduler(passengers, scheduler_name)
        for scheduler_name in scheduler_names
    }
```

이 문법은 **dict comprehension**입니다.

리스트 컴프리헨션이 리스트를 만드는 것처럼, dict comprehension은 딕셔너리를 만듭니다.

위 코드는 아래와 거의 같습니다.

```python
results = {}
for scheduler_name in scheduler_names:
    results[scheduler_name] = run_scheduler(passengers, scheduler_name)
```

`--scheduler all`이면 내부적으로 다음처럼 실행됩니다.

```python
results = {
    "fcfs": run_scheduler(passengers, "fcfs"),
    "priority": run_scheduler(passengers, "priority"),
    "sjf": run_scheduler(passengers, "sjf"),
    "ours": run_scheduler(passengers, "ours"),
}
```

```python
    canonical_scheduler = "ours" if "ours" in results else scheduler_names[-1]
```

이 문법은 조건 표현식입니다.

뜻은 다음과 같습니다.

```python
if "ours" in results:
    canonical_scheduler = "ours"
else:
    canonical_scheduler = scheduler_names[-1]
```

`scheduler_names[-1]`은 리스트의 마지막 요소입니다.

```python
    write_outputs(results, args.output, canonical_scheduler)
    print_summary(results)
    print(f"output_dir: {args.output}")

    return 0
```

결과 파일을 쓰고, 요약을 출력한 뒤 정상 종료 코드 `0`을 반환합니다.

### 프로그램 시작점

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

이 파일을 직접 실행했을 때만 `main()`을 호출합니다.

```powershell
python scheduler.py input.txt --scheduler all
```

처럼 실행하면 `__name__`이 `"__main__"`이 됩니다.

`raise SystemExit(main())`는 `main()`의 반환값을 프로그램 종료 코드로 사용합니다.

## 실행 명령어 처리 흐름

명령:

```powershell
python scheduler.py input.txt --scheduler all
```

실행 흐름:

```text
1. Python이 scheduler.py 파일 실행
2. if __name__ == "__main__" 조건이 참
3. main() 호출
4. build_arg_parser() 호출
5. parser.parse_args()가 input.txt와 --scheduler all 해석
6. parse_input_file(input.txt)로 승객 목록 생성
7. selected_scheduler_names("all") 호출
8. ["fcfs", "priority", "sjf", "ours"] 반환
9. dict comprehension으로 각 스케줄러 실행
10. run_scheduler(passengers, "fcfs")
11. run_scheduler(passengers, "priority")
12. run_scheduler(passengers, "sjf")
13. run_scheduler(passengers, "ours")
14. canonical_scheduler를 "ours"로 결정
15. write_outputs()로 결과 파일 생성
16. print_summary()로 콘솔 요약 출력
17. output_dir 출력
18. main()이 0 반환
19. SystemExit(0)로 정상 종료
```

각 `run_scheduler()` 내부 흐름은 다음과 같습니다.

```text
run_scheduler()
  -> create_scheduler()
  -> SimulationEngine(passengers=..., enable_log=True)
  -> engine.run(scheduler)
  -> _validate_result()
  -> SimulationResult 반환
```

`engine.run(scheduler)` 내부에서는 카운터가 비어 있을 때마다 다음 메서드가 호출됩니다.

```python
scheduler.select_next_passenger(...)
```

이 메서드는 `strategies.py`의 FCFS, Priority, SJF, OurScheduler 중 하나입니다.

## 스케줄러별 선택 기준

`scheduler.py`는 선택 기준을 직접 계산하지 않습니다. 선택 기준은 `strategies.py`에 있습니다.

하지만 `scheduler.py`의 `create_scheduler()`가 어떤 이름이 어떤 클래스로 연결되는지 결정합니다.

| 명령어 값 | 생성되는 클래스 | 선택 기준 |
| --- | --- | --- |
| `fcfs` | `BaselineA_FCFS()` | 먼저 도착한 승객 |
| `priority` | `BaselineB_Priority()` | 등급이 높은 승객 |
| `sjf` | `BaselineC_SJF()` | 서비스 시간이 짧은 승객 |
| `ours` | `OurScheduler()` | 등급 가중치 + 기다린 시간 + 서비스 시간 |
| `all` | 위 네 개 모두 | `fcfs`, `priority`, `sjf`, `ours` 순서 실행 |

## 스케줄러 비교표

| 항목 | FCFS | Priority | SJF | OurScheduler |
| --- | --- | --- | --- | --- |
| `scheduler.py` 이름 | `fcfs` | `priority` | `sjf` | `ours` |
| 클래스 | `BaselineA_FCFS` | `BaselineB_Priority` | `BaselineC_SJF` | `OurScheduler` |
| 먼저 보는 기준 | 도착 시간 | 승객 등급 | 서비스 시간 | weighted HRRN 점수 |
| 출력 파일 prefix | `fcfs_` | `priority_` | `sjf_` | `ours_` |
| 대표 결과 가능성 | 단독 실행 시 가능 | 단독 실행 시 가능 | 단독 실행 시 가능 | `all` 실행 시 대표 결과 |

## 다른 파일과의 관계

### `models.py`

`scheduler.py`는 `models.py`의 `Passenger`와 `SimulationResult`를 사용합니다.

입력 파일 한 줄은 `Passenger` 객체 하나로 변환됩니다.

```python
Passenger(
    passenger_id=passenger_id,
    arrival_time=arrival_time,
    passenger_class=passenger_class,
    service_time=service_time,
)
```

시뮬레이션 결과는 `SimulationResult`로 돌아옵니다.

### `strategies.py`

`scheduler.py`는 `create_scheduler()`에서 `strategies.py`의 스케줄러 클래스를 생성합니다.

```python
if name == "sjf":
    return BaselineC_SJF()
```

### `simulation.py`

`scheduler.py`는 `SimulationEngine`을 생성하고 `run()`을 호출합니다.

```python
engine = SimulationEngine(passengers=passengers, enable_log=True)
result = engine.run(scheduler)
```

실제 시간 증가, 카운터 배정, 서비스 완료 처리는 `simulation.py`가 담당합니다.

### `report_utils.py`

`scheduler.py`는 `write_att_comparison_png()`를 호출해서 ATT 비교 그래프를 생성합니다.

```python
write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
```

CSV 파일 대부분은 `scheduler.py`가 직접 쓰지만, PNG 그래프는 `report_utils.py` 함수에 맡깁니다.
