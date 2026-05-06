# strategies.py 설명

## 파일의 역할

`strategies.py`는 승객을 어떤 순서로 체크인 카운터에 배정할지 결정하는 **스케줄러 알고리즘 모음**입니다.

이 파일은 시뮬레이션을 직접 실행하지 않습니다. 대신 `simulation.py`의 `SimulationEngine`이 현재 대기 중인 승객 목록(`ready_queue`)을 넘겨주면, `strategies.py` 안의 스케줄러 클래스가 그중 **다음에 처리할 승객 1명**을 골라서 반환합니다.

핵심 역할은 다음과 같습니다.

- FCFS, Priority, SJF, OurScheduler 알고리즘 구현
- 승객의 도착 시간, 등급, 서비스 시간, ID를 읽는 보조 함수 제공
- 모든 스케줄러가 따라야 하는 공통 인터페이스 정의
- 카운터가 특정 등급 전용인지, 유연 카운터인지 판별

`strategies.py`의 함수들은 대부분 `Passenger` 객체를 직접 알고 있다고 가정하지 않고, 객체 또는 딕셔너리 형태 모두 처리할 수 있게 작성되어 있습니다. 그래서 테스트나 다른 코드에서 비슷한 구조의 데이터를 넣어도 작동하기 쉽습니다.

## 전체 구조

```text
strategies.py
|
|-- import 구문
|-- 승객 등급 상수
|-- 보조 함수
|   |-- _get_value()
|   |-- _passenger_id()
|   |-- _passenger_id_key()
|   |-- _arrival_time()
|   |-- _passenger_class()
|   |-- _service_time()
|   |-- _counter_preferred_class()
|
|-- SchedulerStrategy 추상 클래스
|
|-- BaselineA_FCFS
|-- BaselineB_Priority
|-- BaselineC_SJF
|-- OurScheduler
|
|-- 별칭(alias)
```

이 파일의 가장 중요한 클래스는 다음 네 개입니다.

| 클래스 | 의미 | 선택 기준 |
| --- | --- | --- |
| `BaselineA_FCFS` | First-Come First-Served | 먼저 도착한 승객 |
| `BaselineB_Priority` | Priority Scheduling | 승객 등급 우선 |
| `BaselineC_SJF` | Shortest Job First | 서비스 시간이 짧은 승객 |
| `OurScheduler` | MLQ + Weighted HRRN + SJF | 등급, 기다린 시간, 서비스 시간 조합 |

## import 구문 설명

```python
from __future__ import annotations
```

타입 힌트를 조금 더 유연하게 쓰기 위한 구문입니다. 예를 들어 `Any | None` 같은 최신 타입 표기를 더 안정적으로 사용할 수 있게 합니다.

```python
from abc import ABC, abstractmethod
```

`ABC`는 **Abstract Base Class**, 즉 추상 기반 클래스입니다.

`abstractmethod`는 자식 클래스가 반드시 구현해야 하는 메서드를 표시할 때 사용합니다.

이 파일에서는 모든 스케줄러가 반드시 `select_next_passenger()`를 구현하도록 강제합니다.

```python
from collections import defaultdict
```

`defaultdict`는 없는 키를 조회할 때 자동으로 기본값을 만들어 주는 딕셔너리입니다.

예:

```python
class_queues: dict[int, list[Any]] = defaultdict(list)
class_queues[1].append(passenger)
```

일반 `dict`라면 `class_queues[1]`이 없을 때 에러가 나지만, `defaultdict(list)`는 자동으로 빈 리스트를 만들어 줍니다.

```python
import re
```

정규표현식 모듈입니다. 승객 ID 안에서 숫자 부분을 찾을 때 사용합니다.

예를 들어 `"P12"`에서 `12`를 뽑아 정렬 기준으로 씁니다.

```python
from typing import Any, Iterable, Optional
```

타입 힌트용 도구입니다.

- `Any`: 어떤 타입이든 가능
- `Iterable`: 반복 가능한 값, 예를 들어 리스트나 튜플
- `Optional[int]`: `int`이거나 `None`일 수 있음

