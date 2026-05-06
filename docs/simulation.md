# simulation.py 설명

## 파일의 역할

`simulation.py`는 공항 체크인 시뮬레이션을 실제로 진행하는 엔진입니다.

중요한 점은 이 파일이 "어떤 승객을 먼저 처리할지"를 직접 결정하지 않는다는 것입니다. 그 결정은 `strategies.py`에 있는 스케줄러가 합니다. `simulation.py`는 현재 시간, 대기열, 카운터 상태를 관리하면서 스케줄러에게 다음 승객 선택을 요청합니다.

쉽게 말하면 역할은 다음과 같습니다.

- 승객이 도착할 시간이 되면 대기열에 넣기
- 카운터의 서비스 완료 시간이 되면 승객 완료 처리하기
- 빈 카운터가 있으면 스케줄러에게 다음 승객을 물어보기
- 다음 이벤트 시간까지 시뮬레이션 시간을 이동시키기
- 모든 승객이 끝나면 `SimulationResult`를 반환하기

## 전체 구조

| 구간 | 역할 |
| --- | --- |
| import 구문 | 복사 기능, 타입 규칙, 모델 클래스를 가져옴 |
| `SchedulerProtocol` | 스케줄러가 반드시 가져야 할 메서드 모양을 정의 |
| `SimulationEngine.__init__()` | 시뮬레이션 실행에 필요한 초기 상태 준비 |
| `SimulationEngine.run()` | 전체 시뮬레이션 반복 실행 |
| `_reset()` | 실행 전 상태 초기화 |
| `_move_arrivals_to_ready_queue()` | 도착한 승객을 대기열로 이동 |
| `_complete_due_services()` | 완료 시간이 된 카운터 처리 |
| `_assign_idle_counters()` | 빈 카운터에 승객 배정 |
| `_next_event_time()` | 다음으로 시간이 이동할 지점 계산 |
| `_advance_time()` | 시간을 이동하고 카운터 유휴 시간 누적 |
| `_log()` | 이벤트 로그 저장 |

## 코드 설명

### import 구문

```python
from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from models import Counter, Passenger, SimulationResult, create_default_counters
```

- `from __future__ import annotations`
  - 타입 힌트를 더 유연하게 처리하게 해 줍니다.
  - 실행 흐름을 직접 바꾸는 핵심 코드는 아닙니다.

- `from copy import deepcopy`
  - 객체를 깊게 복사하기 위해 가져옵니다.
  - `deepcopy`는 리스트 안의 객체까지 새로 복사합니다.
  - 이 프로젝트에서는 여러 스케줄러를 비교할 때 한 스케줄러의 실행 결과가 다른 스케줄러 실행에 섞이지 않도록 사용합니다.

- `from typing import Protocol`
  - `Protocol`은 "이런 메서드를 가진 객체라면 사용할 수 있다"는 규칙을 표현할 때 사용합니다.
  - 꼭 같은 부모 클래스를 상속하지 않아도, 필요한 메서드 모양만 맞으면 사용할 수 있게 하는 타입 힌트 도구입니다.

- `from models import ...`
  - `models.py`에서 정의한 클래스와 함수를 가져옵니다.
  - `Counter`: 카운터 객체
  - `Passenger`: 승객 객체
  - `SimulationResult`: 최종 결과 객체
  - `create_default_counters`: 기본 카운터 생성 함수

### `SchedulerProtocol` 클래스

```python
class SchedulerProtocol(Protocol):
    def select_next_passenger(
        self,
        ready_queue: list[Passenger],
        counters: list[Counter],
        current_time: int,
        counter: Counter,
    ) -> Passenger | None:
        ...
```

이 클래스는 실제 스케줄러 클래스가 아니라, 스케줄러가 어떤 메서드를 가져야 하는지 알려 주는 타입 규칙입니다.

- `class SchedulerProtocol(Protocol):`
  - `SchedulerProtocol`이라는 프로토콜을 정의합니다.
  - `Protocol`은 "이 모양을 만족하는 객체"를 의미합니다.

- `def select_next_passenger(...)`
  - 스케줄러가 반드시 제공해야 하는 메서드 이름입니다.
  - `simulation.py`는 이 메서드를 호출해서 다음 승객을 선택합니다.

- `ready_queue: list[Passenger]`
  - 현재 기다리고 있는 승객 목록입니다.

- `counters: list[Counter]`
  - 전체 카운터 목록입니다.

- `current_time: int`
  - 현재 시뮬레이션 시간입니다.

