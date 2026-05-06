# `generate_final_report.py` 설명

## `generate_final_report.py`의 역할

`generate_final_report.py`는 이미 생성된 `output` 폴더의 CSV/PNG 파일을 읽어서 Word 문서(`.docx`) 형식의 최종 보고서를 자동으로 만드는 파일이다.

중요한 점은 이 파일이 시뮬레이션을 직접 실행하지 않는다는 것이다. 시뮬레이션 실행과 `output` 파일 생성은 `scheduler.py`가 담당하고, `generate_final_report.py`는 그 결과 파일을 읽어 보고서 표와 그림으로 넣는다.

실행 명령어는 다음과 같다.

```powershell
python generate_final_report.py
```

보고서 생성 전에 결과 파일을 최신 상태로 만들려면 먼저 다음 명령을 실행한다.

```powershell
python scheduler.py input.txt --scheduler all --output output
```

## 전체 보고서 생성 흐름

```text
output/*.csv, output/*.png
        ↓
generate_final_report.py
        ↓
Word 템플릿 찾기
        ↓
문서 본문 비우기
        ↓
기본 글꼴/여백 설정
        ↓
제목, 목차, 설계, 구현, 결과, 비교, 결론 섹션 작성
        ↓
운영체제최종보고서_작성본.docx 저장
```

`output` 파일 중 실제로 보고서에 들어가는 파일은 다음과 같다.

| 보고서 함수 | 읽는 파일 | 보고서에 들어가는 내용 |
|---|---|---|
| `add_results_sections()` | `output/passenger_results.csv` | 승객별 결과 표 |
| `add_results_sections()` | `output/class_summary.csv` | 등급별 평균 Turnaround Time 표 |
| `add_results_sections()` | `output/counter_summary.csv` | 카운터별 통계 표 |
| `add_comparison_sections()` | `output/att_comparison.csv` | 스케줄러별 ATT 비교 표 |
| `add_comparison_sections()` | `output/att_comparison.png` | ATT 비교 그래프 |
| `add_tradeoff_section()` | `output/fcfs_class_summary.csv` 등 | 스케줄러별 등급 평균 TAT 비교 |

## import 구문 설명

파일 맨 위에는 필요한 기능을 가져오는 `import` 구문이 있다.

```python
from __future__ import annotations

import csv
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt
```

`from __future__ import annotations`는 타입 힌트를 조금 더 유연하게 쓰게 해 주는 문장이다. 예를 들어 `Path | None`, `list[dict[str, str]]` 같은 타입 표기를 사용할 때 도움이 된다.

`csv`는 CSV 파일을 읽기 위해 사용한다. 이 코드에서는 `csv.DictReader`를 사용해서 CSV 한 줄을 딕셔너리처럼 읽는다.

`Path`는 파일 경로를 다루는 클래스이다. 문자열 경로를 직접 이어 붙이는 것보다 안전하고 읽기 쉽다.

```python
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
```

`Path(__file__)`은 현재 파이썬 파일의 경로를 뜻한다. `resolve()`는 절대 경로로 바꾸고, `.parent`는 그 파일이 들어 있는 폴더를 뜻한다. `ROOT / "output"`처럼 `/` 연산자를 쓰면 운영체제에 맞게 경로가 합쳐진다.

`Document`는 `python-docx` 라이브러리의 핵심 클래스이다. 새 Word 문서를 만들거나 기존 `.docx` 템플릿을 열 때 사용한다.

`WD_ALIGN_PARAGRAPH`는 문단 정렬을 지정할 때 사용한다. 예를 들어 제목을 가운데 정렬할 때 쓴다.

`WD_SECTION_START`는 현재 파일에서 import되어 있지만 실제 코드에서는 사용되지 않는다.

`OxmlElement`, `qn`은 `python-docx`가 기본으로 제공하지 않는 세부 Word XML 설정을 직접 만질 때 사용한다. 이 코드에서는 표 셀 배경색, 표 테두리, 한글 글꼴 설정에 사용된다.

