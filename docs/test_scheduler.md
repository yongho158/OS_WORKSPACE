# `test_scheduler.py` 설명

## `test_scheduler.py`의 역할

`test_scheduler.py`는 입력 데이터와 스케줄러 실행 결과가 기본 조건을 만족하는지 자동으로 검사하는 테스트 파일이다.

이 테스트는 보고서 문서를 직접 검사하지 않는다. 대신 보고서의 근거가 되는 시뮬레이션 코드가 다음 조건을 만족하는지 확인한다.

| 검사 대상 | 확인하는 내용 |
|---|---|
| `input.txt` | 승객 수가 50명인지 확인 |
| `input.txt` | 전체 `service_time` 합이 379인지 확인 |
| 모든 스케줄러 | 모든 승객을 완료 처리하는지 확인 |
| 모든 스케줄러 | 입력의 `service_time` 합을 보존하는지 확인 |
| 모든 스케줄러 | `completion_time`, `turnaround_time` 계산식이 맞는지 확인 |

실행 명령어는 다음과 같다.

```powershell
python -m unittest -v test_scheduler.py
```

프로젝트 전체 테스트를 실행하려면 다음 명령도 가능하다.

```powershell
python -m unittest -v
```

## import 구문

```python
from pathlib import Path
import unittest

from scheduler import SCHEDULER_ORDER, parse_input_file, run_scheduler
```

`Path`는 현재 테스트 파일 기준으로 `input.txt` 경로를 만들기 위해 사용한다.

`unittest`는 파이썬 기본 테스트 프레임워크이다. 별도 설치 없이 사용할 수 있다.

`scheduler`에서 가져오는 항목은 다음과 같다.

| import 항목 | 의미 |
|---|---|
| `SCHEDULER_ORDER` | 실행할 스케줄러 이름 목록. 현재 `fcfs`, `priority`, `sjf`, `ours` |
| `parse_input_file` | `input.txt`를 읽어 `Passenger` 객체 리스트로 바꾸는 함수 |
| `run_scheduler` | 특정 스케줄러로 시뮬레이션을 실행하는 함수 |

## 테스트용 상수

```python
INPUT_PATH = Path(__file__).with_name("input.txt")
EXPECTED_PASSENGER_COUNT = 50
EXPECTED_TOTAL_SERVICE_TIME = 379
```

`Path(__file__)`은 현재 파일인 `test_scheduler.py`의 경로이다.

`with_name("input.txt")`는 같은 폴더에 있는 `input.txt`를 가리키는 새 경로를 만든다.

예를 들어 현재 파일이 다음 위치라면,

```text
C:\OS_WORKSPACE\test_scheduler.py
```

`INPUT_PATH`는 다음 위치가 된다.

```text
C:\OS_WORKSPACE\input.txt
```

`EXPECTED_PASSENGER_COUNT`는 기대 승객 수이다. 이 프로젝트에서는 입력 파일에 승객 50명이 있어야 한다.

`EXPECTED_TOTAL_SERVICE_TIME`은 모든 승객의 `service_time` 합계이다. 현재 `input.txt` 기준 합계는 379이다.

## 테스트 클래스

```python
class SchedulerInputTests(unittest.TestCase):
```

`unittest.TestCase`를 상속하면 이 클래스 안에 테스트 함수를 만들 수 있다.

파이썬에서 클래스는 관련 함수와 데이터를 묶는 틀이다. 여기서는 스케줄러 테스트들을 `SchedulerInputTests`라는 이름 아래에 묶었다.

`unittest`는 이름이 `test_`로 시작하는 메서드를 자동으로 테스트로 인식한다.

## 입력 파일 검증 테스트

```python
def test_input_file_matches_expected_workload(self):
    passengers = parse_input_file(INPUT_PATH)

    self.assertEqual(len(passengers), EXPECTED_PASSENGER_COUNT)
```

이 테스트는 먼저 `input.txt`를 읽어 `passengers` 리스트를 만든다.

`len(passengers)`는 리스트 안의 승객 수를 구한다. 이 값이 `50`인지 확인한다.

```python
self.assertEqual(
    sum(passenger.service_time for passenger in passengers),
    EXPECTED_TOTAL_SERVICE_TIME,
    "input.txt service_time total must match the required workload total.",
)
```

이 코드는 모든 승객의 `service_time`을 더해서 379인지 확인한다.

```python
sum(passenger.service_time for passenger in passengers)
```

이 문법은 generator expression이다. 리스트를 새로 만들지 않고 승객을 하나씩 보며 `service_time`만 꺼내 합계를 구한다.

