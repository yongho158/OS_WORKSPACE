# scheduler.py 실행 흐름 설명

## 파일의 역할

이 문서는 `scheduler.py`가 실제로 어떤 순서로 실행되는지 설명합니다.

특히 다음 명령어를 기준으로 내부 함수 호출 순서를 따라갑니다.

```powershell
python scheduler.py input.txt --scheduler all
```

이 명령은 네 가지 스케줄러를 모두 실행합니다.

실행 순서는 다음과 같습니다.

```python
("fcfs", "priority", "sjf", "ours")
```

## 전체 구조

큰 흐름은 다음과 같습니다.

```text
터미널 명령어
  -> scheduler.py 실행
  -> main()
  -> 입력 파일 파싱
  -> 실행할 스케줄러 목록 결정
  -> 각 스케줄러별 SimulationEngine 실행
  -> 결과 검증
  -> CSV / TXT / PNG 파일 저장
  -> 콘솔 요약 출력
```

더 자세히 보면 다음 구조입니다.

```text
main()
|
|-- build_arg_parser()
|-- parser.parse_args()
|-- parse_input_file()
|-- selected_scheduler_names()
|
|-- run_scheduler() 반복 실행
|   |-- create_scheduler()
|   |-- SimulationEngine(...)
|   |-- engine.run(...)
|   |   |-- _reset()
|   |   |-- _move_arrivals_to_ready_queue()
|   |   |-- _complete_due_services()
|   |   |-- _assign_idle_counters()
|   |   |   |-- scheduler.select_next_passenger()
|   |   |-- _next_event_time()
|   |   |-- _advance_time()
|   |-- _validate_result()
|
|-- write_outputs()
|-- print_summary()
```

## 코드 설명

### 프로그램 시작점

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

파이썬 파일을 직접 실행하면 `__name__` 값이 `"__main__"`이 됩니다.

따라서 다음 명령을 실행하면,

```powershell
python scheduler.py input.txt --scheduler all
```

`main()` 함수가 호출됩니다.

`raise SystemExit(main())`는 `main()`이 반환한 값을 프로그램 종료 코드로 사용합니다.

- `0`: 정상 종료
- 0이 아닌 값: 비정상 종료로 보는 경우가 많음

### `main()`의 첫 단계

```python
def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
```

`main()`은 가장 먼저 명령행 인자 파서를 만듭니다.

`argv`는 직접 전달된 인자 목록입니다. 보통은 `None`이고, 이 경우 실제 터미널 명령어를 읽습니다.

```python
args = parser.parse_args(argv)
```

이 줄이 명령어를 해석합니다.

명령어가 다음과 같다면,

```powershell
python scheduler.py input.txt --scheduler all
```

`args`에는 대략 다음 값이 들어갑니다.

```python
args.input == Path("input.txt")
args.scheduler == "all"
args.output == Path("output")
```

`--output`을 따로 지정하지 않았기 때문에 기본값 `output`이 사용됩니다.

## 실행 명령어 처리 흐름

### 1단계: 인자 파서 만들기

```python
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run airport check-in scheduling simulations.",
    )
```

`argparse.ArgumentParser`는 명령행 인자를 해석하는 객체입니다.

```python
    parser.add_argument(
        "input",
        type=Path,
        help="input.txt path. Each row: passenger_id arrival_time class service_time",
    )
```

`input`은 필수 위치 인자입니다.

명령어에서 `input.txt`가 여기에 들어갑니다.

```python
    parser.add_argument(
        "--scheduler",
        choices=(*SCHEDULER_ORDER, "all"),
        default="all",
        help="scheduler to run: fcfs, priority, sjf, ours, or all. Default: all",
    )
```

`--scheduler`는 선택 인자입니다.

사용 가능한 값은 다음입니다.

```text
fcfs, priority, sjf, ours, all
```

이번 명령에서는 `all`입니다.

```python
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="output directory. Default: output",
    )
```

결과 저장 폴더입니다.

이번 명령에서는 지정하지 않았으므로 `output` 폴더를 사용합니다.

### 2단계: 입력 파일 읽기

```python
passengers = parse_input_file(args.input)
```

`args.input`은 `Path("input.txt")`입니다.

따라서 실제 호출은 다음과 같습니다.

```python
parse_input_file(Path("input.txt"))
```

입력 파일 한 줄은 다음 형식이어야 합니다.

```text
passenger_id arrival_time class service_time
```

예:

```text
1 0 3 7
```

의미는 다음과 같습니다.

| 값 | 의미 |
| --- | --- |
| `1` | 승객 ID |
| `0` | 도착 시간 |
| `3` | 승객 등급, Economy |
| `7` | 서비스 시간 |