`Cm`, `Inches`, `Pt`는 Word 문서의 크기 단위이다. `Cm(1.6)`은 여백, `Inches(5.8)`은 그림 너비, `Pt(10)`은 글자 크기에 사용된다.

## 주요 상수

```python
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
REPORT_PATH = ROOT / "운영체제최종보고서_작성본.docx"
REVIEWED_REPORT_PATH = ROOT / "운영체제최종보고서_작성본_검토수정.docx"

KOREAN_FONT = "맑은 고딕"
CODE_FONT = "Consolas"
TEAM_NAME = "7팀"
MEMBER_NAME = "최용호"
MEMBER_ID = "2022152039"
```

상수는 코드 전체에서 반복해서 쓰는 값을 이름으로 저장한 것이다.

`OUTPUT_DIR`은 보고서가 읽을 결과 파일 폴더이다. `REPORT_PATH`는 기본 저장 파일명이고, `REVIEWED_REPORT_PATH`는 기본 파일 저장이 실패했을 때 대신 저장할 파일명이다.

`TEAM_NAME`, `MEMBER_NAME`, `MEMBER_ID`는 제목 페이지 표에 들어간다. 아래 코드처럼 f-string으로 이름과 학번을 합친다.

```python
["팀 원", f"{MEMBER_NAME} / {MEMBER_ID}"]
```

f-string은 문자열 앞에 `f`를 붙이고 `{변수명}`을 넣어 변수 값을 문자열 안에 끼워 넣는 문법이다.

## CSV 읽기 함수

```python
def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))
```

이 함수는 CSV 파일을 읽어서 `list[dict[str, str]]` 형태로 돌려준다.

예를 들어 `output/class_summary.csv`가 다음과 같다고 하자.

```csv
class,class_name,passenger_count,average_turnaround_time
1,First,8,20.38
```

`csv.DictReader`로 읽으면 한 줄이 다음 딕셔너리처럼 된다.

```python
{
    "class": "1",
    "class_name": "First",
    "passenger_count": "8",
    "average_turnaround_time": "20.38",
}
```

초보자 관점에서 중요한 문법은 다음과 같다.

| 코드 | 뜻 |
|---|---|
| `def read_csv(...)` | 함수를 정의한다. |
| `path: Path` | `path` 매개변수는 `Path` 타입이라는 힌트이다. |
| `-> list[dict[str, str]]` | 반환값은 딕셔너리들의 리스트라는 힌트이다. |
| `with ... as file` | 파일을 열고, 블록이 끝나면 자동으로 닫는다. |
| `encoding="utf-8-sig"` | UTF-8 BOM이 있어도 CSV를 정상적으로 읽는다. |
| `list(...)` | `DictReader` 결과를 실제 리스트로 만든다. |

## Word 템플릿 찾기

```python
def find_template() -> Path | None:
    matches = sorted(ROOT.glob("운영체제최종보고서서식*.docx"))
    return matches[0] if matches else None
```

`ROOT.glob("운영체제최종보고서서식*.docx")`는 프로젝트 폴더에서 이름이 `운영체제최종보고서서식`으로 시작하고 `.docx`로 끝나는 파일을 찾는다.

`Path | None`은 반환값이 `Path`일 수도 있고 `None`일 수도 있다는 뜻이다. 템플릿 파일을 찾으면 첫 번째 파일을 반환하고, 없으면 `None`을 반환한다.

```python
return matches[0] if matches else None
```

이 문장은 조건 표현식이다. `matches`가 비어 있지 않으면 `matches[0]`, 비어 있으면 `None`을 반환한다.

## 문서 본문 비우기

```python
def clear_document_body(doc: Document) -> None:
    body = doc._body._element
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)
```

템플릿의 여백 같은 섹션 설정은 유지하고, 본문 내용만 지우는 함수이다.