## 코드 설명

### 승객 등급 상수

```python
FIRST = 1
BUSINESS = 2
ECONOMY = 3
```

승객 등급을 숫자로 표현합니다.

- `1`: First
- `2`: Business
- `3`: Economy

Priority 스케줄러에서는 숫자가 작을수록 우선순위가 높습니다. 그래서 First가 가장 먼저 선택됩니다.

```python
CLASS_WEIGHTS = {
    FIRST: 1.5,
    BUSINESS: 1.1,
    ECONOMY: 1.0,
}
```

`OurScheduler`에서 사용하는 등급별 가중치입니다.

- First 승객은 점수에 `1.5`를 곱함
- Business 승객은 점수에 `1.1`을 곱함
- Economy 승객은 점수에 `1.0`을 곱함

즉 같은 조건이면 First 승객이 더 높은 점수를 받습니다.

### `_get_value()`

```python
def _get_value(obj: Any, names: Iterable[str], default: Any = None) -> Any:
    """Read a value from either an object model or a dict-like model."""
    if obj is None:
        return default
```

객체나 딕셔너리에서 값을 읽기 위한 공통 함수입니다.

`obj`가 `None`이면 읽을 값이 없으므로 `default`를 반환합니다.

```python
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
        return default
```

`isinstance(obj, dict)`는 `obj`가 딕셔너리인지 확인합니다.

`names`에는 후보 이름들이 들어옵니다. 예를 들어 승객 ID를 찾을 때는 `("passenger_id", "pid", "id")`처럼 여러 이름을 시도합니다.

```python
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    return default
```

딕셔너리가 아니라 일반 객체라면 `hasattr()`로 속성이 있는지 확인하고, `getattr()`로 값을 가져옵니다.

예:

```python
passenger.passenger_id
```

를 직접 쓰는 대신,

```python
getattr(passenger, "passenger_id")
```

처럼 이름 문자열로 값을 가져오는 방식입니다.

### 승객 ID 읽기

```python
def _passenger_id(passenger: Any) -> Any:
    return _get_value(passenger, ("passenger_id", "pid", "id"), "")
```

승객 ID를 읽습니다.

`Passenger` 객체라면 `passenger.passenger_id`를 읽고, 딕셔너리라면 `passenger["passenger_id"]` 또는 `passenger["pid"]` 또는 `passenger["id"]`를 찾습니다.

### 승객 ID 정렬 키

```python
def _passenger_id_key(passenger: Any) -> tuple[int, Any]:
    raw_id = _passenger_id(passenger)
    if isinstance(raw_id, int):
        return (0, raw_id)
```

정렬에 사용할 승객 ID 키를 만듭니다.

반환 타입은 `tuple[int, Any]`입니다. 파이썬에서 튜플은 앞 요소부터 차례대로 비교됩니다.

예:

```python
(0, 2) < (0, 10)
(0, 10) < (1, "A")
```

```python
    text_id = str(raw_id)
    match = re.search(r"\d+", text_id)
    if match:
        return (0, int(match.group()))
    return (1, text_id)
```

ID가 `"P12"`처럼 문자열이면 정규표현식으로 숫자 부분을 찾습니다.

- `"P12"` -> `(0, 12)`
- `"A"` -> `(1, "A")`

이렇게 하면 `"P2"`가 `"P10"`보다 먼저 오도록 자연스럽게 정렬할 수 있습니다.

### 승객 속성 읽기 함수

```python
def _arrival_time(passenger: Any) -> int:
    return int(_get_value(passenger, ("arrival_time", "arrival", "arrived_at"), 0))
```

도착 시간을 정수로 읽습니다.

```python
def _passenger_class(passenger: Any) -> int:
    return int(
        _get_value(
            passenger,
            ("passenger_class", "class_type", "travel_class", "cls", "class"),
            ECONOMY,
        )
    )
```