`parse_input_file()` 내부 흐름은 다음과 같습니다.

```text
파일 열기
  -> 한 줄씩 읽기
  -> 주석 제거
  -> 빈 줄 건너뛰기
  -> 공백/쉼표 기준으로 4개 값 분리
  -> 각 값을 int 등으로 변환
  -> Passenger 객체 생성
  -> 리스트에 추가
  -> 도착 시간과 ID 기준 정렬
```

중요한 코드:

```python
parts = re.split(r"[\s,]+", line)
```

`re.split()`은 정규표현식으로 문자열을 나눕니다.

`r"[\s,]+"`의 의미는 다음과 같습니다.

- `\s`: 공백 문자
- `,`: 쉼표
- `+`: 하나 이상 반복

그래서 공백 입력과 쉼표 입력을 모두 처리할 수 있습니다.

### 3단계: 실행할 스케줄러 목록 결정

```python
scheduler_names = selected_scheduler_names(args.scheduler)
```

이번 명령에서는 `args.scheduler`가 `"all"`입니다.

```python
def selected_scheduler_names(selection: str) -> list[str]:
    if selection == "all":
        return list(SCHEDULER_ORDER)
    return [selection]
```

따라서 결과는 다음입니다.

```python
["fcfs", "priority", "sjf", "ours"]
```

`SCHEDULER_ORDER`는 원래 튜플입니다.

```python
SCHEDULER_ORDER = ("fcfs", "priority", "sjf", "ours")
```

`list(SCHEDULER_ORDER)`는 튜플을 리스트로 바꿉니다.

### 4단계: 모든 스케줄러 실행

```python
results = {
    scheduler_name: run_scheduler(passengers, scheduler_name)
    for scheduler_name in scheduler_names
}
```

이 문법은 **dict comprehension**입니다.

초보자 관점에서는 아래 코드와 같다고 보면 됩니다.

```python
results = {}
for scheduler_name in scheduler_names:
    results[scheduler_name] = run_scheduler(passengers, scheduler_name)
```

이번 명령에서는 다음 순서로 호출됩니다.

```text
run_scheduler(passengers, "fcfs")
run_scheduler(passengers, "priority")
run_scheduler(passengers, "sjf")
run_scheduler(passengers, "ours")
```

각 실행 결과는 `results` 딕셔너리에 저장됩니다.

```python
{
    "fcfs": SimulationResult(...),
    "priority": SimulationResult(...),
    "sjf": SimulationResult(...),
    "ours": SimulationResult(...),
}
```

## 한 스케줄러의 실행 흐름

`run_scheduler()`는 다음과 같습니다.

```python
def run_scheduler(passengers: list[Passenger], scheduler_name: str) -> SimulationResult:
    scheduler = create_scheduler(scheduler_name)
    engine = SimulationEngine(passengers=passengers, enable_log=True)
    result = engine.run(scheduler)
    _validate_result(result)
    return result
```

### 1. 스케줄러 객체 생성

```python
scheduler = create_scheduler(scheduler_name)
```

예를 들어 `scheduler_name`이 `"fcfs"`이면 다음 객체가 만들어집니다.

```python
BaselineA_FCFS()
```

연결 관계:

| 이름 | 생성되는 객체 |
| --- | --- |
| `fcfs` | `BaselineA_FCFS()` |
| `priority` | `BaselineB_Priority()` |
| `sjf` | `BaselineC_SJF()` |
| `ours` | `OurScheduler()` |

### 2. 시뮬레이션 엔진 생성

```python
engine = SimulationEngine(passengers=passengers, enable_log=True)
```

`SimulationEngine`은 `simulation.py`에 있습니다.

엔진은 다음 상태를 관리합니다.

| 상태 | 의미 |
| --- | --- |
| `self.passengers` | 전체 승객 목록 |
| `self.counters` | 체크인 카운터 목록 |
| `self.current_time` | 현재 시뮬레이션 시간 |
| `self.ready_queue` | 도착해서 기다리는 승객 |
| `self.completed_passengers` | 서비스가 끝난 승객 |
| `self.event_log` | 시뮬레이션 로그 |

`SimulationEngine` 내부에서는 `deepcopy()`를 사용해 승객 목록을 복사합니다.

그래서 `fcfs` 실행이 끝나 승객들의 시작/완료 시간이 기록되어도, 다음 `priority` 실행은 깨끗한 상태에서 다시 시작할 수 있습니다.

### 3. 엔진 실행

```python
result = engine.run(scheduler)
```

이 한 줄이 실제 시뮬레이션을 진행합니다.

`simulation.py`의 `run()` 흐름은 다음과 같습니다.