`doc._body._element`처럼 `_`로 시작하는 속성은 보통 내부 구현에 가까운 속성이다. 일반적인 `python-docx` 기능만으로 본문 전체를 깔끔하게 지우기 어려워서 Word XML 요소에 직접 접근한다.

`for child in list(body):`는 문서 본문의 자식 요소들을 하나씩 반복한다. `list(body)`로 감싸는 이유는 반복 중에 `body.remove(child)`로 요소를 지우기 때문이다.

`sectPr`는 Word 문서의 섹션 설정이다. 여백 같은 정보가 들어 있으므로 지우지 않고 `continue`로 건너뛴다.

## 기본 스타일 설정

```python
def set_default_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = KOREAN_FONT
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), KOREAN_FONT)
    normal.font.size = Pt(10)
```

`doc.styles["Normal"]`은 Word의 기본 문단 스타일이다. 기본 글꼴을 `맑은 고딕`, 글자 크기를 10pt로 설정한다.

한글 글꼴은 `normal.font.name`만으로 제대로 적용되지 않는 경우가 있다. 그래서 아래처럼 `w:eastAsia` 속성도 같이 설정한다.

```python
normal._element.rPr.rFonts.set(qn("w:eastAsia"), KOREAN_FONT)
```

제목 스타일도 같은 방식으로 한글 글꼴을 적용한다.

```python
for style_name in ("Heading 1", "Heading 2", "Heading 3"):
    style = doc.styles[style_name]
    style.font.name = KOREAN_FONT
    style._element.rPr.rFonts.set(qn("w:eastAsia"), KOREAN_FONT)
```

`for`문은 여러 값을 하나씩 꺼내 반복 실행한다. 여기서는 `Heading 1`, `Heading 2`, `Heading 3` 스타일에 같은 설정을 적용한다.

문서 여백은 각 섹션마다 설정한다.

```python
for section in doc.sections:
    section.top_margin = Cm(1.6)
    section.bottom_margin = Cm(1.6)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
```

## 글자, 문단, 제목 추가 함수

### `set_run_font()`

```python
def set_run_font(run, font_name: str = KOREAN_FONT, size: int | None = None, bold: bool | None = None) -> None:
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
```

Word 문서에서는 실제 글자 조각을 `run`이라고 부른다. 이 함수는 `run`의 글꼴, 크기, 굵기를 설정한다.

`size: int | None = None`은 `size`가 정수이거나 `None`일 수 있다는 뜻이다. `None`은 값이 없다는 뜻이다.

```python
if size is not None:
```

이 조건문은 `size`가 전달된 경우에만 글자 크기를 바꾼다.

### `add_paragraph()`

```python
def add_paragraph(doc: Document, text: str = "", bold_prefix: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    if bold_prefix and text.startswith(bold_prefix):
        prefix_run = paragraph.add_run(bold_prefix)
        set_run_font(prefix_run, bold=True)
        body_run = paragraph.add_run(text[len(bold_prefix):])
        set_run_font(body_run)
    else:
        run = paragraph.add_run(text)
        set_run_font(run)
```

문단을 하나 추가하는 함수이다. `bold_prefix`가 지정되어 있고 문장이 그 접두사로 시작하면, 접두사 부분만 굵게 만든다.

`text[len(bold_prefix):]`는 문자열 슬라이싱이다. 접두사 길이 이후의 나머지 문자열만 잘라서 가져온다.

### `add_heading()`

```python
def add_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_heading(level=level)
    run = paragraph.add_run(text)
    set_run_font(run, size=16 if level == 1 else 13, bold=True)
```

제목을 추가하는 함수이다. `level=1`이면 큰 제목이고, `level=2`이면 하위 제목이다.

```python
size=16 if level == 1 else 13
```

이 부분도 조건 표현식이다. 1단계 제목이면 16pt, 아니면 13pt를 사용한다.

### `add_code_block()`

