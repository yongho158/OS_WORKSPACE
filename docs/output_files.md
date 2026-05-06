# `output` 폴더 파일 설명

## `output` 폴더의 역할

`output` 폴더는 `scheduler.py`를 실행해서 생성되는 결과 파일을 담는다.

생성 명령어는 다음과 같다.

```powershell
python scheduler.py input.txt --scheduler all --output output
```

`--scheduler all`을 사용하면 `fcfs`, `priority`, `sjf`, `ours` 네 가지 스케줄러를 모두 실행하고, 스케줄러별 결과 파일과 전체 비교 파일을 만든다.

## 전체 파일 구조

```text
output/
├─ passenger_results.csv
├─ class_summary.csv
├─ counter_summary.csv
├─ simulation_log.txt
├─ att_comparison.csv
├─ att_comparison.png
├─ fcfs_passenger_results.csv
├─ fcfs_class_summary.csv
├─ fcfs_counter_summary.csv
├─ fcfs_simulation_log.txt
├─ priority_passenger_results.csv
├─ priority_class_summary.csv
├─ priority_counter_summary.csv
├─ priority_simulation_log.txt
├─ sjf_passenger_results.csv
├─ sjf_class_summary.csv
├─ sjf_counter_summary.csv
├─ sjf_simulation_log.txt
├─ ours_passenger_results.csv
├─ ours_class_summary.csv
├─ ours_counter_summary.csv
└─ ours_simulation_log.txt
```

접두어가 없는 `passenger_results.csv`, `class_summary.csv`, `counter_summary.csv`, `simulation_log.txt`는 기본 보고서용 결과이다. `--scheduler all` 실행 시 코드에서는 `ours` 스케줄러를 대표 결과로 사용한다.

즉, 다음 파일들은 같은 성격의 데이터이다.

| 대표 파일 | 같은 내용의 스케줄러별 파일 |
|---|---|
| `passenger_results.csv` | `ours_passenger_results.csv` |
| `class_summary.csv` | `ours_class_summary.csv` |
| `counter_summary.csv` | `ours_counter_summary.csv` |
| `simulation_log.txt` | `ours_simulation_log.txt` |

## 파일 생성 위치

`scheduler.py`의 `write_outputs()` 함수가 결과 파일을 만든다.

```python
for scheduler_name, result in results.items():
    prefix = f"{scheduler_name}_"
    _write_passenger_results(result, output_dir / f"{prefix}passenger_results.csv")
    _write_class_summary(result, output_dir / f"{prefix}class_summary.csv")
    _write_counter_summary(result, output_dir / f"{prefix}counter_summary.csv")
    _write_simulation_log(result, output_dir / f"{prefix}simulation_log.txt")
```

이 코드는 스케줄러별 파일을 만든다. 예를 들어 `scheduler_name`이 `fcfs`이면 `prefix`는 `fcfs_`가 된다.

f-string 때문에 다음 파일명이 만들어진다.

```text
fcfs_passenger_results.csv
fcfs_class_summary.csv
fcfs_counter_summary.csv
fcfs_simulation_log.txt
```

대표 파일은 다음 코드로 따로 만든다.

```python
canonical_result = results[canonical_scheduler]
_write_passenger_results(canonical_result, output_dir / "passenger_results.csv")
_write_class_summary(canonical_result, output_dir / "class_summary.csv")
_write_counter_summary(canonical_result, output_dir / "counter_summary.csv")
_write_simulation_log(canonical_result, output_dir / "simulation_log.txt")
```

전체 ATT 비교 파일과 그래프는 다음 코드로 만든다.

```python
_write_att_comparison(results, output_dir / "att_comparison.csv")
write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
```

## 출력 파일 설명표