- `counter: Counter`
  - 지금 승객을 배정하려는 카운터입니다.

- `-> Passenger | None`
  - 반환값이 `Passenger`이거나 `None`일 수 있다는 뜻입니다.
  - `| None`은 Python 3.10 이후 문법입니다.
  - `None`은 "지금 이 카운터에 배정할 승객이 없다"는 뜻입니다.

- `...`
  - ellipsis라고 부릅니다.
  - 여기서는 함수 내용을 실제로 구현하지 않는다는 표시입니다.
  - `Protocol`에서는 메서드 모양만 중요하므로 본문을 `...`로 둡니다.

`strategies.py`의 `BaselineA_FCFS`, `BaselineB_Priority`, `BaselineC_SJF`, `OurScheduler`는 모두 `select_next_passenger()`를 구현하므로 이 프로토콜을 만족합니다.

## `SimulationEngine` 클래스

### 생성자 `__init__()`

```python
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
```

`__init__()`은 객체가 만들어질 때 자동으로 실행되는 특별한 메서드입니다.

예를 들어 다음 코드가 실행되면,

```python
engine = SimulationEngine(passengers=passengers, enable_log=True)
```

`SimulationEngine.__init__()`이 호출됩니다.

- `self`
  - 현재 만들어지는 `SimulationEngine` 객체 자신입니다.
  - `self.passengers`처럼 쓰면 이 객체 안에 값을 저장합니다.

- `passengers: list[Passenger]`
  - 시뮬레이션에 사용할 승객 목록입니다.

- `counters: list[Counter] | None = None`
  - 사용할 카운터 목록입니다.
  - 값을 넘기지 않으면 `None`이고, 이 경우 기본 카운터 5개를 사용합니다.

- `enable_log: bool = True`
  - 로그를 남길지 여부입니다.
  - 기본값은 `True`입니다.

#### 승객 목록 복사와 정렬

```python
self.passengers = sorted(deepcopy(passengers), key=lambda passenger: passenger.sort_key())
```

- `deepcopy(passengers)`
  - 승객 목록을 깊게 복사합니다.
  - 원본 `passengers`를 직접 수정하지 않기 위해서입니다.
  - `Passenger` 객체 안의 상태값도 새 객체로 복사됩니다.

- `sorted(..., key=...)`
  - 목록을 정렬한 새 리스트를 만듭니다.

- `lambda passenger: passenger.sort_key()`
  - 작은 익명 함수입니다.
  - 각 승객을 어떤 기준으로 정렬할지 알려 줍니다.
  - 여기서는 승객의 `sort_key()` 결과를 기준으로 정렬합니다.

결과적으로 승객은 도착 시간, 승객 ID 순서로 정렬됩니다.

#### 카운터 목록 준비

```python
self.counters = deepcopy(counters) if counters is not None else create_default_counters()
```

이 줄은 조건 표현식입니다.

뜻은 다음과 같습니다.

```python
if counters is not None:
    self.counters = deepcopy(counters)
else:
    self.counters = create_default_counters()
```

- 사용자가 카운터 목록을 직접 넘겼으면 그 목록을 깊게 복사합니다.
- 넘기지 않았으면 `create_default_counters()`로 기본 카운터를 만듭니다.

#### 실행 상태 초기화

```python
self.enable_log = enable_log
self.current_time = 0
self.ready_queue: list[Passenger] = []
self.completed_passengers: list[Passenger] = []
self.event_log: list[str] = []
```

- `self.enable_log`
  - 로그를 남길지 저장합니다.

- `self.current_time = 0`
  - 시뮬레이션 시작 시간을 0으로 둡니다.

- `self.ready_queue`
  - 현재 도착했지만 아직 서비스 시작 전인 승객 목록입니다.

- `self.completed_passengers`
  - 서비스가 완료된 승객 목록입니다.

- `self.event_log`
  - 로그 문자열들을 저장하는 리스트입니다.

### `run()` 메서드

```python
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
```

`run()`은 시뮬레이션 전체를 실행하는 핵심 메서드입니다.

#### 시작 전 초기화

```python
self._reset()
```

- `_reset()`을 호출해서 이전 실행 상태를 모두 지웁니다.
- 메서드 이름 앞의 `_`는 "클래스 내부에서 주로 쓰는 메서드"라는 관례입니다.

#### 기본 변수 준비

```python
next_arrival_index = 0
total_passenger_count = len(self.passengers)
```