승객 등급을 읽습니다. 값이 없으면 기본값으로 `ECONOMY`를 사용합니다.

```python
def _service_time(passenger: Any) -> int:
    return int(_get_value(passenger, ("service_time", "burst_time", "service", "burst"), 0))
```

서비스 시간을 읽습니다.

운영체제 스케줄링에서 `service_time`은 흔히 `burst_time`이라고도 부릅니다.

### 카운터 정보 읽기

```python
def _counter_id(counter: Any) -> str:
    raw_id = _get_value(counter, ("counter_id", "id", "cid"), "")
    return str(raw_id).upper()
```

카운터 ID를 문자열 대문자로 바꿉니다.

예:

```python
"c1" -> "C1"
```

```python
def _counter_type(counter: Any) -> str:
    raw_type = _get_value(counter, ("counter_type", "type", "kind"), "")
    return str(raw_type).upper()
```

카운터 타입도 대문자로 바꿉니다.

예:

```python
"First" -> "FIRST"
```

### `_counter_preferred_class()`

```python
def _counter_preferred_class(counter: Any) -> Optional[int]:
    """Return the counter's preferred class, if it is a dedicated counter."""
```

카운터가 특정 등급 전용인지 확인합니다.

반환값은 다음 중 하나입니다.

- `FIRST`
- `BUSINESS`
- `ECONOMY`
- `None`

`None`은 특정 등급 전용이 아니라는 뜻입니다. 이 프로젝트에서는 Flex 카운터가 여기에 해당합니다.

```python
    raw_preference = _get_value(
        counter,
        ("preferred_class", "dedicated_class", "assigned_class", "counter_class"),
        None,
    )
```

카운터 객체에 선호 등급 정보가 직접 들어 있다면 먼저 그것을 읽습니다.

```python
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
```

`try-except`는 에러가 날 수 있는 코드를 안전하게 실행하는 문법입니다.

예를 들어 `int("FIRST")`는 실패합니다. 이때 `except` 블록으로 이동해서 문자열에 `"FIRST"`가 들어 있는지 확인합니다.

```python
    counter_type = _counter_type(counter)
    if "FLEX" in counter_type:
        return None
    if "FIRST" in counter_type:
        return FIRST
    if "BUSINESS" in counter_type:
        return BUSINESS
    if "ECONOMY" in counter_type:
        return ECONOMY
```

카운터 타입 문자열로 전용 등급을 판단합니다.

```python
    counter_id = _counter_id(counter)
    if counter_id in {"1", "C1"}:
        return FIRST
    if counter_id in {"2", "C2"}:
        return BUSINESS
    if counter_id in {"3", "C3"}:
        return ECONOMY

    return None
```

마지막으로 카운터 ID를 기준으로 판단합니다.

이 프로젝트의 기본 카운터는 `models.py`에서 다음처럼 만들어집니다.

```python
C1: First 전용
C2: Business 전용
C3: Economy 전용
C4: Flex
C5: Flex
```

## SchedulerStrategy 추상 클래스

```python
class SchedulerStrategy(ABC):
    """Base interface for all non-preemptive scheduler strategies."""

    name = "SchedulerStrategy"
```

모든 스케줄러의 부모 클래스입니다.

`ABC`를 상속했기 때문에 추상 클래스로 동작합니다. 이 클래스 자체를 직접 사용하기보다, 자식 클래스가 공통 규칙을 따르도록 만드는 용도입니다.

```python
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
```

`@abstractmethod`가 붙은 메서드는 자식 클래스에서 반드시 구현해야 합니다.

이 메서드는 다음 정보를 받습니다.

| 인자 | 의미 |
| --- | --- |
| `ready_queue` | 현재 기다리는 승객 목록 |
| `counters` | 전체 카운터 목록 |
| `current_time` | 현재 시뮬레이션 시간 |
| `counter` | 지금 승객을 배정하려는 카운터 |

반환값은 다음 둘 중 하나입니다.

- 선택된 승객 1명
- 선택할 승객이 없으면 `None`