| 파일 | 생성 함수 | 담고 있는 내용 | `generate_final_report.py` 사용 여부 |
|---|---|---|---|
| `passenger_results.csv` | `_write_passenger_results()` | 대표 스케줄러의 승객별 결과 | 사용 |
| `class_summary.csv` | `_write_class_summary()` | 대표 스케줄러의 등급별 평균 TAT | 사용 |
| `counter_summary.csv` | `_write_counter_summary()` | 대표 스케줄러의 카운터별 처리 통계 | 사용 |
| `simulation_log.txt` | `_write_simulation_log()` | 대표 스케줄러의 시간별 이벤트 로그 | 직접 사용 안 함 |
| `att_comparison.csv` | `_write_att_comparison()` | 스케줄러별 ATT 비교 | 사용 |
| `att_comparison.png` | `write_att_comparison_png()` | 스케줄러별 ATT 막대그래프 | 사용 |
| `fcfs_passenger_results.csv` | `_write_passenger_results()` | FCFS 승객별 결과 | 직접 사용 안 함 |
| `fcfs_class_summary.csv` | `_write_class_summary()` | FCFS 등급별 평균 TAT | 사용 |
| `fcfs_counter_summary.csv` | `_write_counter_summary()` | FCFS 카운터별 통계 | 직접 사용 안 함 |
| `fcfs_simulation_log.txt` | `_write_simulation_log()` | FCFS 로그 | 직접 사용 안 함 |
| `priority_passenger_results.csv` | `_write_passenger_results()` | Priority 승객별 결과 | 직접 사용 안 함 |
| `priority_class_summary.csv` | `_write_class_summary()` | Priority 등급별 평균 TAT | 사용 |
| `priority_counter_summary.csv` | `_write_counter_summary()` | Priority 카운터별 통계 | 직접 사용 안 함 |
| `priority_simulation_log.txt` | `_write_simulation_log()` | Priority 로그 | 직접 사용 안 함 |
| `sjf_passenger_results.csv` | `_write_passenger_results()` | SJF 승객별 결과 | 직접 사용 안 함 |
| `sjf_class_summary.csv` | `_write_class_summary()` | SJF 등급별 평균 TAT | 사용 |
| `sjf_counter_summary.csv` | `_write_counter_summary()` | SJF 카운터별 통계 | 직접 사용 안 함 |
| `sjf_simulation_log.txt` | `_write_simulation_log()` | SJF 로그 | 직접 사용 안 함 |
| `ours_passenger_results.csv` | `_write_passenger_results()` | Our Scheduler 승객별 결과 | 대표 파일과 중복 |
| `ours_class_summary.csv` | `_write_class_summary()` | Our Scheduler 등급별 평균 TAT | 사용 |
| `ours_counter_summary.csv` | `_write_counter_summary()` | Our Scheduler 카운터별 통계 | 대표 파일과 중복 |
| `ours_simulation_log.txt` | `_write_simulation_log()` | Our Scheduler 로그 | 대표 파일과 중복 |

## `passenger_results.csv`

승객 1명당 한 줄씩 결과가 들어간다.

헤더는 다음과 같다.

```csv
passenger_id,class,class_name,arrival_time,service_time,service_start_time,completion_time,turnaround_time,assigned_counter_id
```

예시:

```csv
passenger_id,class,class_name,arrival_time,service_time,service_start_time,completion_time,turnaround_time,assigned_counter_id
1,3,Economy,0,7,0,7,7,C2
2,1,First,0,12,0,12,12,C1
```

컬럼 의미는 다음과 같다.

| 컬럼 | 의미 |
|---|---|
| `passenger_id` | 승객 ID |
| `class` | 승객 등급 숫자. 1은 First, 2는 Business, 3은 Economy |
| `class_name` | 승객 등급 이름 |
| `arrival_time` | 승객 도착 시간 |
| `service_time` | 필요한 처리 시간 |
| `service_start_time` | 실제 서비스 시작 시간 |
| `completion_time` | 서비스 완료 시간 |
| `turnaround_time` | `completion_time - arrival_time` |
| `assigned_counter_id` | 배정된 카운터 |

`generate_final_report.py`는 이 파일을 읽어 `3.1 승객별 결과` 표를 만든다.

## `class_summary.csv`

등급별 평균 Turnaround Time을 담는다.

헤더는 다음과 같다.

```csv
class,class_name,passenger_count,average_turnaround_time
```

예시:

```csv
class,class_name,passenger_count,average_turnaround_time
1,First,8,20.38
2,Business,11,21.73
3,Economy,31,17.97
```

`generate_final_report.py`는 이 파일을 읽어 `3.2 등급별 평균 Turnaround Time` 표를 만든다.

스케줄러별 파일인 `fcfs_class_summary.csv`, `priority_class_summary.csv`, `sjf_class_summary.csv`, `ours_class_summary.csv`는 `5. Trade-off 분석 및 한계` 표에 사용된다.