- `next_arrival_index`
  - 아직 대기열에 넣지 않은 다음 승객의 위치입니다.
  - 승객 목록은 이미 도착 시간 순서로 정렬되어 있으므로, 이 인덱스를 앞으로 이동시키며 처리합니다.

- `len(self.passengers)`
  - 전체 승객 수를 구합니다.

#### 메인 반복문

```python
while len(self.completed_passengers) < total_passenger_count:
```

- `while`은 조건이 참인 동안 계속 반복합니다.
- 완료된 승객 수가 전체 승객 수보다 적으면 아직 시뮬레이션이 끝나지 않은 것입니다.

반복문 안에서는 매 시간 다음 순서로 처리합니다.

```python
next_arrival_index = self._move_arrivals_to_ready_queue(next_arrival_index)
self._complete_due_services()
self._assign_idle_counters(scheduler)
```

1. 현재 시간까지 도착한 승객을 대기열로 옮깁니다.
2. 현재 시간에 완료되는 서비스를 처리합니다.
3. 빈 카운터에 승객을 배정합니다.

#### 종료 확인

```python
if len(self.completed_passengers) >= total_passenger_count:
    break
```

- 모든 승객이 완료되었으면 반복문을 빠져나갑니다.
- `break`는 반복문을 즉시 종료하는 키워드입니다.

#### 다음 이벤트 시간 계산

```python
next_time = self._next_event_time(next_arrival_index)
if next_time is None:
    raise RuntimeError("Simulation cannot continue because no future event exists.")
```

- 다음에 일이 생길 시간을 계산합니다.
- 일이란 "새 승객 도착" 또는 "카운터 서비스 완료"입니다.
- 다음 이벤트가 없다면 시뮬레이션이 더 진행될 수 없는 비정상 상태이므로 에러를 냅니다.

#### 시간 이동

```python
self._advance_time(next_time)
```

- 현재 시간을 `next_time`으로 이동합니다.
- 이 시뮬레이션은 시간을 `0, 1, 2, 3...`처럼 매번 1씩 증가시키지 않습니다.
- 다음 이벤트가 있는 시간으로 바로 점프합니다.

#### 결과 반환

```python
return SimulationResult(
    passengers=sorted(self.passengers, key=lambda passenger: passenger.sort_key()),
    counters=self.counters,
    event_log=list(self.event_log),
    finished_at=self.current_time,
)
```

- 모든 승객이 완료되면 결과 객체를 만들어 반환합니다.
- `event_log=list(self.event_log)`는 로그 리스트를 복사해서 넣습니다.
- `finished_at`에는 마지막 시뮬레이션 시간이 들어갑니다.

## 내부 메서드 설명

### `_reset()`

```python
def _reset(self) -> None:
    self.current_time = 0
    self.ready_queue = []
    self.completed_passengers = []
    self.event_log = []

    for passenger in self.passengers:
        passenger.reset_runtime_state()
    for counter in self.counters:
        counter.reset_runtime_state()
```

시뮬레이션 실행 전에 상태를 초기화합니다.

- `self.current_time = 0`
  - 시간을 처음으로 되돌립니다.

- `self.ready_queue = []`
  - 대기열을 빈 리스트로 만듭니다.

- `self.completed_passengers = []`
  - 완료 승객 목록을 비웁니다.

- `self.event_log = []`
  - 로그를 비웁니다.

- `for passenger in self.passengers:`
  - 모든 승객을 하나씩 반복합니다.

- `passenger.reset_runtime_state()`
  - 승객의 시작 시간, 완료 시간, Turnaround Time 등을 초기화합니다.

- `for counter in self.counters:`
  - 모든 카운터를 하나씩 반복합니다.

- `counter.reset_runtime_state()`
  - 카운터의 현재 승객, 처리 기록, 유휴 시간 등을 초기화합니다.

### `_move_arrivals_to_ready_queue()`

```python
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
```

현재 시간까지 도착한 승객을 `ready_queue`에 넣습니다.

- `start_index`
  - 승객 목록에서 어디부터 확인할지 나타냅니다.

- `index = start_index`
  - 전달받은 시작 위치를 지역 변수로 복사합니다.

- `while index < len(self.passengers) and ...`
  - 아직 확인할 승객이 남아 있고, 그 승객의 도착 시간이 현재 시간 이하이면 반복합니다.
  - `and`는 두 조건이 모두 참이어야 전체가 참입니다.

