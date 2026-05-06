# models.py 설명

## 파일의 역할

`models.py`는 이 프로젝트에서 사용하는 핵심 데이터 구조를 모아 둔 파일입니다.

공항 체크인 시뮬레이션에는 크게 세 가지 정보가 필요합니다.

- 승객 정보: 언제 도착했는지, 등급이 무엇인지, 서비스 시간이 얼마나 걸리는지
- 카운터 정보: 어떤 카운터가 어떤 승객을 처리 중인지, 언제까지 바쁜지
- 시뮬레이션 결과: 모든 승객과 카운터의 최종 상태, 로그, 종료 시간

이 파일은 위 정보를 `Passenger`, `Counter`, `SimulationResult`라는 클래스로 표현합니다. `simulation.py`는 이 클래스들을 사용해서 실제 시뮬레이션을 진행하고, `scheduler.py`는 결과를 CSV 파일로 저장할 때 이 클래스들의 값을 읽습니다.

## 전체 구조

`models.py`는 다음 순서로 구성됩니다.

| 구간 | 역할 |
| --- | --- |
| import 구문 | `dataclass`, 타입 힌트 도구를 가져옴 |
| 승객 등급 상수 | First, Business, Economy 등급을 숫자로 정의 |
| 카운터 종류 상수 | First, Business, Economy, Flex 카운터 이름을 정의 |
| `passenger_id_sort_key()` | 승객 ID를 안정적으로 정렬하기 위한 보조 함수 |
| `Passenger` 클래스 | 승객 한 명의 입력 정보와 실행 중 상태를 저장 |
| `Counter` 클래스 | 카운터 한 개의 상태와 처리 기록을 저장 |
| `SimulationResult` 클래스 | 시뮬레이션이 끝난 뒤 결과를 묶어서 저장 |
| `create_default_counters()` | 기본 카운터 5개를 생성 |

## 코드 설명

### import 구문

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
```

- `from __future__ import annotations`
  - 타입 힌트를 조금 더 유연하게 쓰게 해 주는 설정입니다.
  - 예를 들어 클래스 안에서 `list[Passenger]`처럼 아직 완전히 만들어지는 중인 타입 이름을 더 안전하게 사용할 수 있습니다.
  - 프로그램 실행 로직 자체를 바꾸는 코드는 아닙니다.

- `from dataclasses import dataclass, field`
  - `dataclass`는 데이터를 담는 클래스를 쉽게 만들게 해 주는 기능입니다.
  - 일반 클래스를 만들면 `__init__()` 같은 생성자를 직접 작성해야 하지만, `@dataclass`를 붙이면 Python이 자동으로 만들어 줍니다.
  - `field`는 dataclass 필드에 특별한 설정을 줄 때 사용합니다. 이 파일에서는 빈 리스트를 안전하게 만들기 위해 `field(default_factory=list)` 형태로 사용합니다.

- `from typing import Any, Optional`
  - 타입 힌트를 위해 가져옵니다.
  - `Any`는 "아무 타입이나 가능하다"는 뜻입니다.
  - `Optional[int]`는 "정수이거나 `None`일 수 있다"는 뜻입니다.

### 승객 등급 상수

```python
FIRST = 1
BUSINESS = 2
ECONOMY = 3

CLASS_NAMES = {
    FIRST: "First",
    BUSINESS: "Business",
    ECONOMY: "Economy",
}
```

- `FIRST = 1`
  - First Class 승객을 숫자 `1`로 표현합니다.

- `BUSINESS = 2`
  - Business Class 승객을 숫자 `2`로 표현합니다.

- `ECONOMY = 3`
  - Economy Class 승객을 숫자 `3`으로 표현합니다.

- `CLASS_NAMES = {...}`
  - `dict`, 즉 딕셔너리입니다.
  - 딕셔너리는 `키: 값` 형태로 데이터를 저장합니다.
  - 여기서는 숫자 등급을 사람이 읽기 쉬운 문자열로 바꾸기 위해 사용합니다.
  - 예를 들어 `CLASS_NAMES[1]`은 `"First"`입니다.

Python 문법으로 보면 다음과 같습니다.

```python
{
    FIRST: "First",
}
```

이 코드는 실제로는 다음과 비슷합니다.

```python
{
    1: "First",
}
```

`FIRST`라는 변수 안에 `1`이 들어 있기 때문입니다.

### 카운터 종류 상수

```python
COUNTER_FIRST = "First"
COUNTER_BUSINESS = "Business"
COUNTER_ECONOMY = "Economy"
COUNTER_FLEX = "Flex"
```

- 각 카운터의 종류를 문자열로 정의합니다.
- `"First"` 카운터는 First 승객을 우선 처리하는 전용 카운터입니다.
- `"Business"` 카운터는 Business 승객을 우선 처리합니다.
- `"Economy"` 카운터는 Economy 승객을 우선 처리합니다.
- `"Flex"` 카운터는 특정 등급에 고정되지 않은 유연한 카운터입니다.

상수를 쓰는 이유는 오타를 줄이기 위해서입니다. 코드 여러 곳에서 직접 `"Business"`를 반복해서 쓰면, 한 곳에서 `"Busines"`처럼 잘못 적어도 Python이 바로 알아차리기 어렵습니다. 상수로 모아 두면 같은 값을 일관되게 사용할 수 있습니다.

### `passenger_id_sort_key()` 함수

```python
def passenger_id_sort_key(passenger_id: Any) -> tuple[int, Any]:
    """Return a stable sort key for numeric ids and ids such as P01."""
    text = str(passenger_id)
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return (0, int(digits))
    return (1, text)