## `counter_summary.csv`

카운터별 처리 통계를 담는다.

헤더는 다음과 같다.

```csv
counter_id,counter_type,processed_count,total_service_time,idle_time,processed_passenger_ids
```

예시:

```csv
counter_id,counter_type,processed_count,total_service_time,idle_time,processed_passenger_ids
C1,First,6,76,6,2 14 19 32 40 46
C2,Business,9,82,0,1 8 11 24 21 33 37 42 49
```

컬럼 의미는 다음과 같다.

| 컬럼 | 의미 |
|---|---|
| `counter_id` | 카운터 ID. 예: `C1` |
| `counter_type` | 카운터 유형. `First`, `Business`, `Economy`, `Flex` |
| `processed_count` | 처리한 승객 수 |
| `total_service_time` | 처리한 승객들의 서비스 시간 합 |
| `idle_time` | 카운터가 쉬고 있던 시간 |
| `processed_passenger_ids` | 해당 카운터가 처리한 승객 ID 목록 |

`generate_final_report.py`는 이 파일을 읽어 `3.3 카운터별 통계` 표를 만든다.

## `simulation_log.txt`

시간 흐름에 따른 이벤트 로그이다.

예시:

```text
time=0: passenger 1 arrived (class=3, service=7).
time=0: passenger 2 arrived (class=1, service=12).
time=0: passenger 2 started at C1; completes at 12.
time=0: passenger 1 started at C2; completes at 7.
time=0: counters C3,C4,C5 idle for 1 time unit(s).
```

이 파일은 디버깅이나 시뮬레이션 흐름 확인에 유용하다. 현재 `generate_final_report.py`는 로그 파일을 Word 보고서에 직접 넣지 않는다.

## `att_comparison.csv`

스케줄러별 평균 Turnaround Time을 비교하는 파일이다.

헤더는 다음과 같다.

```csv
scheduler,scheduler_name,ATT,improvement_rate
```

예시:

```csv
scheduler,scheduler_name,ATT,improvement_rate
fcfs,Baseline A: FCFS,19.52,1.74
priority,Baseline B: Priority,22.50,14.76
sjf,Baseline C: Non-preemptive SJF,14.90,-28.72
ours,Our Scheduler: MLQ + Weighted HRRN + SJF,19.18,0.00
```

컬럼 의미는 다음과 같다.

| 컬럼 | 의미 |
|---|---|
| `scheduler` | 코드에서 쓰는 짧은 스케줄러 이름 |
| `scheduler_name` | 보고서용 전체 스케줄러 이름 |
| `ATT` | Average Turnaround Time |
| `improvement_rate` | `ours` 기준 개선율 |

`improvement_rate`는 다음 식으로 계산된다.

```text
(비교 대상 ATT - ours ATT) / 비교 대상 ATT * 100
```

값이 양수면 `ours`가 해당 대상보다 ATT가 낮다는 뜻이다. 값이 음수면 `ours`가 해당 대상보다 ATT가 높다는 뜻이다.

## `att_comparison.png`

`att_comparison.csv`의 ATT 값을 막대그래프로 만든 PNG 이미지이다.

`scheduler.py`는 다음 함수를 통해 이 파일을 만든다.

```python
write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
```

`report_utils.py` 안에서는 `matplotlib`이 설치되어 있으면 `matplotlib`으로 그래프를 만들고, 없으면 내장 PNG 생성 코드로 대체한다.

`generate_final_report.py`는 이 이미지가 존재할 때 Word 문서에 넣는다.

```python
graph_path = OUTPUT_DIR / "att_comparison.png"
if graph_path.exists():
    run.add_picture(str(graph_path), width=Inches(5.8))
```

## 파일을 다시 만들 때 주의할 점

`generate_final_report.py`는 `scheduler.py`를 자동으로 실행하지 않는다.

따라서 `input.txt`나 스케줄러 코드를 바꾼 뒤 보고서를 다시 만들려면 순서가 중요하다.

```powershell
python scheduler.py input.txt --scheduler all --output output
python generate_final_report.py
```

첫 번째 명령은 `output` 파일을 최신으로 만들고, 두 번째 명령은 그 결과를 Word 보고서에 넣는다.