- `self.passengers[index].arrival_time <= self.current_time`
  - 승객이 이미 도착했는지 확인합니다.
  - 도착 시간이 현재 시간보다 작거나 같으면 대기열에 들어갈 수 있습니다.

- `passenger = self.passengers[index]`
  - 현재 인덱스의 승객을 가져옵니다.

- `self.ready_queue.append(passenger)`
  - 대기열에 승객을 추가합니다.

- `self._log(...)`
  - 도착 로그를 남깁니다.

- `index += 1`
  - 다음 승객으로 이동합니다.

- `self.ready_queue.sort(...)`
  - 대기열을 도착 시간과 승객 ID 기준으로 정렬합니다.

- `return index`
  - 다음에 확인해야 할 승객 위치를 반환합니다.

이 메서드는 승객 목록을 처음부터 매번 다시 보지 않기 위해 `index`를 사용합니다.

### `_complete_due_services()`

```python
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
```

현재 시간에 완료되는 서비스를 처리합니다.

- `for counter in self.counters:`
  - 모든 카운터를 하나씩 확인합니다.

- `passenger = counter.complete_current_passenger(self.current_time)`
  - 해당 카운터에서 완료할 승객이 있는지 확인합니다.
  - 완료된 승객이 있으면 `Passenger` 객체가 반환되고, 없으면 `None`이 반환됩니다.

- `if passenger is None:`
  - 완료된 승객이 없으면 다음 카운터로 넘어갑니다.

- `continue`
  - 현재 반복의 나머지 코드를 건너뛰고 다음 반복으로 갑니다.

- `self.completed_passengers.append(passenger)`
  - 완료 승객 목록에 추가합니다.

- `self._log(...)`
  - 완료 로그를 남깁니다.

### `_assign_idle_counters()`

```python
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
```

빈 카운터에 승객을 배정하는 메서드입니다. 이 부분에서 `simulation.py`와 스케줄러가 연결됩니다.

#### 반복 제어

```python
made_assignment = True
while made_assignment:
    made_assignment = False
```

- `made_assignment`는 이번 반복에서 승객 배정이 있었는지 기록합니다.
- 처음에는 `True`로 시작해서 반복문에 들어갑니다.
- 반복문 안에서 일단 `False`로 바꿉니다.
- 실제 배정이 하나라도 일어나면 다시 `True`가 됩니다.
- 이렇게 하면 가능한 배정을 모두 시도할 수 있습니다.

#### 카운터 확인

```python
for counter in self.counters:
    if not counter.is_idle or not self.ready_queue:
        continue
```

- 모든 카운터를 하나씩 봅니다.
- 카운터가 바쁘거나 대기열이 비어 있으면 배정할 수 없으므로 넘어갑니다.

#### 스케줄러 호출

```python
selected = scheduler.select_next_passenger(
    ready_queue=list(self.ready_queue),
    counters=self.counters,
    current_time=self.current_time,
    counter=counter,
)
```

스케줄러에게 "이 카운터에 누구를 배정할까?"라고 묻는 부분입니다.

- `scheduler.select_next_passenger(...)`
  - 실제 승객 선택 알고리즘은 이 메서드 안에 있습니다.
  - `simulation.py`는 알고리즘 내용을 모릅니다.

- `ready_queue=list(self.ready_queue)`
  - 현재 대기열을 복사해서 넘깁니다.
  - `list(...)`는 새 리스트를 만듭니다.
  - 스케줄러가 실수로 대기열을 직접 바꾸는 일을 줄이려는 목적입니다.

- `counters=self.counters`
  - 전체 카운터 상태를 넘깁니다.

- `current_time=self.current_time`
  - 현재 시간을 넘깁니다.

- `counter=counter`
  - 지금 승객을 배정하려는 카운터를 넘깁니다.

#### 선택 결과 처리

```python
if selected is None:
    self._log(f"time={self.current_time}: {counter.counter_id} is idle.")
    continue
```

- 스케줄러가 `None`을 반환하면 지금 이 카운터에 배정할 승객이 없다는 뜻입니다.
- 로그를 남기고 다음 카운터로 넘어갑니다.

```python
if selected not in self.ready_queue:
    raise ValueError(...)
```

- 스케줄러가 반환한 승객이 실제 대기열에 있는지 검사합니다.
- 대기열에 없는 승객을 반환하면 잘못된 스케줄러 구현이므로 에러를 냅니다.

```python
self.ready_queue.remove(selected)
counter.assign_passenger(selected, self.current_time)
made_assignment = True
```