```

이 함수는 승객 ID를 정렬하기 쉽게 바꿔 주는 함수입니다. 승객 ID가 `1`, `2`, `10`처럼 숫자일 수도 있고, `"P01"`, `"P10"`처럼 문자와 숫자가 섞여 있을 수도 있기 때문에 별도 함수가 필요합니다.

- `def passenger_id_sort_key(...)`
  - `def`는 함수를 정의할 때 사용하는 키워드입니다.
  - `passenger_id_sort_key`는 함수 이름입니다.

- `passenger_id: Any`
  - `passenger_id`라는 매개변수를 받습니다.
  - `Any`는 숫자, 문자열 등 어떤 타입이든 들어올 수 있다는 뜻입니다.

- `-> tuple[int, Any]`
  - 이 함수가 반환하는 값의 타입 힌트입니다.
  - `tuple[int, Any]`는 `(정수, 어떤 값)` 형태의 튜플을 반환한다는 뜻입니다.
  - 튜플은 리스트와 비슷하지만 보통 한 번 만든 뒤 바꾸지 않는 묶음 값으로 사용합니다.

- `text = str(passenger_id)`
  - 승객 ID를 문자열로 바꿉니다.
  - `1`이 들어와도 `"1"`로 만들고, `"P01"`이 들어와도 그대로 문자열로 다룹니다.

- `digits = "".join(ch for ch in text if ch.isdigit())`
  - `text` 안에서 숫자인 문자만 뽑아서 이어 붙입니다.
  - `for ch in text`는 문자열의 글자를 하나씩 꺼냅니다.
  - `if ch.isdigit()`은 그 글자가 숫자인지 확인합니다.
  - `"".join(...)`은 뽑힌 글자들을 빈 문자열 기준으로 이어 붙입니다.
  - 예를 들어 `"P01"`은 `"01"`이 됩니다.

- `if digits:`
  - `digits`가 빈 문자열이 아니면 실행됩니다.
  - Python에서는 빈 문자열 `""`은 거짓처럼 취급되고, `"01"` 같은 문자열은 참처럼 취급됩니다.

- `return (0, int(digits))`
  - 숫자가 있으면 `(0, 숫자)` 형태로 반환합니다.
  - `"P01"`은 `(0, 1)`이 됩니다.
  - 정렬할 때 튜플의 첫 번째 값부터 비교하므로, 첫 번째 값 `0`은 "숫자 ID 그룹"이라는 표시처럼 쓰입니다.

- `return (1, text)`
  - 숫자가 하나도 없으면 `(1, 원래 문자열)` 형태로 반환합니다.
  - 첫 번째 값이 `1`이므로 숫자가 있는 ID보다 뒤쪽에 정렬됩니다.

예시는 다음과 같습니다.

```python
passenger_id_sort_key(10)      # (0, 10)
passenger_id_sort_key("P01")   # (0, 1)
passenger_id_sort_key("ABC")   # (1, "ABC")
```

## `Passenger` 클래스

### 클래스 선언과 필드

```python
@dataclass
class Passenger:
    passenger_id: Any
    arrival_time: int
    passenger_class: int
    service_time: int
    service_start_time: Optional[int] = None
    completion_time: Optional[int] = None
    turnaround_time: Optional[int] = None
    assigned_counter_id: Optional[str] = None
