# `input.txt` 구조

## `input.txt`의 역할

`input.txt`는 시뮬레이션에 들어갈 승객 데이터를 담은 입력 파일이다.

`scheduler.py`가 이 파일을 읽어서 `Passenger` 객체 리스트를 만들고, 각 스케줄러가 이 승객들을 카운터에 배정한다.

`generate_final_report.py`는 `input.txt`를 직접 읽지 않는다. 대신 `scheduler.py`가 `input.txt`를 처리해서 만든 `output/*.csv`를 읽는다.

## 전체 형식

`input.txt`에는 헤더가 없다. 각 줄은 승객 1명을 의미하고, 4개 컬럼으로 되어 있다.

```text
passenger_id    arrival_time    class    service_time
```

실제 첫 줄은 다음과 같다.

```text
1	0	3	7
```

이 줄의 의미는 다음과 같다.

| 값 | 컬럼 | 의미 |
|---|---|---|
| `1` | `passenger_id` | 승객 ID가 1번 |
| `0` | `arrival_time` | 시간 0에 도착 |
| `3` | `class` | Economy 승객 |
| `7` | `service_time` | 처리에 7시간 단위가 필요 |

## 컬럼 설명

| 순서 | 컬럼명 | 예시 | 의미 |
|---|---|---:|---|
| 1 | `passenger_id` | `1` | 승객을 구분하는 ID |
| 2 | `arrival_time` | `0` | 승객이 공항 체크인 대기열에 도착한 시간 |
| 3 | `class` | `3` | 승객 등급 |
| 4 | `service_time` | `7` | 체크인 카운터에서 처리하는 데 걸리는 시간 |

## `class` 값의 의미

| class 값 | 등급명 |
|---:|---|
| `1` | `First` |
| `2` | `Business` |
| `3` | `Economy` |

예를 들어 다음 줄은 First 승객이다.

```text
2	0	1	12
```

의미는 `2번 승객`, `시간 0 도착`, `First 등급`, `서비스 시간 12`이다.

## 현재 입력 파일 요약

현재 `input.txt`는 총 50명의 승객을 담고 있다.

| 항목 | 값 |
|---|---:|
| 전체 승객 수 | 50 |
| 전체 `service_time` 합계 | 379 |
| First 승객 수 | 8 |
| Business 승객 수 | 11 |
| Economy 승객 수 | 31 |

`test_scheduler.py`는 승객 수 50명과 전체 `service_time` 합계 379를 자동으로 검사한다.

## `scheduler.py`가 읽는 방식

입력 파일은 `scheduler.py`의 `parse_input_file()` 함수가 읽는다.

```python
def parse_input_file(input_path: Path) -> list[Passenger]:
    """Parse passenger rows: passenger_id arrival_time passenger_class service_time."""
    passengers: list[Passenger] = []
```

`passengers: list[Passenger] = []`는 빈 리스트를 만든다. 이 리스트에 `Passenger` 객체가 하나씩 추가된다.

파일을 여는 코드는 다음과 같다.

```python
with input_path.open("r", encoding="utf-8") as file:
    for line_number, raw_line in enumerate(file, start=1):
```

`with`는 파일을 자동으로 닫아 주는 문법이다.

`enumerate(file, start=1)`은 파일을 한 줄씩 읽으면서 줄 번호도 함께 만든다. 오류가 발생했을 때 몇 번째 줄이 문제인지 알려주기 위해 사용한다.

주석과 빈 줄을 처리하는 코드는 다음과 같다.

```python
line = raw_line.partition("#")[0].strip()
if not line:
    continue
```

`partition("#")`는 `#` 뒤쪽을 주석으로 보고 잘라낸다.

`strip()`은 앞뒤 공백을 제거한다.

`if not line: continue`는 빈 줄이면 건너뛴다는 뜻이다.

컬럼 분리는 다음 코드로 한다.

```python
parts = re.split(r"[\s,]+", line)
if len(parts) != 4:
    raise ValueError(
        f"{input_path}:{line_number}: expected 4 columns "
        "(passenger_id arrival_time class service_time)."
    )
```

`re.split(r"[\s,]+", line)`은 공백, 탭, 쉼표를 기준으로 줄을 나눈다. 그래서 입력 파일은 탭으로 구분되어 있어도 되고, 공백이나 쉼표로 구분되어 있어도 된다.

컬럼이 정확히 4개가 아니면 `ValueError`를 발생시킨다.

각 컬럼은 다음 변수에 저장된다.

```python
passenger_id_token, arrival_token, class_token, service_token = parts
```

이 문법은 리스트 언패킹이다. `parts` 안의 4개 값을 왼쪽 변수 4개에 순서대로 넣는다.

그 다음 값 검증을 한다.

```python
passenger_id = _parse_passenger_id(passenger_id_token)
arrival_time = _parse_non_negative_int(input_path, line_number, "arrival_time", arrival_token)
passenger_class = _parse_passenger_class(input_path, line_number, class_token)
service_time = _parse_positive_int(input_path, line_number, "service_time", service_token)
```

| 함수 | 검사 내용 |
|---|---|
| `_parse_passenger_id()` | 숫자 ID면 정수로 변환 |
| `_parse_non_negative_int()` | `arrival_time`이 0 이상 정수인지 검사 |
| `_parse_passenger_class()` | `class`가 1, 2, 3 중 하나인지 검사 |
| `_parse_positive_int()` | `service_time`이 1 이상 정수인지 검사 |

검증이 끝나면 `Passenger` 객체를 만든다.

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

`append()`는 리스트 끝에 값을 추가하는 함수이다.

마지막에는 승객을 정렬해서 반환한다.

```python
return sorted(passengers, key=lambda passenger: passenger.sort_key())
```

`sorted()`는 새 정렬 리스트를 만든다. `key=lambda ...`는 어떤 기준으로 정렬할지 알려주는 짧은 함수이다. 여기서는 승객의 `sort_key()` 결과를 기준으로 정렬한다.

## 좋은 입력 예시

```text
1 0 3 7
2 0 1 12
3 1 3 5
4 2 2 9
```

위처럼 공백으로 구분해도 된다.

```text
1,0,3,7
2,0,1,12
```

쉼표로 구분해도 `scheduler.py`의 파서가 처리할 수 있다.

## 잘못된 입력 예시

컬럼이 부족한 경우:

```text
1 0 3
```

`service_time`이 없으므로 오류가 난다.

`class` 값이 잘못된 경우:

```text
1 0 4 7
```

`class`는 1, 2, 3 중 하나여야 한다.

`service_time`이 0 이하인 경우:

```text
1 0 3 0
```

서비스 시간은 양수여야 한다.

## 출력 파일과의 연결

`input.txt`의 각 컬럼은 `output/passenger_results.csv`에서 다음 컬럼들과 연결된다.

| `input.txt` 컬럼 | `output/passenger_results.csv` 컬럼 | 설명 |
|---|---|---|
| `passenger_id` | `passenger_id` | 같은 승객 ID |
| `arrival_time` | `arrival_time` | 도착 시간 |
| `class` | `class`, `class_name` | 숫자 등급과 등급명 |
| `service_time` | `service_time` | 처리 시간 |
| 없음 | `service_start_time` | 시뮬레이션 결과로 계산 |
| 없음 | `completion_time` | 시뮬레이션 결과로 계산 |
| 없음 | `turnaround_time` | `completion_time - arrival_time` |
| 없음 | `assigned_counter_id` | 배정된 카운터 ID |