```python
    def select_next(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        """Compatibility alias for engines that call select_next()."""
        return self.select_next_passenger(ready_queue, counters, current_time, counter)
```

`select_next()`는 호환성을 위한 별칭 메서드입니다.

어떤 코드가 `select_next()`라는 이름으로 호출해도 내부적으로 `select_next_passenger()`를 실행합니다.

## 스케줄러별 선택 기준

### 1. BaselineA_FCFS

```python
class BaselineA_FCFS(SchedulerStrategy):
    """Baseline A: single ready queue, first-come first-served."""

    name = "Baseline A: FCFS"
```

FCFS는 `First-Come First-Served`의 약자입니다.

먼저 온 승객을 먼저 처리합니다.

```python
    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        if not ready_queue:
            return None
```

`if not ready_queue`는 리스트가 비어 있는지 확인하는 파이썬식 표현입니다.

빈 리스트는 `False`처럼 취급됩니다.

```python
        return min(ready_queue, key=lambda passenger: (_arrival_time(passenger), _passenger_id_key(passenger)))
```

`min()`은 가장 작은 값을 고릅니다.

여기서는 승객 객체 자체를 비교하지 않고, `key=`에 지정한 기준으로 비교합니다.

기준은 튜플입니다.

```python
(_arrival_time(passenger), _passenger_id_key(passenger))
```

파이썬 튜플 정렬은 앞에서부터 비교합니다.

1. 도착 시간이 빠른 승객
2. 도착 시간이 같으면 ID가 작은 승객

`lambda passenger: ...`는 이름 없는 짧은 함수입니다.

위 코드는 다음 함수와 비슷합니다.

```python
def sort_key(passenger):
    return (_arrival_time(passenger), _passenger_id_key(passenger))
```

### 2. BaselineB_Priority

```python
class BaselineB_Priority(SchedulerStrategy):
    """Baseline B: fixed class priority, then FCFS within the same class."""

    name = "Baseline B: Priority"
```

Priority 스케줄러는 승객 등급을 가장 먼저 봅니다.

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

선택 기준은 다음 순서입니다.

1. 승객 등급이 높은 사람
2. 같은 등급이면 먼저 도착한 사람
3. 도착 시간도 같으면 ID가 작은 사람

여기서 등급 숫자는 다음과 같습니다.

```python
FIRST = 1
BUSINESS = 2
ECONOMY = 3
```

`min()`은 작은 값을 고르므로 `1`인 First가 가장 먼저 선택됩니다.

### 3. BaselineC_SJF

```python
class BaselineC_SJF(SchedulerStrategy):
    """Baseline C: non-preemptive shortest-job-first."""

    name = "Baseline C: Non-preemptive SJF"
```

SJF는 `Shortest Job First`의 약자입니다.

서비스 시간이 가장 짧은 승객을 먼저 처리합니다.

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

선택 기준은 다음 순서입니다.

1. 서비스 시간이 짧은 승객
2. 서비스 시간이 같으면 먼저 도착한 승객
3. 도착 시간도 같으면 ID가 작은 승객

주의할 점은 이 스케줄러가 **비선점형(non-preemptive)** 이라는 점입니다.

한번 승객이 카운터에서 서비스를 시작하면, 중간에 더 짧은 서비스 시간의 승객이 와도 기존 승객을 멈추지 않습니다.

### 4. OurScheduler

```python
class OurScheduler(SchedulerStrategy):
    """
    Hybrid Multi-Level Queue scheduler.
```

`OurScheduler`는 여러 아이디어를 섞은 스케줄러입니다.

- Multi-Level Queue: 승객 등급별 큐 개념 사용
- Priority Weight: First, Business에 가중치 부여
- HRRN/Aging: 오래 기다릴수록 점수가 올라감
- SJF tie-break: 점수가 같으면 서비스 시간이 짧은 승객 우선
- FCFS tie-break: 그다음은 먼저 도착한 승객 우선

#### 초기화