```

`Passenger`는 승객 한 명을 나타내는 클래스입니다.

- `@dataclass`
  - 바로 아래에 있는 `class Passenger`에 적용됩니다.
  - `Passenger(...)`처럼 객체를 만들 수 있도록 생성자를 자동으로 만들어 줍니다.

- `class Passenger:`
  - `Passenger`라는 클래스를 정의합니다.
  - 클래스는 관련 있는 데이터와 기능을 하나로 묶는 틀입니다.

- `passenger_id: Any`
  - 승객 번호입니다.
  - 숫자일 수도 있고 문자열일 수도 있어서 `Any`를 사용합니다.

- `arrival_time: int`
  - 승객이 공항 체크인 대기열에 도착한 시간입니다.

- `passenger_class: int`
  - 승객 등급입니다.
  - 이 프로젝트에서는 `1`은 First, `2`는 Business, `3`은 Economy입니다.

- `service_time: int`
  - 체크인 서비스에 걸리는 시간입니다.

- `service_start_time: Optional[int] = None`
  - 서비스가 시작된 시간입니다.
  - 처음에는 아직 시작하지 않았으므로 `None`입니다.

- `completion_time: Optional[int] = None`
  - 서비스가 끝난 시간입니다.
  - 처음에는 아직 끝나지 않았으므로 `None`입니다.

- `turnaround_time: Optional[int] = None`
  - 도착부터 완료까지 걸린 전체 시간입니다.
  - 계산식은 `completion_time - arrival_time`입니다.

- `assigned_counter_id: Optional[str] = None`
  - 어느 카운터에서 처리되었는지 저장합니다.
  - 예를 들어 `"C1"` 같은 값이 들어갑니다.

필드 중 앞의 네 개는 입력 데이터입니다.

```python
passenger_id
arrival_time
passenger_class
service_time
```

뒤의 네 개는 시뮬레이션이 진행되면서 채워지는 실행 상태입니다.

```python
service_start_time
completion_time
turnaround_time
assigned_counter_id
```

### `class_name` 속성

```python
@property
def class_name(self) -> str:
    return CLASS_NAMES.get(self.passenger_class, str(self.passenger_class))
```

- `@property`
  - 메서드를 변수처럼 읽을 수 있게 해 줍니다.
  - `passenger.class_name()`이 아니라 `passenger.class_name`처럼 사용합니다.

- `def class_name(self) -> str:`
  - `class_name`이라는 메서드를 정의합니다.
  - `self`는 현재 객체 자신을 뜻합니다.
  - 예를 들어 `p = Passenger(...)`라면, 메서드 안의 `self`는 `p`입니다.

- `return CLASS_NAMES.get(...)`
  - `return`은 함수나 메서드의 결과를 돌려주는 키워드입니다.
  - `CLASS_NAMES.get(key, default)`는 딕셔너리에서 `key`를 찾고, 없으면 `default`를 반환합니다.
  - `self.passenger_class`가 `1`이면 `"First"`를 반환합니다.
  - 알 수 없는 등급이면 숫자를 문자열로 바꿔 반환합니다.

### `has_started` 속성

```python
@property
def has_started(self) -> bool:
    return self.service_start_time is not None
```

- 서비스가 이미 시작되었는지 알려 줍니다.
- `bool`은 `True` 또는 `False` 값을 뜻합니다.
- `is not None`은 값이 `None`이 아닌지 확인합니다.
- `service_start_time`이 아직 `None`이면 `False`, 시간이 들어 있으면 `True`입니다.

### `is_completed` 속성

```python
@property
def is_completed(self) -> bool:
    return self.completion_time is not None
```

- 서비스가 끝났는지 알려 줍니다.
- 완료 시간이 있으면 완료된 승객입니다.

### `sort_key()` 메서드

```python
def sort_key(self) -> tuple[int, tuple[int, Any]]:
    return (self.arrival_time, passenger_id_sort_key(self.passenger_id))
```

이 메서드는 승객을 정렬할 때 사용할 기준을 반환합니다.

- 첫 번째 기준은 `arrival_time`입니다.
- 두 번째 기준은 `passenger_id_sort_key(self.passenger_id)`입니다.

즉, 먼저 도착 시간이 빠른 승객이 앞에 오고, 도착 시간이 같으면 승객 ID가 작은 쪽이 앞에 옵니다.

`simulation.py`에서는 다음처럼 사용합니다.

```python
sorted(passengers, key=lambda passenger: passenger.sort_key())
```

여기서 `lambda passenger: passenger.sort_key()`는 "각 승객을 정렬할 때 `sort_key()` 결과를 기준으로 삼아라"라는 뜻입니다.

### `reset_runtime_state()` 메서드

```python
def reset_runtime_state(self) -> None:
    self.service_start_time = None
    self.completion_time = None
    self.turnaround_time = None
    self.assigned_counter_id = None
```

이 메서드는 승객의 실행 중 상태를 초기화합니다.

- `-> None`
  - 이 메서드는 특별한 결과값을 반환하지 않는다는 뜻입니다.

- `self.service_start_time = None`
  - 서비스 시작 시간을 지웁니다.

- `self.completion_time = None`
  - 완료 시간을 지웁니다.

- `self.turnaround_time = None`
  - 반환 시간을 지웁니다.

- `self.assigned_counter_id = None`
  - 배정된 카운터 정보를 지웁니다.

왜 필요할까요? 같은 승객 목록으로 여러 스케줄러를 비교할 수 있기 때문입니다. 이전 실행에서 남은 시작 시간이나 완료 시간이 있으면 다음 시뮬레이션 결과가 섞일 수 있으므로, 실행 전 초기화합니다.

### `start_service()` 메서드

```python
def start_service(self, current_time: int, counter_id: str) -> None:
    if self.has_started:
        raise ValueError(f"Passenger {self.passenger_id} has already started service.")

    self.service_start_time = current_time
    self.assigned_counter_id = counter_id
