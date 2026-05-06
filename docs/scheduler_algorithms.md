# 스케줄러 알고리즘 설명

## 파일의 역할

이 문서는 `strategies.py`에 구현된 네 가지 스케줄러 알고리즘을 초보자 관점에서 비교합니다.

대상 알고리즘은 다음입니다.

- FCFS
- Priority
- SJF
- OurScheduler

`scheduler.py`는 명령어를 처리하고, `simulation.py`는 시간 흐름을 진행합니다. 하지만 **어떤 승객을 다음에 처리할지 결정하는 핵심 기준**은 `strategies.py`에 있습니다.

## 전체 구조

스케줄러들은 모두 같은 메서드를 가집니다.

```python
select_next_passenger(
    ready_queue,
    counters,
    current_time,
    counter,
)
```

이 메서드는 현재 대기 중인 승객 중 한 명을 선택합니다.

입력값 의미:

| 인자 | 의미 |
| --- | --- |
| `ready_queue` | 현재 도착해서 기다리는 승객 목록 |
| `counters` | 전체 카운터 목록 |
| `current_time` | 현재 시뮬레이션 시간 |
| `counter` | 지금 배정하려는 카운터 |

반환값:

| 반환값 | 의미 |
| --- | --- |
| `Passenger` | 선택된 승객 |
| `None` | 지금 선택할 승객 없음 |

## import 구문 설명

알고리즘 이해에 필요한 import는 주로 `strategies.py`에 있습니다.

```python
from abc import ABC, abstractmethod
```

모든 스케줄러가 같은 메서드를 구현하도록 강제하기 위해 사용합니다.

```python
from collections import defaultdict
```

`OurScheduler`에서 승객을 등급별 큐로 나누기 위해 사용합니다.

```python
import re
```

승객 ID 안의 숫자 부분을 찾아 정렬 기준으로 쓰기 위해 사용합니다.

```python
from typing import Any, Iterable, Optional
```

타입 힌트입니다.

`Any`는 어떤 값이든 가능하다는 뜻이고, `Optional[int]`는 `int` 또는 `None`이 가능하다는 뜻입니다.

`scheduler.py` 쪽에서는 다음 import도 중요합니다.

```python
import argparse
from pathlib import Path
```

`argparse`는 명령어 옵션을 해석하고, `Path`는 파일 경로를 다룹니다.

## 코드 설명

## 공통 인터페이스

```python
class SchedulerStrategy(ABC):
    name = "SchedulerStrategy"

    @abstractmethod
    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        raise NotImplementedError
```

`SchedulerStrategy`는 모든 스케줄러의 부모 클래스입니다.

`ABC`는 추상 클래스를 만들 때 사용합니다.

`@abstractmethod`가 붙은 메서드는 자식 클래스에서 반드시 구현해야 합니다.

이 구조 덕분에 `simulation.py`는 구체적인 스케줄러 이름을 몰라도 됩니다.

그저 다음 메서드만 호출합니다.

```python
scheduler.select_next_passenger(...)
```

이것이 객체지향에서 말하는 다형성입니다.

## Python 문법 핵심

### `min()`

```python
min(ready_queue, key=lambda passenger: 기준값)
```

`min()`은 가장 작은 기준값을 가진 항목을 고릅니다.

FCFS, Priority, SJF는 작은 값이 더 좋은 기준이므로 `min()`을 사용합니다.

### `max()`

```python
max(candidate_pool, key=lambda passenger: 점수)
```

`max()`는 가장 큰 기준값을 가진 항목을 고릅니다.

OurScheduler는 점수가 높을수록 좋은 승객이므로 `max()`를 사용합니다.

### `lambda`

```python
lambda passenger: (_arrival_time(passenger), _passenger_id_key(passenger))
```

`lambda`는 짧은 함수를 한 줄로 만드는 문법입니다.

위 코드는 아래 함수와 비슷합니다.

```python
def key_function(passenger):
    return (_arrival_time(passenger), _passenger_id_key(passenger))
```

### 튜플 정렬

파이썬은 튜플을 비교할 때 앞에서부터 차례대로 비교합니다.

```python
(0, 3) < (1, 1)
(1, 2) < (1, 5)
```