```python
    def __init__(
        self,
        class_weights: dict[int, float] | None = None,
        allow_dedicated_counter_borrowing: bool = True,
    ) -> None:
        self.class_weights = dict(CLASS_WEIGHTS if class_weights is None else class_weights)
        self.allow_dedicated_counter_borrowing = allow_dedicated_counter_borrowing
```

`__init__()`은 객체가 만들어질 때 자동으로 실행되는 초기화 메서드입니다.

`class_weights`를 따로 전달하지 않으면 기본값 `CLASS_WEIGHTS`를 사용합니다.

`dict(...)`는 딕셔너리를 복사해서 저장합니다. 원본 딕셔너리를 직접 수정하지 않기 위한 처리입니다.

`allow_dedicated_counter_borrowing`은 전용 카운터가 자기 등급 승객을 찾지 못했을 때 다른 등급 승객을 처리해도 되는지 나타냅니다.

기본값은 `True`입니다.

#### 전체 선택 흐름

```python
    def select_next_passenger(
        self,
        ready_queue: list[Any],
        counters: list[Any],
        current_time: int,
        counter: Any,
    ) -> Any | None:
        if not ready_queue:
            return None
```

대기열이 비어 있으면 선택할 승객이 없으므로 `None`을 반환합니다.

```python
        class_queues = self._build_class_queues(ready_queue)
        candidate_pool = self._candidate_pool_for_counter(class_queues, ready_queue, counter)
        if not candidate_pool:
            return None
```

먼저 승객을 등급별로 나눕니다.

그다음 현재 카운터가 처리할 수 있는 후보 승객 목록을 만듭니다.

예를 들어 `C1`이 First 전용이라면 First 승객을 우선 후보로 봅니다.

```python
        return max(candidate_pool, key=lambda passenger: self._selection_key(passenger, current_time))
```

`OurScheduler`는 `max()`를 씁니다.

FCFS, Priority, SJF는 작은 기준값이 좋기 때문에 `min()`을 썼습니다. 하지만 `OurScheduler`는 점수가 높을수록 좋기 때문에 `max()`를 씁니다.

#### 등급별 큐 만들기

```python
    def _build_class_queues(self, ready_queue: list[Any]) -> dict[int, list[Any]]:
        class_queues: dict[int, list[Any]] = defaultdict(list)
        for passenger in ready_queue:
            class_queues[_passenger_class(passenger)].append(passenger)
        return class_queues
```

`ready_queue`를 승객 등급별로 나눕니다.

예:

```python
{
    1: [First 승객들],
    2: [Business 승객들],
    3: [Economy 승객들],
}
```

`for passenger in ready_queue:`는 리스트의 승객을 하나씩 꺼내 반복합니다.

#### 카운터별 후보군 만들기

```python
    def _candidate_pool_for_counter(
        self,
        class_queues: dict[int, list[Any]],
        ready_queue: list[Any],
        counter: Any,
    ) -> list[Any]:
        preferred_class = _counter_preferred_class(counter)
```

현재 카운터가 선호하는 승객 등급을 찾습니다.

```python
        if preferred_class is None:
            return list(ready_queue)
```

Flex 카운터라면 특정 등급 제한이 없으므로 전체 대기열을 후보로 사용합니다.

```python
        preferred_queue = class_queues.get(preferred_class, [])
        if preferred_queue:
            return list(preferred_queue)
```

전용 카운터라면 자기 등급 승객을 먼저 후보로 봅니다.

예:

- `C1`: First 승객
- `C2`: Business 승객
- `C3`: Economy 승객

```python
        if self.allow_dedicated_counter_borrowing:
            return list(ready_queue)

        return []
```

자기 등급 승객이 없고 `allow_dedicated_counter_borrowing`이 `True`라면 다른 등급 승객도 처리합니다.

이렇게 하면 전용 카운터가 놀고 있는 시간을 줄일 수 있습니다.

#### 점수 계산