```

이 메서드는 승객이 카운터에서 서비스를 시작할 때 호출됩니다.

- `current_time: int`
  - 현재 시뮬레이션 시간입니다.

- `counter_id: str`
  - 승객이 배정된 카운터 ID입니다.

- `if self.has_started:`
  - 이미 시작된 승객인지 확인합니다.
  - `if`는 조건이 참일 때만 아래 코드를 실행합니다.

- `raise ValueError(...)`
  - 잘못된 상황이면 에러를 발생시킵니다.
  - 이미 서비스를 시작한 승객을 다시 시작시키면 시뮬레이션 결과가 이상해지므로 막습니다.

- `f"Passenger {self.passenger_id} ..."`
  - f-string입니다.
  - 문자열 안에 `{변수}`를 넣으면 변수 값이 문자열에 들어갑니다.

- `self.service_start_time = current_time`
  - 서비스 시작 시간을 현재 시간으로 저장합니다.

- `self.assigned_counter_id = counter_id`
  - 어떤 카운터에서 처리되는지 저장합니다.

### `complete_service()` 메서드

```python
def complete_service(self, completion_time: int) -> None:
    if self.service_start_time is None:
        raise ValueError(f"Passenger {self.passenger_id} cannot complete before service starts.")

    expected_completion = self.service_start_time + self.service_time
    if completion_time != expected_completion:
        raise ValueError(
            f"Passenger {self.passenger_id} completion_time={completion_time} "
            f"does not match start + service_time={expected_completion}."
        )

    self.completion_time = completion_time
    self.turnaround_time = self.completion_time - self.arrival_time
```

이 메서드는 승객의 서비스 완료 처리를 합니다.

- `if self.service_start_time is None:`
  - 서비스 시작 시간이 없으면 아직 시작하지 않은 승객입니다.
  - 시작하지 않은 승객을 완료할 수 없으므로 에러를 냅니다.

- `expected_completion = self.service_start_time + self.service_time`
  - 예상 완료 시간을 계산합니다.
  - 예를 들어 시작 시간이 `5`, 서비스 시간이 `10`이면 완료 시간은 `15`입니다.

- `if completion_time != expected_completion:`
  - 전달받은 완료 시간이 예상 완료 시간과 다르면 잘못된 상태입니다.
  - `!=`는 "같지 않다"는 비교 연산자입니다.

- `raise ValueError(...)`
  - 시뮬레이션 시간 계산이 틀렸다는 의미로 에러를 발생시킵니다.

- `self.completion_time = completion_time`
  - 완료 시간을 저장합니다.

- `self.turnaround_time = self.completion_time - self.arrival_time`
  - 도착부터 완료까지 걸린 시간을 계산합니다.
  - 이 프로젝트에서 ATT, 즉 평균 Turnaround Time을 계산할 때 이 값이 사용됩니다.

### `to_result_dict()` 메서드

```python
def to_result_dict(self) -> dict[str, Any]:
    return {
        "passenger_id": self.passenger_id,
        "passenger_class": self.passenger_class,
        "arrival_time": self.arrival_time,
        "service_time": self.service_time,
        "service_start_time": self.service_start_time,
        "completion_time": self.completion_time,
        "turnaround_time": self.turnaround_time,
        "assigned_counter_id": self.assigned_counter_id,
    }
```

이 메서드는 승객 정보를 딕셔너리로 바꿉니다.

- `dict[str, Any]`
  - 키는 문자열이고, 값은 여러 타입이 될 수 있는 딕셔너리라는 뜻입니다.

- `return { ... }`
  - 여러 값을 묶은 딕셔너리를 반환합니다.

이 메서드는 `scheduler.py`에서 CSV 파일을 만들 때 사용됩니다.

```python
row = passenger.to_result_dict()
```

객체의 속성을 CSV 한 줄로 쓰기 쉬운 형태로 바꾸는 역할입니다.

## `Counter` 클래스

### 클래스 선언과 필드

```python
@dataclass
class Counter:
    counter_id: str
    counter_type: str
    current_passenger: Optional[Passenger] = None
    busy_until: int = 0
    processed_passengers: list[Passenger] = field(default_factory=list)
    total_service_time: int = 0
    idle_time: int = 0