스케줄러에서 자주 나오는 기준은 이런 형태입니다.

```python
(
    첫 번째 기준,
    두 번째 기준,
    세 번째 기준,
)
```

첫 번째 기준이 다르면 첫 번째 기준만 보고 결정합니다.

첫 번째 기준이 같을 때만 두 번째 기준을 봅니다.

### dict comprehension

`scheduler.py`에서 모든 스케줄러를 실행할 때 사용합니다.

```python
results = {
    scheduler_name: run_scheduler(passengers, scheduler_name)
    for scheduler_name in scheduler_names
}
```

아래 코드와 같은 의미입니다.

```python
results = {}
for scheduler_name in scheduler_names:
    results[scheduler_name] = run_scheduler(passengers, scheduler_name)
```

## 스케줄러별 선택 기준

## 1. FCFS

FCFS는 `First-Come First-Served`입니다.

뜻은 **먼저 온 승객을 먼저 처리한다**입니다.

코드:

```python
return min(
    ready_queue,
    key=lambda passenger: (
        _arrival_time(passenger),
        _passenger_id_key(passenger),
    ),
)
```

선택 순서:

1. 도착 시간이 가장 빠른 승객
2. 도착 시간이 같으면 ID가 작은 승객

예:

| 승객 | 도착 시간 | 서비스 시간 |
| --- | --- | --- |
| P1 | 0 | 10 |
| P2 | 3 | 2 |
| P3 | 3 | 1 |

FCFS는 P1을 먼저 고릅니다.

P2와 P3가 동시에 도착했다면 ID가 작은 P2가 P3보다 먼저입니다.

장점:

- 매우 단순함
- 먼저 온 사람을 먼저 처리하므로 직관적임

단점:

- 서비스 시간이 긴 승객이 앞에 있으면 뒤의 짧은 승객들이 오래 기다릴 수 있음

## 2. Priority

Priority 스케줄러는 승객 등급을 우선합니다.

코드:

```python
return min(
    ready_queue,
    key=lambda passenger: (
        _passenger_class(passenger),
        _arrival_time(passenger),
        _passenger_id_key(passenger),
    ),
)
```

승객 등급 숫자는 다음입니다.

```python
FIRST = 1
BUSINESS = 2
ECONOMY = 3
```

`min()`은 작은 값을 고르므로 우선순위는 다음입니다.

```text
First -> Business -> Economy
```

선택 순서:

1. 등급 숫자가 가장 작은 승객
2. 같은 등급이면 도착 시간이 빠른 승객
3. 도착 시간도 같으면 ID가 작은 승객

예:

| 승객 | 등급 | 도착 시간 |
| --- | --- | --- |
| P1 | Economy, 3 | 0 |
| P2 | First, 1 | 5 |
| P3 | Business, 2 | 2 |

세 승객이 모두 `ready_queue`에 있다면 Priority는 P2를 먼저 고릅니다.

P2가 First 등급이기 때문입니다.

장점:

- First, Business 승객을 빠르게 처리할 수 있음

단점:

- Economy 승객이 계속 밀릴 수 있음
- 기다린 시간이 길어져도 등급이 낮으면 불리함

## 3. SJF

SJF는 `Shortest Job First`입니다.

뜻은 **서비스 시간이 가장 짧은 승객을 먼저 처리한다**입니다.

코드:

```python
return min(
    ready_queue,
    key=lambda passenger: (
        _service_time(passenger),
        _arrival_time(passenger),
        _passenger_id_key(passenger),
    ),
)
```

선택 순서:

1. 서비스 시간이 가장 짧은 승객
2. 서비스 시간이 같으면 도착 시간이 빠른 승객
3. 도착 시간도 같으면 ID가 작은 승객

예:

| 승객 | 도착 시간 | 서비스 시간 |
| --- | --- | --- |
| P1 | 0 | 10 |
| P2 | 1 | 2 |
| P3 | 2 | 1 |

세 승객이 모두 기다리고 있다면 SJF는 P3를 먼저 고릅니다.

서비스 시간이 `1`로 가장 짧기 때문입니다.

장점:

- 평균 대기 시간이나 평균 반환 시간을 줄이는 데 유리할 수 있음

단점:

- 서비스 시간이 긴 승객이 계속 뒤로 밀릴 수 있음
- 새로 온 짧은 작업이 많으면 긴 작업의 대기 시간이 커질 수 있음

주의:

이 프로젝트의 SJF는 **비선점형**입니다.

즉 한 승객이 서비스를 시작하면 중간에 멈추지 않습니다.

## 4. OurScheduler

`OurScheduler`는 여러 기준을 섞은 스케줄러입니다.

핵심 아이디어:

- 카운터 종류를 반영함
- 승객 등급별 가중치를 반영함
- 오래 기다린 승객의 점수를 높임
- 점수가 같으면 서비스 시간이 짧은 승객을 우선함
- 그래도 같으면 먼저 온 승객을 우선함

### 카운터별 후보군

`OurScheduler`는 먼저 현재 카운터가 어떤 승객을 처리할지 후보군을 정합니다.

```python
preferred_class = _counter_preferred_class(counter)
```

기본 카운터는 다음과 같습니다.

| 카운터 | 타입 | 우선 후보 |
| --- | --- | --- |
| C1 | First | First 승객 |
| C2 | Business | Business 승객 |
| C3 | Economy | Economy 승객 |
| C4 | Flex | 전체 승객 |
| C5 | Flex | 전체 승객 |

코드:

```python
if preferred_class is None:
    return list(ready_queue)
```

Flex 카운터라면 전체 대기열을 후보로 사용합니다.

```python
preferred_queue = class_queues.get(preferred_class, [])
if preferred_queue:
    return list(preferred_queue)
```

전용 카운터라면 자기 등급 승객을 우선 후보로 사용합니다.

```python
if self.allow_dedicated_counter_borrowing:
    return list(ready_queue)
```

자기 등급 승객이 없으면 다른 등급 승객도 처리할 수 있습니다.

이 설정의 기본값은 `True`입니다.

### 점수 계산

코드:

```python
waiting_time = max(0, current_time - _arrival_time(passenger))
service_time = max(1, _service_time(passenger))
passenger_class = _passenger_class(passenger)
class_weight = self.class_weights.get(passenger_class, 1.0)

response_ratio = (waiting_time + service_time) / service_time
weighted_hrrn_score = response_ratio * class_weight
```

HRRN 공식:

```text
response_ratio = (waiting_time + service_time) / service_time
```

이 공식은 기다린 시간이 길수록 값이 커집니다.

예:

| 대기 시간 | 서비스 시간 | response_ratio |
| --- | --- | --- |
| 0 | 5 | 1.0 |
| 5 | 5 | 2.0 |
| 10 | 5 | 3.0 |

`OurScheduler`는 여기에 등급 가중치를 곱합니다.

```python
weighted_hrrn_score = response_ratio * class_weight
```

등급 가중치:

| 등급 | 값 | 가중치 |
| --- | --- | --- |
| First | 1 | 1.5 |
| Business | 2 | 1.1 |
| Economy | 3 | 1.0 |

예:

| 승객 | 등급 | response_ratio | 가중치 | 최종 점수 |
| --- | --- | --- | --- | --- |
| P1 | First | 2.0 | 1.5 | 3.0 |
| P2 | Economy | 2.5 | 1.0 | 2.5 |

이 경우 P1이 선택됩니다.

### 최종 선택 키

```python
return (
    weighted_hrrn_score,
    -service_time,
    -_arrival_time(passenger),
    _reverse_id_key(passenger),
)
```

`OurScheduler`는 `max()`로 가장 큰 튜플을 고릅니다.

따라서 기준은 다음 순서입니다.

1. `weighted_hrrn_score`가 큰 승객
2. 점수가 같으면 서비스 시간이 짧은 승객
3. 그래도 같으면 도착 시간이 빠른 승객
4. 그래도 같으면 ID가 작은 승객

왜 음수를 쓸까요?

`max()`는 큰 값을 고릅니다.

하지만 서비스 시간은 짧을수록 좋습니다.

그래서 다음처럼 음수로 바꿉니다.

```python
service_time = 3  -> -3
service_time = 10 -> -10
```

`-3`이 `-10`보다 크므로 서비스 시간이 짧은 승객이 선택됩니다.

## 실행 명령어 처리 흐름