## 모든 스케줄러 실행 테스트

```python
def test_all_schedulers_are_runnable_and_complete_all_passengers(self):
    for scheduler_name in SCHEDULER_ORDER:
        with self.subTest(scheduler=scheduler_name):
            result = run_scheduler(parse_input_file(INPUT_PATH), scheduler_name)
```

`for scheduler_name in SCHEDULER_ORDER`는 모든 스케줄러 이름을 하나씩 반복한다.

현재 순서는 다음과 같다.

```python
("fcfs", "priority", "sjf", "ours")
```

`with self.subTest(scheduler=scheduler_name)`는 반복 테스트를 스케줄러별로 분리해서 보여준다. 예를 들어 `sjf`만 실패하면 어떤 스케줄러가 실패했는지 알기 쉽다.

```python
self.assertEqual(len(result.passengers), EXPECTED_PASSENGER_COUNT)
self.assertEqual(len(result.completed_passengers), EXPECTED_PASSENGER_COUNT)
```

첫 번째 줄은 결과 객체 안에 승객 50명이 유지되는지 확인한다.

두 번째 줄은 완료된 승객도 50명인지 확인한다. 즉, 스케줄러가 중간에 승객을 누락하지 않았는지 검사한다.

## service_time 보존 테스트

```python
def test_all_schedulers_preserve_required_service_time_total(self):
    for scheduler_name in SCHEDULER_ORDER:
        with self.subTest(scheduler=scheduler_name):
            result = run_scheduler(parse_input_file(INPUT_PATH), scheduler_name)

            self.assertEqual(
                sum(passenger.service_time for passenger in result.passengers),
                EXPECTED_TOTAL_SERVICE_TIME,
                "completed passenger service_time total must match input workload total.",
            )
```

이 테스트는 시뮬레이션을 실행해도 승객들의 `service_time` 값이 바뀌지 않는지 확인한다.

스케줄러는 승객의 처리 순서를 정할 뿐이다. 승객의 실제 서비스 시간 자체를 줄이거나 늘리면 안 된다.

## 완료 시간과 Turnaround Time 검증 테스트

```python
def test_all_schedulers_record_valid_completion_and_turnaround_times(self):
    for scheduler_name in SCHEDULER_ORDER:
        with self.subTest(scheduler=scheduler_name):
            result = run_scheduler(parse_input_file(INPUT_PATH), scheduler_name)

            for passenger in result.passengers:
                self.assertIsNotNone(passenger.service_start_time)
                self.assertIsNotNone(passenger.completion_time)
                self.assertIsNotNone(passenger.turnaround_time)
```

모든 승객에 대해 `service_start_time`, `completion_time`, `turnaround_time`이 기록되었는지 확인한다.

`assertIsNotNone()`은 값이 `None`이 아닌지 검사한다. `None`이면 아직 기록되지 않았다는 뜻이다.

그 다음 계산식이 맞는지 확인한다.

```python
self.assertEqual(
    passenger.completion_time,
    passenger.service_start_time + passenger.service_time,
)
```

완료 시간은 다음과 같아야 한다.

```text
completion_time = service_start_time + service_time
```

또 다른 계산식은 다음과 같다.

```python
self.assertEqual(
    passenger.turnaround_time,
    passenger.completion_time - passenger.arrival_time,
)
```

Turnaround Time은 도착부터 완료까지 걸린 전체 시간이다.

```text
turnaround_time = completion_time - arrival_time
```

## 마지막 실행 코드

```python
if __name__ == "__main__":
    unittest.main()
```

이 파일을 직접 실행하면 `unittest.main()`이 테스트를 찾아 실행한다.

예를 들어 다음처럼 실행할 수 있다.

```powershell
python test_scheduler.py
```

다만 자세한 테스트 이름을 보려면 보통 다음 명령을 더 많이 사용한다.

```powershell
python -m unittest -v test_scheduler.py
```

## 보고서 생성과의 연결

`test_scheduler.py`가 통과한다는 것은 다음을 의미한다.

1. `input.txt`의 승객 수와 전체 서비스 시간이 예상과 같다.
2. `scheduler.py`가 모든 스케줄러를 실행할 수 있다.
3. 모든 승객이 완료된다.
4. 결과 CSV에 들어갈 핵심 시간 값이 올바른 공식으로 계산된다.

따라서 `generate_final_report.py`가 `output/*.csv`를 읽어 보고서를 만들 때, 그 CSV의 기본 신뢰성을 이 테스트가 뒷받침한다.