```python
    def _selection_key(self, passenger: Any, current_time: int) -> tuple[float, int, int, tuple[int, Any]]:
        waiting_time = max(0, current_time - _arrival_time(passenger))
        service_time = max(1, _service_time(passenger))
        passenger_class = _passenger_class(passenger)
        class_weight = self.class_weights.get(passenger_class, 1.0)
```

여기서 `max()`는 더 큰 값을 고르는 함수입니다.

```python
waiting_time = max(0, current_time - arrival_time)
```

대기 시간이 음수가 되지 않게 최소값을 0으로 제한합니다.

```python
service_time = max(1, _service_time(passenger))
```

서비스 시간이 0이면 나눗셈 문제가 생길 수 있으므로 최소 1로 제한합니다.

```python
class_weight = self.class_weights.get(passenger_class, 1.0)
```

딕셔너리의 `.get(key, default)`는 키가 있으면 값을 반환하고, 없으면 기본값을 반환합니다.

```python
        response_ratio = (waiting_time + service_time) / service_time
        weighted_hrrn_score = response_ratio * class_weight
```

HRRN 점수는 다음 공식입니다.

```text
response_ratio = (waiting_time + service_time) / service_time
```

대기 시간이 길수록 점수가 올라갑니다.

`OurScheduler`는 여기에 등급 가중치를 곱합니다.

```text
weighted_hrrn_score = response_ratio * class_weight
```

예를 들어 같은 조건이면 First 승객은 `1.5`를 곱하므로 Economy보다 높은 점수를 받습니다.

```python
        return (
            weighted_hrrn_score,
            -service_time,
            -_arrival_time(passenger),
            _reverse_id_key(passenger),
        )
```

`max()`는 튜플의 앞 요소부터 비교해서 가장 큰 값을 고릅니다.

선택 기준은 다음 순서입니다.

1. `weighted_hrrn_score`가 큰 승객
2. 점수가 같으면 `-service_time`이 큰 승객
3. 그래도 같으면 `-_arrival_time`이 큰 승객
4. 그래도 같으면 `_reverse_id_key()`가 큰 승객

왜 `-service_time`을 쓸까요?

`max()`는 큰 값을 고르기 때문에, 서비스 시간이 짧은 승객을 우선하려면 음수로 바꿔야 합니다.

예:

```python
service_time = 3  -> -3
service_time = 10 -> -10
```

`-3`이 `-10`보다 크므로 서비스 시간이 3인 승객이 먼저 선택됩니다.

도착 시간도 마찬가지입니다.

```python
arrival_time = 0 -> 0
arrival_time = 5 -> -5
```

`0`이 `-5`보다 크므로 먼저 도착한 승객이 선택됩니다.

### 역방향 ID 키

```python
def _reverse_id_key(passenger: Any) -> tuple[int, Any]:
    order, value = _passenger_id_key(passenger)
    if isinstance(value, int):
        return (-order, -value)
    return (-order, _reverse_text(value))
```

`OurScheduler`는 `max()`를 쓰기 때문에 ID가 작은 승객을 고르려면 ID도 반대로 바꿔야 합니다.

예:

```python
ID 2  -> -2
ID 10 -> -10
```

`-2`가 더 크므로 ID 2가 먼저 선택됩니다.

```python
def _reverse_text(value: Any) -> tuple[int, ...]:
    return tuple(-ord(char) for char in str(value))
```

문자열 ID도 반대로 정렬하기 위한 함수입니다.

`ord(char)`는 문자를 숫자 코드로 바꿉니다.

`tuple(... for ... in ...)`는 generator expression으로 만든 값을 튜플로 바꾸는 문법입니다.

## 실행 명령어 처리 흐름

`strategies.py` 자체는 명령어를 처리하지 않습니다.

명령어 실행은 `scheduler.py`가 담당합니다.

예:

```powershell
python scheduler.py input.txt --scheduler all
```

이 명령을 실행하면 흐름은 다음과 같습니다.