```text
_reset()
while 모든 승객이 완료되지 않았으면:
    _move_arrivals_to_ready_queue()
    _complete_due_services()
    _assign_idle_counters()
    _next_event_time()
    _advance_time()
SimulationResult 반환
```

### 4. 결과 검증

```python
_validate_result(result)
```

모든 승객이 정상적으로 완료되었는지 확인합니다.

검증 내용은 다음입니다.

- 완료 승객 수가 전체 승객 수와 같은가
- 모든 승객에게 `service_start_time`이 있는가
- 모든 승객에게 `completion_time`이 있는가
- 모든 승객에게 `turnaround_time`이 있는가
- `completion_time == service_start_time + service_time`인가
- `turnaround_time == completion_time - arrival_time`인가

문제가 있으면 `RuntimeError`를 발생시킵니다.

## SimulationEngine 내부 흐름

### `_reset()`

```text
시뮬레이션 시간을 0으로 초기화
ready_queue 비우기
completed_passengers 비우기
event_log 비우기
승객 실행 상태 초기화
카운터 실행 상태 초기화
```

각 스케줄러 실행은 독립적으로 시작해야 하므로 초기화가 필요합니다.

### `_move_arrivals_to_ready_queue()`

현재 시간까지 도착한 승객을 `ready_queue`로 옮깁니다.

예를 들어 현재 시간이 `0`이면, 도착 시간이 `0`인 승객들이 대기열에 들어갑니다.

```text
전체 승객 목록
  -> arrival_time <= current_time 인 승객
  -> ready_queue로 이동
```

### `_complete_due_services()`

현재 시간에 서비스가 끝난 승객을 완료 처리합니다.

카운터의 `busy_until` 시간이 현재 시간 이하이면 완료할 수 있습니다.

완료된 승객은 `completed_passengers`에 추가됩니다.

### `_assign_idle_counters()`

빈 카운터에 대기 승객을 배정합니다.

이 단계에서 `strategies.py`의 스케줄러가 호출됩니다.

```python
selected = scheduler.select_next_passenger(
    ready_queue=list(self.ready_queue),
    counters=self.counters,
    current_time=self.current_time,
    counter=counter,
)
```

여기서 중요한 점은 `ready_queue=list(self.ready_queue)`입니다.

원본 리스트를 직접 넘기지 않고 복사본을 넘깁니다.

스케줄러는 승객을 **고르기만** 하고, 실제로 대기열에서 제거하는 일은 `SimulationEngine`이 합니다.

```python
self.ready_queue.remove(selected)
counter.assign_passenger(selected, self.current_time)
```

### `_next_event_time()`

다음 이벤트 시간을 찾습니다.

다음 이벤트가 될 수 있는 것은 두 가지입니다.

1. 다음 승객 도착 시간
2. 현재 처리 중인 승객의 완료 시간

그중 현재 시간보다 큰 가장 작은 시간을 고릅니다.

```python
return min(future_times)
```

### `_advance_time()`

현재 시간을 다음 이벤트 시간으로 이동합니다.

예:

```text
current_time = 0
next_time = 3
```

이면 시간이 3으로 이동합니다.

시간이 이동하는 동안 빈 카운터가 있으면 idle time도 증가합니다.

## `python scheduler.py input.txt --scheduler all` 전체 호출 순서

아래는 실제 호출 순서를 초보자용으로 펼친 것입니다.

```text
Python 실행
|
|-- scheduler.py 로드
|-- if __name__ == "__main__"
|-- main()
    |
    |-- build_arg_parser()
    |-- parse_args()
    |
    |-- parse_input_file(Path("input.txt"))
    |   |-- input.txt 열기
    |   |-- 각 줄을 Passenger 객체로 변환
    |   |-- 승객 리스트 정렬
    |
    |-- selected_scheduler_names("all")
    |   |-- ["fcfs", "priority", "sjf", "ours"] 반환
    |
    |-- run_scheduler(passengers, "fcfs")
    |   |-- create_scheduler("fcfs")
    |   |-- BaselineA_FCFS()
    |   |-- SimulationEngine(...)
    |   |-- engine.run(BaselineA_FCFS)
    |   |-- _validate_result()
    |
    |-- run_scheduler(passengers, "priority")
    |   |-- create_scheduler("priority")
    |   |-- BaselineB_Priority()
    |   |-- SimulationEngine(...)
    |   |-- engine.run(BaselineB_Priority)
    |   |-- _validate_result()
    |
    |-- run_scheduler(passengers, "sjf")
    |   |-- create_scheduler("sjf")
    |   |-- BaselineC_SJF()
    |   |-- SimulationEngine(...)
    |   |-- engine.run(BaselineC_SJF)
    |   |-- _validate_result()
    |
    |-- run_scheduler(passengers, "ours")
    |   |-- create_scheduler("ours")
    |   |-- OurScheduler()
    |   |-- SimulationEngine(...)
    |   |-- engine.run(OurScheduler)
    |   |-- _validate_result()
    |
    |-- canonical_scheduler = "ours"
    |-- write_outputs(results, Path("output"), "ours")
    |-- print_summary(results)
    |-- print("output_dir: output")
    |-- return 0
```