```python
def add_code_block(doc: Document, text: str) -> None:
    for line in text.strip("\n").splitlines():
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(0.5)
        run = paragraph.add_run(line)
        set_run_font(run, CODE_FONT, size=9)
```

보고서 안에 코드처럼 보이는 블록을 넣는 함수이다.

`strip("\n")`은 앞뒤 줄바꿈을 제거한다. `splitlines()`는 여러 줄 문자열을 한 줄씩 나눈다. 각 줄을 문단으로 넣고 왼쪽 들여쓰기를 적용한다.

## 표 생성 함수

### 셀 배경색 지정

```python
def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)
```

표의 셀 배경색을 설정한다. `fill`에는 `"D9EAF7"` 같은 색상 코드가 들어간다.

### 표 테두리 지정

```python
def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
```

표 테두리를 직접 설정하는 함수이다. 이미 테두리 설정이 있으면 사용하고, 없으면 새로 만든다.

```python
for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
```

위쪽, 왼쪽, 아래쪽, 오른쪽, 내부 가로선, 내부 세로선을 반복하면서 같은 스타일을 적용한다.

### 셀 텍스트 지정

```python
def set_cell_text(cell, text: str, bold: bool = False, size: int = 9, align_center: bool = False) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    if align_center:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(str(text))
    set_run_font(run, size=size, bold=bold)
```

셀 안의 기존 텍스트를 지우고 새 텍스트를 넣는다. `str(text)`는 숫자도 문자열로 바꿔서 안전하게 넣기 위한 것이다.

### 전체 표 추가

```python
def add_table(doc: Document, headers: list[str], rows: list[list[str]], font_size: int = 9):
    table = doc.add_table(rows=1, cols=len(headers))
    try:
        table.style = "Table Grid"
    except KeyError:
        pass
```

`headers`는 표의 첫 줄 제목이고, `rows`는 실제 데이터 줄이다.

`try/except KeyError`는 예외 처리 문법이다. 현재 Word 템플릿에 `"Table Grid"` 스타일이 없으면 `KeyError`가 발생할 수 있다. 이때 프로그램이 멈추지 않게 `except KeyError: pass`로 넘어간다.

```python
for index, header in enumerate(headers):
    cell = table.rows[0].cells[index]
    shade_cell(cell, "D9EAF7")
    set_cell_text(cell, header, bold=True, size=font_size, align_center=True)
```

`enumerate(headers)`는 리스트 값을 하나씩 꺼내면서 동시에 번호도 준다. `index`는 몇 번째 셀인지, `header`는 셀에 넣을 제목이다.

데이터 행은 다음 코드로 추가한다.

```python
for row in rows:
    cells = table.add_row().cells
    for index, value in enumerate(row):
        set_cell_text(cells[index], value, size=font_size, align_center=True)
```

`rows`는 리스트 안에 리스트가 들어 있는 구조이다.

```python
[
    ["1", "First", "8", "20.38"],
    ["2", "Business", "11", "21.73"],
]
```

이런 구조를 이중 리스트라고 생각하면 된다.

## 보고서 섹션을 만드는 함수들

### `add_title_page()`

제목 페이지를 만든다.

```python
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("운영체제 (Operating Systems)\nTerm Project 최종 보고서")
set_run_font(run, size=20, bold=True)
```

제목 문단을 만들고 가운데 정렬한다. `\n`은 줄바꿈 문자이다.

팀 정보는 `add_table()`로 표를 만든다.

```python
add_table(
    doc,
    ["항목", "내용"],
    [
        ["팀 명", TEAM_NAME],
        ["팀 원", f"{MEMBER_NAME} / {MEMBER_ID}"],
        ["", ""],
        ["", ""],
    ],
    font_size=10,
)
```

마지막에는 다음 페이지로 넘긴다.

```python
doc.add_page_break()
```

### `add_toc()`

목차를 수동으로 만든다.

```python
toc_items = [
    "1. 설계 개요",
    "  1.1 큐 아키텍처 설계",
    ...
]
for item in toc_items:
    add_paragraph(doc, item)
```