```text
scheduler.py
  -> main()
  -> run_scheduler(passengers, scheduler_name)
  -> create_scheduler(scheduler_name)
  -> strategies.py의 스케줄러 객체 생성
  -> SimulationEngine.run(scheduler)
  -> scheduler.select_next_passenger(...)
```

즉 `strategies.py`는 실행 흐름 중간에서 `SimulationEngine`이 요청할 때마다 승객 1명을 골라 주는 역할입니다.

## 스케줄러 비교표

| 항목 | FCFS | Priority | SJF | OurScheduler |
| --- | --- | --- | --- | --- |
| 가장 먼저 보는 기준 | 도착 시간 | 승객 등급 | 서비스 시간 | HRRN 점수와 등급 가중치 |
| 동점 처리 | ID | 도착 시간, ID | 도착 시간, ID | 서비스 시간, 도착 시간, ID |
| 카운터 종류 반영 | 안 함 | 안 함 | 안 함 | 반영함 |
| 오래 기다린 승객 보정 | 없음 | 없음 | 없음 | 있음 |
| 짧은 작업 우대 | 없음 | 없음 | 있음 | 동점 처리에서 있음 |
| 고등급 승객 우대 | 없음 | 강함 | 없음 | 가중치로 반영 |
| 장점 | 단순하고 공정해 보임 | First/Business 우선 처리 | 평균 대기 시간 감소 가능 | 여러 요소를 균형 있게 반영 |
| 단점 | 짧은 작업도 오래 기다릴 수 있음 | Economy가 밀릴 수 있음 | 긴 작업이 밀릴 수 있음 | 계산 기준이 상대적으로 복잡함 |

## 다른 파일과의 관계

### `scheduler.py`

`scheduler.py`는 사용자 명령을 해석하고 어떤 스케줄러를 실행할지 결정합니다.

```python
def create_scheduler(name: str) -> SchedulerStrategy:
    if name == "fcfs":
        return BaselineA_FCFS()
```

여기서 `strategies.py`의 클래스를 생성합니다.

### `simulation.py`

`simulation.py`의 `SimulationEngine`은 실제 시간 흐름을 진행합니다.

카운터가 비어 있고 대기 승객이 있으면 다음처럼 스케줄러를 호출합니다.

```python
selected = scheduler.select_next_passenger(
    ready_queue=list(self.ready_queue),
    counters=self.counters,
    current_time=self.current_time,
    counter=counter,
)
```

이때 `strategies.py`의 알고리즘이 선택됩니다.

### `models.py`

`models.py`는 `Passenger`, `Counter`, `SimulationResult` 같은 데이터 구조를 정의합니다.

`strategies.py`는 이 객체들의 값을 직접 사용합니다.

예:

- `Passenger.arrival_time`
- `Passenger.passenger_class`
- `Passenger.service_time`
- `Counter.counter_type`

### `report_utils.py`

`strategies.py`와 직접 연결되지는 않습니다.

하지만 `scheduler.py`가 각 스케줄러의 실행 결과를 모아서 `report_utils.py`의 `write_att_comparison_png()`로 그래프를 만듭니다.

즉 전체 흐름에서는 다음처럼 연결됩니다.

```text
strategies.py에서 승객 선택
  -> simulation.py가 결과 생성
  -> scheduler.py가 결과 수집
  -> report_utils.py가 비교 그래프 생성
```

## 별칭(alias)

```python
FCFSStrategy = BaselineA_FCFS
PriorityStrategy = BaselineB_Priority
SJFStrategy = BaselineC_SJF
BaselineAFCFS = BaselineA_FCFS
BaselineBPriority = BaselineB_Priority
BaselineCSJF = BaselineC_SJF
```

같은 클래스를 다른 이름으로도 사용할 수 있게 만든 코드입니다.

예를 들어 아래 두 코드는 같은 클래스 객체를 가리킵니다.

```python
BaselineA_FCFS
FCFSStrategy
```

이런 별칭은 테스트 코드나 이전 버전 코드에서 다른 이름을 사용할 때 호환성을 유지하는 데 도움이 됩니다.