## 결과 파일 생성 흐름

`write_outputs()`는 먼저 각 스케줄러별 파일을 씁니다.

예를 들어 `fcfs` 결과는 다음 파일로 저장됩니다.

```text
output/fcfs_passenger_results.csv
output/fcfs_class_summary.csv
output/fcfs_counter_summary.csv
output/fcfs_simulation_log.txt
```

`all` 실행 시 네 스케줄러 모두에 대해 같은 종류의 파일이 만들어집니다.

그다음 대표 결과 파일을 씁니다.

```text
output/passenger_results.csv
output/class_summary.csv
output/counter_summary.csv
output/simulation_log.txt
```

`all` 실행에서는 대표 스케줄러가 `ours`이므로 위 파일들은 `ours_...` 파일과 같은 내용을 가집니다.

마지막으로 비교 파일을 만듭니다.

```text
output/att_comparison.csv
output/att_comparison.png
```

## 스케줄러별 선택 기준

`SimulationEngine`은 모든 스케줄러를 같은 방식으로 호출합니다.

```python
scheduler.select_next_passenger(...)
```

하지만 실제 선택 기준은 객체 종류에 따라 다릅니다.

| 스케줄러 | 호출되는 클래스 | 선택 기준 |
| --- | --- | --- |
| `fcfs` | `BaselineA_FCFS` | 먼저 도착한 승객 |
| `priority` | `BaselineB_Priority` | First, Business, Economy 순 |
| `sjf` | `BaselineC_SJF` | 서비스 시간이 짧은 승객 |
| `ours` | `OurScheduler` | 카운터 등급, 등급 가중치, 대기 시간, 서비스 시간 |

이 구조는 다형성(polymorphism)의 예입니다.

`SimulationEngine`은 구체적인 알고리즘 이름을 몰라도 됩니다. 그저 `select_next_passenger()` 메서드만 호출하면 됩니다.

## 스케줄러 비교표

| 항목 | FCFS | Priority | SJF | OurScheduler |
| --- | --- | --- | --- | --- |
| 실행 이름 | `fcfs` | `priority` | `sjf` | `ours` |
| 먼저 보는 기준 | 도착 시간 | 승객 등급 | 서비스 시간 | weighted HRRN 점수 |
| 카운터 종류 사용 | 아니오 | 아니오 | 아니오 | 예 |
| 기다린 시간 반영 | 아니오 | 도착 시간만 반영 | 도착 시간은 동점 때만 반영 | 예 |
| 긴 작업이 밀릴 위험 | 낮음 | 등급에 따라 있음 | 높음 | 대기 시간 증가로 완화 |
| 초보자 이해 난이도 | 쉬움 | 쉬움 | 쉬움 | 중간 |

## 다른 파일과의 관계

### `models.py`

`models.py`는 데이터의 모양을 정의합니다.

`scheduler.py`는 입력 파일을 읽어 `Passenger` 객체를 만듭니다.

`simulation.py`는 카운터와 결과를 `Counter`, `SimulationResult` 객체로 관리합니다.

### `strategies.py`

`strategies.py`는 승객 선택 알고리즘을 제공합니다.

`scheduler.py`의 `create_scheduler()`가 이름에 맞는 스케줄러 객체를 생성합니다.

### `simulation.py`

`simulation.py`는 실제 시뮬레이션 루프를 실행합니다.

`scheduler.py`는 `SimulationEngine.run()`을 호출하고, `SimulationEngine`은 필요할 때 `strategies.py`의 선택 메서드를 호출합니다.

### `report_utils.py`

`scheduler.py`는 대부분의 CSV 파일을 직접 씁니다.

하지만 ATT 비교 그래프 PNG는 `report_utils.py`의 `write_att_comparison_png()`를 사용합니다.

연결 흐름은 다음과 같습니다.

```text
input.txt
  -> scheduler.py
  -> models.Passenger
  -> simulation.SimulationEngine
  -> strategies 스케줄러
  -> models.SimulationResult
  -> scheduler.py 결과 파일 작성
  -> report_utils.py 그래프 작성
```