```

`Counter`는 체크인 카운터 한 개를 나타내는 클래스입니다.

- `counter_id: str`
  - 카운터 ID입니다. 예를 들어 `"C1"`입니다.

- `counter_type: str`
  - 카운터 종류입니다. `"First"`, `"Business"`, `"Economy"`, `"Flex"` 중 하나입니다.

- `current_passenger: Optional[Passenger] = None`
  - 현재 처리 중인 승객입니다.
  - 아무도 처리하지 않으면 `None`입니다.

- `busy_until: int = 0`
  - 이 카운터가 언제까지 바쁜지 나타냅니다.
  - 예를 들어 현재 시간 `3`에 서비스 시간 `7`인 승객을 받으면 `busy_until`은 `10`입니다.

- `processed_passengers: list[Passenger] = field(default_factory=list)`
  - 이 카운터가 처리 완료한 승객 목록입니다.
  - `list[Passenger]`는 `Passenger` 객체들이 들어 있는 리스트라는 뜻입니다.
  - `field(default_factory=list)`는 새 `Counter` 객체마다 독립적인 빈 리스트를 만들어 줍니다.

- `total_service_time: int = 0`
  - 이 카운터가 실제로 승객을 처리하는 데 쓴 총 시간입니다.

- `idle_time: int = 0`
  - 이 카운터가 놀고 있던 시간입니다.

`field(default_factory=list)`가 중요한 이유는 리스트가 바뀔 수 있는 값이기 때문입니다. 여러 `Counter`가 같은 리스트를 공유하면 한 카운터의 처리 승객이 다른 카운터에도 들어가는 이상한 문제가 생길 수 있습니다. `default_factory=list`는 객체마다 새 리스트를 만들어서 그 문제를 막습니다.

### `is_idle` 속성

```python
@property
def is_idle(self) -> bool:
    return self.current_passenger is None
```

- 카운터가 비어 있는지 알려 줍니다.
- `current_passenger`가 `None`이면 현재 처리 중인 승객이 없다는 뜻입니다.

사용 예시는 다음과 같습니다.

```python
if counter.is_idle:
    ...
```

`counter.is_idle`이 `True`일 때만 아래 코드가 실행됩니다.

### `preferred_passenger_class` 속성

```python
@property
def preferred_passenger_class(self) -> Optional[int]:
    if self.counter_type == COUNTER_FIRST:
        return FIRST
    if self.counter_type == COUNTER_BUSINESS:
        return BUSINESS
    if self.counter_type == COUNTER_ECONOMY:
        return ECONOMY
    return None
```

이 속성은 카운터가 선호하는 승객 등급을 반환합니다.

- `if self.counter_type == COUNTER_FIRST:`
  - 카운터 종류가 `"First"`이면 First 등급을 반환합니다.

- `return FIRST`
  - `FIRST`는 숫자 `1`입니다.

- `return None`
  - `"Flex"` 카운터처럼 특정 등급에 고정되지 않은 경우 `None`을 반환합니다.

이 속성은 현재 `simulation.py`에서 직접 쓰지는 않지만, 스케줄러나 다른 로직이 카운터의 선호 등급을 알고 싶을 때 사용할 수 있습니다.

### `reset_runtime_state()` 메서드

```python
def reset_runtime_state(self) -> None:
    self.current_passenger = None
    self.busy_until = 0
    self.processed_passengers.clear()
    self.total_service_time = 0
    self.idle_time = 0
```

카운터의 실행 중 상태를 초기화합니다.

- `self.current_passenger = None`
  - 현재 처리 중인 승객을 비웁니다.

- `self.busy_until = 0`
  - 바쁜 종료 시간을 초기값으로 되돌립니다.

- `self.processed_passengers.clear()`
  - 처리 완료 승객 리스트를 비웁니다.
  - `clear()`는 리스트 안의 내용을 모두 삭제합니다.

- `self.total_service_time = 0`
  - 총 서비스 시간을 초기화합니다.

- `self.idle_time = 0`
  - 유휴 시간을 초기화합니다.

### `assign_passenger()` 메서드

```python
def assign_passenger(self, passenger: Passenger, current_time: int) -> None:
    if not self.is_idle:
        active_id = self.current_passenger.passenger_id if self.current_passenger else None
        raise RuntimeError(
            f"Counter {self.counter_id} is busy with passenger {active_id} until {self.busy_until}."
        )

    passenger.start_service(current_time=current_time, counter_id=self.counter_id)
    self.current_passenger = passenger
    self.busy_until = current_time + passenger.service_time
    self.total_service_time += passenger.service_time