이 목차는 Word의 자동 목차 기능이 아니라 문자열 리스트를 문단으로 넣는 방식이다.

### `add_design_sections()`

보고서의 `1. 설계 개요`를 만든다.

포함되는 내용은 다음과 같다.

| 하위 섹션 | 만드는 내용 |
|---|---|
| `1.1 큐 아키텍처 설계` | First/Business/Economy 큐 구조 설명 |
| `1.2 알고리즘 조합 및 근거` | MLQ, Priority, HRRN/Aging, SJF, FCFS 조합 설명 |
| `1.3 카운터 배정 전략` | C1~C5 카운터 역할 설명 |

이 함수는 `add_paragraph()`, `add_code_block()`, `add_table()`을 조합해서 긴 설명 문단과 표를 만든다.

### `add_implementation_sections()`

보고서의 `2. 구현`을 만든다.

포함되는 내용은 다음과 같다.

| 하위 섹션 | 만드는 내용 |
|---|---|
| `2.1 시스템 구조` | `input.txt`부터 `CSV / Log / Graph` 출력까지의 구조 |
| `2.2 핵심 모듈 설명` | `SimulationEngine`, `SchedulerStrategy` 설명 |
| `2.3 실행 방법` | `scheduler.py` 실행 명령어와 출력 파일 표 |

명령어도 Word 문서 안에 코드 블록처럼 들어간다.

```python
add_code_block(
    doc,
    """
cd C:\\OS_WORKSPACE
python scheduler.py input.txt --scheduler all
    """,
)
```

문자열 안의 `\\`는 백슬래시 문자 하나를 표현하기 위한 이스케이프이다.

### `add_results_sections()`

보고서의 `3. 시뮬레이션 결과`를 만든다. 이 함수부터 실제 `output` CSV 파일을 읽는다.

```python
passengers = read_csv(OUTPUT_DIR / "passenger_results.csv")
class_summary = read_csv(OUTPUT_DIR / "class_summary.csv")
counter_summary = read_csv(OUTPUT_DIR / "counter_summary.csv")
```

`passenger_results.csv`는 승객별 결과 표로 들어간다.

```python
rows = [
    [
        row["passenger_id"],
        row["class"],
        row["class_name"],
        row["arrival_time"],
        row["service_time"],
        row["service_start_time"],
        row["completion_time"],
        row["turnaround_time"],
        row["assigned_counter_id"],
    ]
    for row in passengers
]
```

이 코드는 리스트 컴프리헨션이다. `passengers`의 각 딕셔너리에서 필요한 컬럼만 꺼내 표에 넣을 2차원 리스트를 만든다.

`row["passenger_id"]`처럼 딕셔너리에서 값을 꺼낸다. 키 이름은 CSV 헤더와 같아야 한다.

### `add_comparison_sections()`

보고서의 `4. Baseline 비교 분석`을 만든다.

```python
att_comparison = read_csv(OUTPUT_DIR / "att_comparison.csv")
```

`att_comparison.csv`를 읽어서 스케줄러별 ATT 표를 만든다.

그래프 파일은 존재할 때만 넣는다.

```python
graph_path = OUTPUT_DIR / "att_comparison.png"
if graph_path.exists():
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(graph_path), width=Inches(5.8))
```

`Path.exists()`는 파일이 실제로 존재하는지 확인한다. `run.add_picture()`가 `python-docx`로 Word 문서에 이미지를 넣는 핵심 코드이다.

### `add_tradeoff_section()`

보고서의 `5. Trade-off 분석 및 한계`를 만든다.

```python
scheduler_class_files = {
    "FCFS": OUTPUT_DIR / "fcfs_class_summary.csv",
    "Priority": OUTPUT_DIR / "priority_class_summary.csv",
    "SJF": OUTPUT_DIR / "sjf_class_summary.csv",
    "Ours": OUTPUT_DIR / "ours_class_summary.csv",
}
```