알고리즘은 `scheduler.py`에서 실행됩니다.

명령:

```powershell
python scheduler.py input.txt --scheduler all
```

흐름:

```text
main()
  -> parse_input_file()
  -> selected_scheduler_names("all")
  -> ["fcfs", "priority", "sjf", "ours"]
  -> run_scheduler(..., "fcfs")
  -> run_scheduler(..., "priority")
  -> run_scheduler(..., "sjf")
  -> run_scheduler(..., "ours")
```

각 `run_scheduler()`는 다음을 실행합니다.

```text
create_scheduler()
  -> strategies.py의 스케줄러 객체 생성
SimulationEngine.run()
  -> 카운터가 비면 scheduler.select_next_passenger() 호출
```

즉 알고리즘은 프로그램 시작 시 한 번만 호출되는 것이 아닙니다.

시뮬레이션 중 카운터가 빈 상태가 될 때마다 반복해서 호출됩니다.

## 스케줄러 비교표

| 비교 항목 | FCFS | Priority | SJF | OurScheduler |
| --- | --- | --- | --- | --- |
| 전체 이름 | First-Come First-Served | Priority Scheduling | Shortest Job First | MLQ + Weighted HRRN + SJF |
| 핵심 질문 | 누가 먼저 왔나? | 누가 높은 등급인가? | 누가 빨리 끝나나? | 누가 종합 점수가 높은가? |
| 첫 번째 기준 | 도착 시간 | 승객 등급 | 서비스 시간 | 등급 가중 HRRN 점수 |
| 두 번째 기준 | ID | 도착 시간 | 도착 시간 | 서비스 시간 |
| 세 번째 기준 | 없음 | ID | ID | 도착 시간 |
| 카운터 전용 등급 고려 | 아니오 | 아니오 | 아니오 | 예 |
| 대기 시간 증가 반영 | 간접적 | 거의 없음 | 거의 없음 | 직접 반영 |
| 짧은 작업 우대 | 아니오 | 아니오 | 예 | 점수 동점 시 예 |
| 높은 등급 우대 | 아니오 | 강하게 우대 | 아니오 | 가중치로 우대 |
| starvation 위험 | 낮음 | Economy에 있음 | 긴 작업에 있음 | 완화됨 |
| 구현 난이도 | 쉬움 | 쉬움 | 쉬움 | 중간 |

## 초보자용 핵심 비교

FCFS는 줄 서기입니다.

먼저 온 사람이 먼저 갑니다.

Priority는 VIP 우선 줄입니다.

First, Business 승객이 Economy보다 먼저 갑니다.

SJF는 빨리 끝나는 사람 먼저 처리하는 방식입니다.

서비스 시간이 짧은 승객이 먼저 갑니다.

OurScheduler는 점수제입니다.

승객 등급, 기다린 시간, 서비스 시간을 섞어 점수를 계산하고 가장 점수가 높은 승객을 고릅니다.

## 다른 파일과의 관계

### `scheduler.py`

알고리즘 이름을 실제 클래스와 연결합니다.

```python
if name == "ours":
    return OurScheduler()
```

또한 `--scheduler all`일 때 네 알고리즘을 모두 실행합니다.

### `simulation.py`

알고리즘을 반복 호출합니다.

카운터가 비어 있고 대기 승객이 있으면 다음 호출이 발생합니다.

```python
scheduler.select_next_passenger(...)
```

선택된 승객은 대기열에서 제거되고 카운터에 배정됩니다.

### `models.py`

승객과 카운터의 데이터를 제공합니다.

알고리즘은 다음 값을 사용합니다.

| 값 | 출처 |
| --- | --- |
| `arrival_time` | `Passenger` |
| `passenger_class` | `Passenger` |
| `service_time` | `Passenger` |
| `passenger_id` | `Passenger` |
| `counter_type` | `Counter` |

### `report_utils.py`

알고리즘 실행 결과를 직접 고르지는 않습니다.

하지만 알고리즘별 결과 비교 그래프를 만들 때 사용됩니다.

흐름:

```text
각 알고리즘 실행
  -> SimulationResult 생성
  -> 평균 반환 시간 계산
  -> att_comparison.csv 생성
  -> att_comparison.png 생성
```