```

이 메서드는 비어 있는 카운터에 승객을 배정합니다.

- `if not self.is_idle:`
  - 카운터가 비어 있지 않으면 아래 에러 처리를 합니다.
  - `not`은 참과 거짓을 뒤집습니다.

- `active_id = self.current_passenger.passenger_id if self.current_passenger else None`
  - 조건 표현식입니다.
  - 현재 승객이 있으면 그 승객 ID를 넣고, 없으면 `None`을 넣습니다.
  - 일반 `if`문을 한 줄로 쓴 형태입니다.

- `raise RuntimeError(...)`
  - 이미 바쁜 카운터에 새 승객을 넣으려는 실행 오류를 막습니다.

- `passenger.start_service(...)`
  - 승객 객체의 서비스 시작 상태를 기록합니다.
  - 이때 승객의 `service_start_time`과 `assigned_counter_id`가 채워집니다.

- `self.current_passenger = passenger`
  - 이 카운터가 현재 처리 중인 승객을 저장합니다.

- `self.busy_until = current_time + passenger.service_time`
  - 카운터가 언제 다시 비게 되는지 계산합니다.

- `self.total_service_time += passenger.service_time`
  - `+=`는 기존 값에 더해서 다시 저장한다는 뜻입니다.
  - `self.total_service_time = self.total_service_time + passenger.service_time`과 같습니다.

### `complete_current_passenger()` 메서드

```python
def complete_current_passenger(self, current_time: int) -> Optional[Passenger]:
    if self.current_passenger is None or self.busy_until > current_time:
        return None

    passenger = self.current_passenger
    passenger.complete_service(self.busy_until)
    self.processed_passengers.append(passenger)
    self.current_passenger = None
    return passenger
```

이 메서드는 현재 처리 중인 승객이 완료될 시간이 되었는지 확인하고, 완료되었으면 승객을 반환합니다.

- `-> Optional[Passenger]`
  - `Passenger` 객체를 반환하거나, 완료할 승객이 없으면 `None`을 반환한다는 뜻입니다.

- `if self.current_passenger is None or self.busy_until > current_time:`
  - 처리 중인 승객이 없거나, 아직 완료 시간이 되지 않았다면 완료할 수 없습니다.
  - `or`는 두 조건 중 하나라도 참이면 전체가 참입니다.

- `return None`
  - 완료된 승객이 없다는 뜻으로 `None`을 반환합니다.

- `passenger = self.current_passenger`
  - 현재 승객을 지역 변수 `passenger`에 잠시 담습니다.

- `passenger.complete_service(self.busy_until)`
  - 승객 객체의 완료 시간을 기록합니다.
  - 내부에서 `turnaround_time`도 계산됩니다.

- `self.processed_passengers.append(passenger)`
  - 처리 완료 승객 목록에 추가합니다.
  - `append()`는 리스트 끝에 값을 하나 추가합니다.

- `self.current_passenger = None`
  - 카운터를 빈 상태로 바꿉니다.

- `return passenger`
  - 완료된 승객을 호출한 쪽에 알려 줍니다.

`simulation.py`는 이 반환값을 보고 완료 승객 목록에 추가합니다.

### `add_idle_time()` 메서드

```python
def add_idle_time(self, duration: int) -> None:
    if duration < 0:
        raise ValueError("Idle duration cannot be negative.")
    if self.is_idle:
        self.idle_time += duration
```

카운터가 쉬고 있던 시간을 누적합니다.

- `duration < 0`
  - 시간이 음수이면 잘못된 값입니다.

- `if self.is_idle:`
  - 카운터가 비어 있을 때만 유휴 시간을 더합니다.

- `self.idle_time += duration`
  - 기존 유휴 시간에 이번에 지나간 시간을 더합니다.

### `to_summary_dict()` 메서드

```python
def to_summary_dict(self) -> dict[str, Any]:
    return {
        "counter_id": self.counter_id,
        "counter_type": self.counter_type,
        "processed_count": len(self.processed_passengers),
        "total_service_time": self.total_service_time,
        "idle_time": self.idle_time,
        "processed_passenger_ids": [p.passenger_id for p in self.processed_passengers],
    }
```

카운터 요약 정보를 딕셔너리로 바꿉니다.

- `len(self.processed_passengers)`
  - 처리 완료 승객 수를 구합니다.

- `[p.passenger_id for p in self.processed_passengers]`
  - 리스트 컴프리헨션입니다.
  - `processed_passengers` 안의 승객을 하나씩 꺼내서 `passenger_id`만 모아 새 리스트를 만듭니다.

예를 들어 처리한 승객이 2번, 5번이라면 다음과 같은 값이 됩니다.

```python
"processed_passenger_ids": [2, 5]
```

## `SimulationResult` 클래스

### 클래스 선언과 필드

```python
@dataclass
class SimulationResult:
    passengers: list[Passenger]
    counters: list[Counter]
    event_log: list[str]
    finished_at: int