- `remove(selected)`는 대기열에서 해당 승객을 제거합니다.
- `counter.assign_passenger(...)`는 카운터에 승객을 배정하고 서비스 시작 상태를 기록합니다.
- 배정이 일어났으므로 `made_assignment`를 `True`로 바꿉니다.

### `_next_event_time()`

```python
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
```

다음 이벤트 시간을 찾는 메서드입니다.

다음 이벤트는 두 종류입니다.

- 아직 도착하지 않은 다음 승객의 도착 시간
- 현재 바쁜 카운터의 완료 시간

코드 의미는 다음과 같습니다.

- `candidate_times: list[int] = []`
  - 후보 시간을 담을 빈 리스트입니다.

- `if next_arrival_index < len(self.passengers):`
  - 아직 도착하지 않은 승객이 남아 있는지 확인합니다.

- `candidate_times.append(...)`
  - 다음 승객의 도착 시간을 후보에 추가합니다.

- `for counter in self.counters:`
  - 모든 카운터를 확인합니다.

- `if not counter.is_idle:`
  - 바쁜 카운터라면 완료 시간이 있습니다.

- `candidate_times.append(counter.busy_until)`
  - 그 카운터의 완료 시간을 후보에 추가합니다.

- `future_times = [time for time in candidate_times if time > self.current_time]`
  - 현재 시간보다 미래인 시간만 남깁니다.

- `if not future_times: return None`
  - 미래 이벤트가 없으면 `None`을 반환합니다.

- `return min(future_times)`
  - 가장 가까운 미래 시간을 반환합니다.

### `_advance_time()`

```python
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
```

현재 시간을 다음 이벤트 시간으로 이동합니다.

- `if next_time <= self.current_time:`
  - 시간이 뒤로 가거나 그대로 있으면 잘못된 상황입니다.

- `duration = next_time - self.current_time`
  - 이번에 시간이 얼마나 흘렀는지 계산합니다.

- `for counter in self.counters:`
  - 모든 카운터를 확인합니다.

- `counter.add_idle_time(duration)`
  - 카운터가 비어 있다면 해당 시간만큼 유휴 시간이 증가합니다.
  - 바쁜 카운터는 `Counter.add_idle_time()` 내부에서 유휴 시간이 증가하지 않습니다.

#### `any()` 사용 부분

```python
any(counter.is_idle for counter in self.counters)
```

- `any()`는 반복되는 값 중 하나라도 참이면 `True`를 반환합니다.
- 여기서는 "비어 있는 카운터가 하나라도 있는가?"를 확인합니다.

#### 대기 승객이 있는데 빈 카운터가 있는 경우

```python
if self.ready_queue and any(counter.is_idle for counter in self.counters):
```

- 대기 승객이 있고 빈 카운터도 있다는 뜻입니다.
- 이 경우는 스케줄러가 특정 이유로 배정을 하지 않았거나, 카운터 조건에 맞는 승객이 없을 수 있습니다.

#### 대기 승객은 없고 빈 카운터가 있는 경우

```python
elif any(counter.is_idle for counter in self.counters):
```

- 빈 카운터가 있지만 기다리는 승객은 없는 상황입니다.
- 이때는 카운터가 정상적으로 쉬고 있는 상태입니다.

#### 시간 갱신

```python
self.current_time = next_time
```

- 마지막에 현재 시간을 실제로 이동합니다.
- 로그는 이동 전 시간을 기준으로 남기고, 그 뒤 시간이 바뀝니다.

### `_log()`

```python
def _log(self, message: str) -> None:
    if self.enable_log:
        self.event_log.append(message)
```

로그를 저장하는 간단한 메서드입니다.

- `message: str`
  - 로그 메시지 문자열입니다.

- `if self.enable_log:`
  - 로그 기능이 켜져 있을 때만 저장합니다.

- `self.event_log.append(message)`
  - 로그 리스트 끝에 메시지를 추가합니다.

## 주요 클래스/함수 설명