이 부분은 딕셔너리이다. 왼쪽 키는 보고서에 표시할 스케줄러 이름이고, 오른쪽 값은 읽을 CSV 파일 경로이다.

```python
for scheduler_name, path in scheduler_class_files.items():
    summary = {row["class_name"]: row["average_turnaround_time"] for row in read_csv(path)}
```

`items()`는 딕셔너리의 키와 값을 함께 꺼낸다. `summary`는 다시 딕셔너리 컴프리헨션으로 만들어진다.

예를 들어 `summary`는 다음처럼 된다.

```python
{
    "First": "20.38",
    "Business": "21.73",
    "Economy": "17.97",
}
```

### `add_remaining_sections()`

보고서의 `6. 역할 분담 및 기여도`, `7. 생성형 AI 활용 경험`, `8. 결론`을 만든다.

이 함수는 외부 CSV를 읽기보다는 정해진 문단과 표를 Word 문서에 직접 추가한다.

## `main()` 함수

```python
def main() -> None:
    template = find_template()
    doc = Document(str(template)) if template else Document()
    clear_document_body(doc)
    set_default_styles(doc)
```

`main()`은 전체 보고서 생성을 지휘하는 함수이다.

템플릿이 있으면 `Document(str(template))`로 템플릿을 열고, 템플릿이 없으면 `Document()`로 빈 문서를 만든다.

그 다음 보고서 섹션 함수들을 순서대로 호출한다.

```python
add_title_page(doc)
add_toc(doc)
add_design_sections(doc)
add_implementation_sections(doc)
add_results_sections(doc)
add_comparison_sections(doc)
add_tradeoff_section(doc)
add_remaining_sections(doc)
```

이 순서가 최종 Word 보고서의 목차 순서이다.

마지막 저장 부분은 예외 처리를 사용한다.

```python
try:
    doc.save(REPORT_PATH)
    print(REPORT_PATH)
except PermissionError:
    doc.save(REVIEWED_REPORT_PATH)
    print(REVIEWED_REPORT_PATH)
```

`try` 블록 안의 코드가 정상 실행되면 `운영체제최종보고서_작성본.docx`로 저장된다.

만약 Word에서 해당 파일을 열어 둔 상태라면 저장 권한 오류인 `PermissionError`가 날 수 있다. 이때 `except PermissionError` 블록이 실행되어 `운영체제최종보고서_작성본_검토수정.docx`로 대신 저장한다.

파일 맨 아래에는 다음 코드가 있다.

```python
if __name__ == "__main__":
    main()
```

이 코드는 이 파일을 직접 실행했을 때만 `main()`을 실행한다. 다른 파일에서 `import generate_final_report`로 가져올 때는 자동으로 보고서가 생성되지 않는다.

## `python-docx` 사용 방식 요약

| 목적 | 사용하는 코드 |
|---|---|
| 새 문서 만들기 | `Document()` |
| 템플릿 열기 | `Document(str(template))` |
| 문단 추가 | `doc.add_paragraph()` |
| 제목 추가 | `doc.add_heading(level=level)` |
| 글자 조각 추가 | `paragraph.add_run(text)` |
| 표 추가 | `doc.add_table(rows=1, cols=len(headers))` |
| 페이지 넘김 | `doc.add_page_break()` |
| 이미지 추가 | `run.add_picture(str(graph_path), width=Inches(5.8))` |
| 문서 저장 | `doc.save(REPORT_PATH)` |

## 초보자가 기억할 핵심 연결

`generate_final_report.py`는 보고서를 예쁘게 만드는 파일이다.

`input.txt`를 직접 읽지 않는다. `input.txt`는 `scheduler.py`가 읽고, 그 결과가 `output/*.csv`, `output/*.png`, `output/*.txt`로 저장된다.

`generate_final_report.py`는 그중 필요한 CSV와 PNG만 읽어서 `.docx`에 표와 그림으로 넣는다.