```

`SimulationResult`는 시뮬레이션이 끝난 뒤 결과를 묶어서 담는 클래스입니다.

- `passengers`
  - 모든 승객의 최종 상태입니다.

- `counters`
  - 모든 카운터의 최종 상태입니다.

- `event_log`
  - 시간별 이벤트 로그입니다.
  - 예를 들어 "승객 1 도착", "승객 2 서비스 완료" 같은 문자열이 들어갑니다.

- `finished_at`
  - 시뮬레이션이 끝난 시간입니다.

### `completed_passengers` 속성

```python
@property
def completed_passengers(self) -> list[Passenger]:
    return [passenger for passenger in self.passengers if passenger.is_completed]
```

완료된 승객만 골라서 반환합니다.

- `[passenger for passenger in self.passengers if passenger.is_completed]`
  - 리스트 컴프리헨션입니다.
  - `self.passengers`에서 승객을 하나씩 꺼냅니다.
  - `passenger.is_completed`가 참인 승객만 새 리스트에 넣습니다.

### `average_turnaround_time` 속성

```python
@property
def average_turnaround_time(self) -> float:
    completed = self.completed_passengers
    if not completed:
        return 0.0
    return sum(passenger.turnaround_time or 0 for passenger in completed) / len(completed)
```

전체 완료 승객의 평균 Turnaround Time을 계산합니다.

- `completed = self.completed_passengers`
  - 완료된 승객 목록을 가져옵니다.

- `if not completed:`
  - 완료 승객이 한 명도 없으면 평균을 계산할 수 없습니다.
  - 빈 리스트는 Python에서 거짓처럼 취급됩니다.

- `return 0.0`
  - 완료 승객이 없을 때는 평균을 `0.0`으로 반환합니다.

- `sum(passenger.turnaround_time or 0 for passenger in completed)`
  - 완료 승객들의 `turnaround_time`을 모두 더합니다.
  - `passenger.turnaround_time or 0`은 값이 `None`이거나 `0`처럼 거짓이면 `0`을 대신 사용합니다.

- `/ len(completed)`
  - 승객 수로 나누어 평균을 구합니다.

### `average_turnaround_by_class()` 메서드

```python
def average_turnaround_by_class(self) -> dict[int, float]:
    averages: dict[int, float] = {}
    for passenger_class in (FIRST, BUSINESS, ECONOMY):
        class_passengers = [
            passenger
            for passenger in self.completed_passengers
            if passenger.passenger_class == passenger_class
        ]
        if class_passengers:
            averages[passenger_class] = sum(
                passenger.turnaround_time or 0 for passenger in class_passengers
            ) / len(class_passengers)
        else:
            averages[passenger_class] = 0.0
    return averages
```

등급별 평균 Turnaround Time을 계산합니다.

- `averages: dict[int, float] = {}`
  - 결과를 담을 빈 딕셔너리를 만듭니다.
  - 키는 등급 숫자이고, 값은 평균 시간입니다.

- `for passenger_class in (FIRST, BUSINESS, ECONOMY):`
  - 세 등급을 하나씩 반복합니다.
  - `for`는 반복문입니다.

- `class_passengers = [...]`
  - 현재 등급에 해당하는 완료 승객만 골라냅니다.

- `if class_passengers:`
  - 해당 등급 승객이 있으면 평균을 계산합니다.

- `else:`
  - 해당 등급 승객이 없으면 평균을 `0.0`으로 넣습니다.

- `return averages`
  - 최종 딕셔너리를 반환합니다.

반환 예시는 다음과 같습니다.

```python
{
    1: 15.2,
    2: 18.7,
    3: 21.4,
}
```

## `create_default_counters()` 함수

```python
def create_default_counters() -> list[Counter]:
    return [
        Counter("C1", COUNTER_FIRST),
        Counter("C2", COUNTER_BUSINESS),
        Counter("C3", COUNTER_ECONOMY),
        Counter("C4", COUNTER_FLEX),
        Counter("C5", COUNTER_FLEX),
    ]