| 이름 | 종류 | 핵심 역할 |
| --- | --- | --- |
| `SchedulerProtocol` | 프로토콜 | 스케줄러가 가져야 할 메서드 모양을 정의 |
| `SimulationEngine` | 클래스 | 전체 시뮬레이션 상태와 실행 흐름을 관리 |
| `__init__()` | 메서드 | 승객, 카운터, 시간, 대기열, 로그 초기 준비 |
| `run()` | 메서드 | 모든 승객이 완료될 때까지 시뮬레이션 실행 |
| `_reset()` | 내부 메서드 | 이전 실행 상태 제거 |
| `_move_arrivals_to_ready_queue()` | 내부 메서드 | 현재 시간까지 도착한 승객을 대기열에 추가 |
| `_complete_due_services()` | 내부 메서드 | 완료 시간이 된 승객을 완료 처리 |
| `_assign_idle_counters()` | 내부 메서드 | 스케줄러를 호출해 빈 카운터에 승객 배정 |
| `_next_event_time()` | 내부 메서드 | 다음 도착 또는 완료 시간 계산 |
| `_advance_time()` | 내부 메서드 | 시간을 이동하고 유휴 시간을 누적 |
| `_log()` | 내부 메서드 | 이벤트 로그 저장 |

## 다른 파일과의 관계

### `models.py`와의 관계

`simulation.py`는 `models.py`의 데이터 클래스를 사용합니다.

- `Passenger`
  - 승객 목록, 대기열, 완료 목록에 사용됩니다.

- `Counter`
  - 카운터 상태를 관리할 때 사용됩니다.

- `SimulationResult`
  - 시뮬레이션 결과를 반환할 때 사용됩니다.

- `create_default_counters()`
  - 카운터 목록이 따로 없을 때 기본 카운터를 만들 때 사용됩니다.

### `strategies.py`와의 관계

`simulation.py`는 스케줄링 알고리즘을 직접 구현하지 않습니다. 대신 다음 메서드를 호출합니다.

```python
scheduler.select_next_passenger(...)
```

`strategies.py`에 있는 각 스케줄러는 이 메서드를 구현합니다.

- `BaselineA_FCFS`
- `BaselineB_Priority`
- `BaselineC_SJF`
- `OurScheduler`

따라서 같은 `SimulationEngine`을 사용하면서 스케줄러만 바꿔 여러 알고리즘을 비교할 수 있습니다.

### `scheduler.py`와의 관계

`scheduler.py`에서는 다음 흐름으로 `simulation.py`를 사용합니다.

```python
engine = SimulationEngine(passengers=passengers, enable_log=True)
result = engine.run(scheduler)
```

- `scheduler.py`가 입력 파일을 읽어 `Passenger` 목록을 만듭니다.
- 선택한 스케줄러 객체를 만듭니다.
- `SimulationEngine`에 승객 목록을 넣습니다.
- `engine.run(scheduler)`로 시뮬레이션을 실행합니다.
- 반환된 `SimulationResult`를 CSV와 로그로 저장합니다.

## 코드 실행 흐름

`SimulationEngine.run()` 기준 실행 순서는 다음과 같습니다.

1. `_reset()`으로 승객과 카운터의 이전 실행 상태를 초기화합니다.
2. `next_arrival_index`를 0으로 시작합니다.
3. 완료 승객 수가 전체 승객 수와 같아질 때까지 반복합니다.
4. `_move_arrivals_to_ready_queue()`로 현재 시간까지 도착한 승객을 대기열에 넣습니다.
5. `_complete_due_services()`로 현재 시간에 끝나는 서비스를 완료 처리합니다.
6. `_assign_idle_counters()`로 빈 카운터에 승객을 배정합니다.
7. 모든 승객이 완료되었으면 반복을 종료합니다.
8. `_next_event_time()`으로 다음 도착 시간 또는 다음 완료 시간을 찾습니다.
9. `_advance_time()`으로 그 시간까지 이동합니다.
10. 모든 승객이 완료되면 `SimulationResult`를 만들어 반환합니다.

## 처음 읽을 때 핵심 포인트

- `simulation.py`는 시뮬레이션의 시간 흐름을 관리하는 파일입니다.
- 실제 승객 선택 기준은 `strategies.py`의 스케줄러가 결정합니다.
- `ready_queue`는 도착했지만 아직 서비스 시작 전인 승객 목록입니다.
- `completed_passengers`는 서비스가 끝난 승객 목록입니다.
- 카운터가 승객을 받으면 `Counter.assign_passenger()`가 실행됩니다.
- 카운터의 완료 시간이 되면 `Counter.complete_current_passenger()`가 실행됩니다.
- 시간은 1씩 증가하지 않고, 다음 이벤트 시간으로 바로 이동합니다.
- `deepcopy`를 사용해서 시뮬레이션 실행 간 상태가 섞이지 않도록 합니다.
- `SchedulerProtocol`은 실제 코드 실행보다 "스케줄러가 이런 메서드를 가져야 한다"는 설명 역할이 큽니다.
