# 운영체제 설계 과제

공항 체크인 카운터를 대상으로 여러 스케줄링 전략을 비교하는 운영체제 설계 프로젝트입니다.

## 구성

- `scheduler.py`: 입력 파일 파싱, 스케줄러 실행, 결과 파일 생성
- `simulation.py`: 체크인 시뮬레이션 엔진
- `strategies.py`: FCFS, Priority, SJF, 제안 스케줄러 구현
- `models.py`: 승객, 카운터, 시뮬레이션 결과 모델
- `report_utils.py`: CSV/PNG 결과 생성 유틸리티
- `generate_final_report.py`: 최종 보고서 문서 생성 스크립트
- `input.txt`: 시뮬레이션 입력 데이터
- `output/`: 실행 결과 CSV, 로그, 비교 이미지
- `docs/`: 코드 및 실행 흐름 설명 문서

## 실행 방법

```powershell
python scheduler.py input.txt --scheduler all --output output
```

특정 스케줄러만 실행하려면 다음 중 하나를 지정합니다.

```powershell
python scheduler.py input.txt --scheduler fcfs --output output
python scheduler.py input.txt --scheduler priority --output output
python scheduler.py input.txt --scheduler sjf --output output
python scheduler.py input.txt --scheduler ours --output output
```

## 테스트

```powershell
python -m unittest
```

## 보고서 생성

보고서 생성에는 `python-docx`가 필요합니다.

```powershell
pip install -r requirements.txt
python generate_final_report.py
```