```

기본 카운터 5개를 만들어 반환합니다.

- `-> list[Counter]`
  - `Counter` 객체들이 들어 있는 리스트를 반환한다는 뜻입니다.

- `return [ ... ]`
  - 리스트를 반환합니다.

- `Counter("C1", COUNTER_FIRST)`
  - ID가 `"C1"`이고 종류가 `"First"`인 카운터를 만듭니다.

기본 구성은 다음과 같습니다.

| 카운터 | 종류 |
| --- | --- |
| C1 | First |
| C2 | Business |
| C3 | Economy |
| C4 | Flex |
| C5 | Flex |

`simulation.py`에서 별도 카운터 목록을 넘기지 않으면 이 함수가 호출되어 기본 카운터를 사용합니다.

## 주요 클래스/함수 설명

| 이름 | 종류 | 핵심 역할 |
| --- | --- | --- |
| `passenger_id_sort_key()` | 함수 | 승객 ID를 정렬 가능한 기준으로 바꿈 |
| `Passenger` | 클래스 | 승객 한 명의 입력 정보와 실행 상태를 저장 |
| `Passenger.start_service()` | 메서드 | 승객의 서비스 시작 시간과 카운터를 기록 |
| `Passenger.complete_service()` | 메서드 | 승객의 완료 시간과 Turnaround Time을 기록 |
| `Passenger.to_result_dict()` | 메서드 | CSV 저장용 딕셔너리로 변환 |
| `Counter` | 클래스 | 카운터 한 개의 처리 상태를 저장 |
| `Counter.assign_passenger()` | 메서드 | 빈 카운터에 승객을 배정 |
| `Counter.complete_current_passenger()` | 메서드 | 완료 시간이 된 승객을 완료 처리 |
| `Counter.add_idle_time()` | 메서드 | 카운터가 놀고 있던 시간을 누적 |
| `SimulationResult` | 클래스 | 시뮬레이션 결과 전체를 묶음 |
| `SimulationResult.average_turnaround_time` | 속성 | 전체 평균 Turnaround Time 계산 |
| `SimulationResult.average_turnaround_by_class()` | 메서드 | 등급별 평균 Turnaround Time 계산 |
| `create_default_counters()` | 함수 | 기본 카운터 5개 생성 |

## 다른 파일과의 관계

### `scheduler.py`와의 관계

`scheduler.py`는 입력 파일을 읽어서 `Passenger` 객체를 만듭니다.

```python
Passenger(
    passenger_id=passenger_id,
    arrival_time=arrival_time,
    passenger_class=passenger_class,
    service_time=service_time,
)
```

또한 시뮬레이션 결과를 CSV로 저장할 때 다음 메서드들을 사용합니다.

- `passenger.to_result_dict()`
- `counter.to_summary_dict()`
- `result.average_turnaround_time`
- `result.average_turnaround_by_class()`

### `simulation.py`와의 관계

`simulation.py`는 `models.py`에서 다음 이름들을 가져옵니다.

```python
from models import Counter, Passenger, SimulationResult, create_default_counters
```

그리고 시뮬레이션 중에 다음 일을 합니다.

- `Passenger` 목록을 도착 시간 순서로 관리
- `Counter`에 승객을 배정
- `Counter.complete_current_passenger()`로 완료 처리
- 마지막에 `SimulationResult`를 만들어 반환

### `strategies.py`와의 관계

`strategies.py`의 스케줄러들은 직접 `Passenger` 타입을 강하게 의존하지는 않지만, 승객 객체의 다음 값을 읽습니다.

- `passenger_id`
- `arrival_time`
- `passenger_class`
- `service_time`

즉, `models.py`의 `Passenger` 필드 이름이 스케줄러 선택 기준에 사용됩니다.

## 코드 실행 흐름

`models.py` 자체는 단독으로 실행되는 파일이라기보다, 다른 파일에서 가져다 쓰는 재료 파일입니다.

기본 흐름은 다음과 같습니다.

1. `scheduler.py`가 `input.txt`를 읽습니다.
2. 각 입력 줄마다 `Passenger` 객체를 만듭니다.
3. `simulation.py`가 `SimulationEngine`을 만들면서 `Passenger` 목록과 `Counter` 목록을 준비합니다.
4. 카운터가 승객을 배정받으면 `Counter.assign_passenger()`가 호출됩니다.
5. 그 안에서 `Passenger.start_service()`가 호출되어 시작 시간이 기록됩니다.
6. 시간이 지나 완료 시점이 되면 `Counter.complete_current_passenger()`가 호출됩니다.
7. 그 안에서 `Passenger.complete_service()`가 호출되어 완료 시간과 Turnaround Time이 기록됩니다.
8. 모든 승객이 완료되면 `SimulationResult` 객체가 만들어집니다.
9. `scheduler.py`가 `SimulationResult`를 이용해 CSV와 로그 파일을 씁니다.

## 처음 읽을 때 핵심 포인트

- `models.py`는 알고리즘을 결정하는 파일이 아닙니다. 데이터를 담고 상태를 바꾸는 기본 객체를 정의하는 파일입니다.
- `Passenger`는 승객 한 명, `Counter`는 카운터 한 개, `SimulationResult`는 전체 결과를 의미합니다.
- `arrival_time`과 `service_time`은 입력값이고, `service_start_time`, `completion_time`, `turnaround_time`은 시뮬레이션 중에 계산됩니다.
- `@dataclass` 덕분에 `Passenger(...)`, `Counter(...)`처럼 객체를 쉽게 만들 수 있습니다.
- `@property`가 붙은 메서드는 함수처럼 호출하지 않고 속성처럼 읽습니다.
- `None`은 아직 값이 정해지지 않았다는 표시로 사용됩니다.
- `Counter.assign_passenger()`는 서비스를 시작시키고, `Counter.complete_current_passenger()`는 서비스를 끝냅니다.
- 평균 Turnaround Time은 `SimulationResult`에서 계산됩니다.
