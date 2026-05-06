# report_utils.py PNG 그래프 생성 코드 설명

## 파일의 역할

이 문서는 `report_utils.py` 중 `att_comparison.png` 그래프 생성 코드를 초보자 관점에서 설명한다.

그래프 생성의 시작점은 공개 함수 `write_att_comparison_png()`다.

```python
def write_att_comparison_png(
    scheduler_results_or_comparison: Mapping[str, Any] | Iterable[Any],
    output_dir: str | Path = "output",
    our_scheduler_name: str | None = None,
) -> Path:
    output_path = ensure_output_dir(output_dir) / "att_comparison.png"
    rows = _normalise_att_comparison(scheduler_results_or_comparison, our_scheduler_name)

    try:
        _write_att_chart_with_matplotlib(rows, output_path)
    except ImportError:
        _write_att_chart_with_builtin_png(rows, output_path)

    return output_path
```

이 함수는 입력 데이터를 스케줄러별 ATT 비교 행으로 정리한 뒤, PNG 막대그래프를 저장한다.

## 주요 출력 파일

| 파일 | 내용 |
| --- | --- |
| `output/att_comparison.png` | 스케줄러별 ATT 막대그래프 |

그래프의 x축은 스케줄러 이름이고, y축은 ATT다. ATT가 낮을수록 승객 평균 처리 완료 시간이 짧다는 뜻이다.

## 코드 설명

### 전체 흐름

```text
scheduler_results_or_comparison
-> _normalise_att_comparison()
-> [{"scheduler_name": ..., "ATT": ..., "improvement_rate": ...}, ...]
-> matplotlib 사용 시도
-> 성공: _write_att_chart_with_matplotlib()
-> ImportError: _write_att_chart_with_builtin_png()
-> output/att_comparison.png 저장
```

### 입력 데이터 정리

PNG 생성 함수는 CSV와 같은 ATT 비교 데이터를 사용한다.

```python
rows = _normalise_att_comparison(scheduler_results_or_comparison, our_scheduler_name)
```

`rows`는 최종적으로 다음과 같은 목록이 된다.

```python
[
    {"scheduler_name": "fcfs", "ATT": 19.52, "improvement_rate": 1.74},
    {"scheduler_name": "priority", "ATT": 22.50, "improvement_rate": 14.76},
    {"scheduler_name": "sjf", "ATT": 14.90, "improvement_rate": -28.72},
    {"scheduler_name": "ours", "ATT": 19.18, "improvement_rate": 0.0},
]
```

현재 `scheduler.py`는 다음처럼 호출한다.

```python
write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
```

여기서 `results`는 대략 이런 딕셔너리다.

```python
{
    "fcfs": SimulationResult(...),
    "priority": SimulationResult(...),
    "sjf": SimulationResult(...),
    "ours": SimulationResult(...),
}
```

`_normalise_att_comparison()`은 이 딕셔너리를 보고 스케줄러 이름과 각 결과의 ATT를 뽑아낸다.

## CSV 저장 함수 설명

PNG 문서의 중심은 그래프 생성이지만, 같은 데이터는 CSV 저장에도 사용된다.

`write_att_comparison_csv()`는 `_normalise_att_comparison()`으로 만든 `rows`를 `att_comparison.csv`에 저장한다.

```python
rows = _normalise_att_comparison(scheduler_results_or_comparison, our_scheduler_name)
_write_dict_csv(output_path, ATT_COMPARISON_HEADERS, rows)
```

즉 CSV와 PNG의 차이는 마지막 출력 방식이다.

| 출력 | 마지막 처리 |
| --- | --- |
| CSV | `csv.DictWriter`로 텍스트 행 저장 |
| PNG | matplotlib 또는 직접 픽셀 그리기로 이미지 저장 |

## matplotlib 그래프 생성 설명

### matplotlib 함수 구조

```python
def _write_att_chart_with_matplotlib(rows, output_path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
```

`import matplotlib`이 함수 안에 있다. 파일을 import하는 순간 matplotlib을 요구하지 않고, 실제 PNG를 만들 때만 필요하게 하려는 구조다.

`matplotlib.use("Agg")`는 화면 창을 띄우지 않고 이미지 파일을 만들기 위한 설정이다. 서버나 자동 채점 환경처럼 GUI가 없는 곳에서도 저장할 수 있다.

### 그래프에 쓸 값 만들기

```python
names = [str(row["scheduler_name"]) for row in rows]
atts = [_number(row["ATT"]) for row in rows]
```

`names`는 x축 라벨이다.

```python
["fcfs", "priority", "sjf", "ours"]
```

`atts`는 막대 높이다.

```python
[19.52, 22.50, 14.90, 19.18]
```

`_number()`를 쓰는 이유는 ATT가 문자열 `"19.52"`로 들어와도 숫자 `19.52`로 바꾸기 위해서다.

### figure와 axes

```python
figure_width = max(7, len(rows) * 1.6)
fig, ax = plt.subplots(figsize=(figure_width, 4.8))
```

`fig`는 전체 그림 종이고, `ax`는 그 안의 실제 그래프 영역이라고 생각하면 된다.

`figure_width = max(7, len(rows) * 1.6)`은 스케줄러 개수가 늘어나면 그림 폭도 늘리려는 계산이다.

### 막대그래프 그리기

```python
colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]
bars = ax.bar(names, atts, color=[colors[index % len(colors)] for index in range(len(rows))])
```

`ax.bar(names, atts, ...)`가 막대그래프를 그린다.

색상은 스케줄러 순서에 따라 반복된다.

```python
colors[index % len(colors)]
```

`%`는 나머지 연산자다. 색상 수보다 막대 수가 많아도 색상을 처음부터 다시 반복할 수 있다.

### 축과 제목 설정

```python
ax.set_xlabel("Scheduler")
ax.set_ylabel("ATT")
ax.set_title("Average Turnaround Time Comparison")
ax.grid(axis="y", linestyle="--", alpha=0.35)
ax.set_axisbelow(True)
```

이 코드는 x축 이름, y축 이름, 제목, y축 grid를 설정한다.

`ax.set_axisbelow(True)`는 grid 선이 막대 뒤쪽에 깔리게 한다.

### y축 범위

```python
y_max = max(atts, default=0)
ax.set_ylim(0, y_max * 1.18 if y_max > 0 else 1)
```

가장 높은 ATT보다 18% 정도 여유를 둔다. 그래야 막대 위에 숫자 텍스트를 쓸 공간이 생긴다.

### 막대 위 숫자 표시

```python
for bar, att in zip(bars, atts):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        _format_metric(att),
        ha="center",
        va="bottom",
        fontsize=9,
    )
```

`zip(bars, atts)`는 막대 객체와 ATT 값을 하나씩 짝지어 반복한다.

`ax.text()`는 막대 위에 숫자를 적는다.

| 인자 | 의미 |
| --- | --- |
| `bar.get_x() + bar.get_width() / 2` | 막대의 가운데 x 위치 |
| `bar.get_height()` | 막대 꼭대기 y 위치 |
| `_format_metric(att)` | 표시할 문자열 |
| `ha="center"` | 가로 가운데 정렬 |
| `va="bottom"` | 텍스트 아래쪽을 기준점에 맞춤 |

### 저장과 정리

```python
fig.tight_layout()
fig.savefig(output_path, dpi=160)
plt.close(fig)
```

`tight_layout()`은 제목, 축 라벨, tick label이 잘리지 않도록 여백을 정리한다.

`savefig()`가 실제 PNG 파일을 저장한다.

`plt.close(fig)`는 그림 객체를 닫아 메모리를 정리한다.

## 내장 PNG 생성 fallback 설명

### fallback이 필요한 이유

matplotlib이 설치되어 있지 않은 환경에서도 과제 결과 이미지가 생성되도록 하기 위해 fallback 코드가 있다.

```python
try:
    _write_att_chart_with_matplotlib(rows, output_path)
except ImportError:
    _write_att_chart_with_builtin_png(rows, output_path)
```

여기서 잡는 에러는 `ImportError`다. 즉 matplotlib을 import할 수 없을 때만 fallback으로 간다. matplotlib은 설치되어 있지만 다른 런타임 에러가 나면 이 except에 잡히지 않는다.

### 기본 값 준비

```python
names = [str(row["scheduler_name"]) for row in rows]
atts = [_number(row["ATT"]) for row in rows]

width = max(760, 140 + max(1, len(rows)) * 160)
height = 520
canvas = bytearray([255] * width * height * 3)
```

`width`는 막대 수에 따라 커진다. 최소 너비는 760이다.

`height`는 520으로 고정이다.

`canvas`는 직접 그림을 그릴 픽셀 배열이다.

RGB 이미지는 한 픽셀에 3개 값이 필요하다.

```text
R, G, B
```

흰색은 `(255, 255, 255)`다. 그래서 `[255] * width * height * 3`으로 전체를 흰색으로 채운다.

`bytearray`는 값을 바꿀 수 있는 바이트 배열이다. 픽셀 색을 계속 수정해야 하므로 `bytes`가 아니라 `bytearray`를 쓴다.

### 그래프 영역 계산

```python
left = 82
right = 42
top = 66
bottom = 395
plot_width = width - left - right
plot_height = bottom - top
max_att = max(atts, default=0)
y_limit = max_att * 1.18 if max_att > 0 else 1
```

전체 이미지 안에서 실제 그래프가 그려질 영역을 계산한다.

| 변수 | 의미 |
| --- | --- |
| `left` | 왼쪽 여백 |
| `right` | 오른쪽 여백 |
| `top` | 위쪽 여백 |
| `bottom` | x축이 있는 y 위치 |
| `plot_width` | 그래프 실제 폭 |
| `plot_height` | 그래프 실제 높이 |
| `y_limit` | y축 최대값 |

좌표계에서 주의할 점이 있다. 일반 수학 그래프는 y가 위로 갈수록 커지지만, 이미지 픽셀 좌표는 y가 아래로 갈수록 커진다.

그래서 값이 클수록 `bar_top`은 더 작은 y 좌표가 된다.

```python
bar_height = int((max(0.0, att) / y_limit) * plot_height)
bar_top = bottom - bar_height
```

### 제목 그리기

```python
_draw_text_centered(
    canvas,
    width,
    height,
    width // 2,
    24,
    "Average Turnaround Time Comparison",
    black,
    scale=2,
)
```

`_draw_text_centered()`는 텍스트 폭을 계산해서 가운데 정렬로 글자를 그린다.

`scale=2`는 글자를 2배 크기로 그리겠다는 뜻이다.

### y축 grid와 숫자

```python
tick_count = 5
for tick in range(tick_count + 1):
    value = y_limit * tick / tick_count
    y = bottom - int((value / y_limit) * plot_height)
    _draw_line(canvas, width, height, left, y, width - right, y, grey)
    _draw_text_right(..., _format_metric(value), ...)
```

tick은 y축 눈금이다. `tick_count = 5`이면 0부터 최대값까지 5등분한다.

`_draw_line()`은 가로 grid 선을 그리고, `_draw_text_right()`는 y축 숫자를 오른쪽 정렬로 쓴다.

### 축 그리기

```python
_draw_line(canvas, width, height, left, top, left, bottom, black)
_draw_line(canvas, width, height, left, bottom, width - right, bottom, black)
_draw_text_centered(canvas, width, height, width // 2, height - 26, "Scheduler", black, scale=1)
_draw_text(canvas, width, height, 18, top + plot_height // 2 - 6, "ATT", black, scale=1)
```

첫 줄은 y축, 둘째 줄은 x축이다. 그 아래에 x축 이름 `Scheduler`, 왼쪽에 y축 이름 `ATT`를 그린다.

### 막대 그리기

```python
group_width = plot_width / len(rows)
for index, (name, att) in enumerate(zip(names, atts)):
    bar_width = min(88, int(group_width * 0.56))
    center_x = int(left + group_width * index + group_width / 2)
    bar_left = center_x - bar_width // 2
    bar_right = center_x + bar_width // 2
    bar_height = int((max(0.0, att) / y_limit) * plot_height)
    bar_top = bottom - bar_height
```

`group_width`는 스케줄러 하나가 차지하는 가로 공간이다.

`center_x`는 해당 막대의 가운데 위치다.

`bar_left`, `bar_right`, `bar_top`, `bottom`이 막대 사각형 좌표가 된다.

```python
_draw_rect(
    canvas,
    width,
    height,
    bar_left,
    bar_top,
    bar_right,
    bottom,
    colors[index % len(colors)],
)
```

`_draw_rect()`로 막대를 채운다.

### 막대 값과 라벨

```python
_draw_text_centered(
    canvas,
    width,
    height,
    center_x,
    max(top + 2, bar_top - 17),
    _format_metric(att),
    black,
    scale=1,
)
```

막대 위에 ATT 숫자를 쓴다.

```python
for line_index, label_line in enumerate(_wrap_label(name, max_chars=14, max_lines=2)):
    _draw_text_centered(
        canvas,
        width,
        height,
        center_x,
        bottom + 12 + line_index * 13,
        label_line,
        black,
        scale=1,
    )
```

스케줄러 이름이 길면 `_wrap_label()`로 최대 두 줄까지 나눠서 그린다.

### 픽셀에 사각형 그리기: _draw_rect

```python
def _draw_rect(canvas, width, height, x0, y0, x1, y1, color):
    x0 = max(0, min(width, x0))
    x1 = max(0, min(width, x1))
    y0 = max(0, min(height, y0))
    y1 = max(0, min(height, y1))
```

먼저 좌표가 이미지 밖으로 나가지 않도록 자른다.

```python
red, green, blue = color
for y in range(y0, y1):
    row_start = y * width * 3
    for x in range(x0, x1):
        index = row_start + x * 3
        canvas[index:index + 3] = bytes((red, green, blue))
```

한 픽셀은 RGB 3바이트다. 특정 픽셀의 시작 위치는 다음 공식으로 계산한다.

```text
index = y * width * 3 + x * 3
```

그리고 `canvas[index:index + 3]`에 `(red, green, blue)`를 넣는다.

### 선 그리기: _draw_line

`_draw_line()`은 수평선과 수직선을 먼저 간단히 처리한다.

```python
if y0 == y1:
    _draw_rect(..., min(x0, x1), y0, max(x0, x1) + 1, y0 + 1, color)
    return
if x0 == x1:
    _draw_rect(..., x0, min(y0, y1), x0 + 1, max(y0, y1) + 1, color)
    return
```

그래프 축과 grid는 대부분 수평선/수직선이기 때문에 이 처리가 많이 쓰인다.

기울어진 선은 Bresenham 방식에 가까운 반복 계산으로 픽셀을 하나씩 찍는다.

### 글자 그리기: FONT_5X7와 _draw_text

파일 아래쪽의 `FONT_5X7`은 글자를 5x7 픽셀 패턴으로 저장한 상수다.

예를 들어 `"A"`는 대략 이런 모양이다.

```text
01110
10001
10001
11111
10001
10001
10001
```

`1`인 위치에 픽셀을 칠하고, `0`인 위치는 비워둔다.

```python
for character in text.upper():
    glyph = FONT_5X7.get(character, FONT_5X7["?"])
```

지원하지 않는 글자는 `?` 패턴으로 대체한다.

### PNG 파일로 저장: _write_png_rgb

```python
def _write_png_rgb(path: Path, width: int, height: int, pixels: bytes | bytearray) -> None:
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        row_start = y * stride
        raw.extend(pixels[row_start:row_start + stride])
```

PNG는 각 행 앞에 filter type 바이트가 들어간다. 여기서는 `raw.append(0)`으로 "필터 없음"을 뜻하는 0을 붙인다.

```python
def chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )
```

PNG 파일은 여러 chunk로 구성된다. 각 chunk는 길이, 타입, 데이터, CRC로 되어 있다.

`struct.pack(">I", len(data))`는 길이 숫자를 PNG가 요구하는 big-endian 4바이트로 바꾼다.

`zlib.crc32(...)`는 데이터가 손상되지 않았는지 확인하는 체크값을 만든다.

```python
png_bytes = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
    + chunk(b"IEND", b"")
)
path.write_bytes(png_bytes)
```

PNG 파일은 정해진 signature로 시작한다. 그 뒤 이미지 정보 `IHDR`, 압축된 픽셀 데이터 `IDAT`, 끝 표시 `IEND`를 붙인다.

마지막 `path.write_bytes(png_bytes)`가 바이너리 파일을 저장한다.

## matplotlib 방식과 fallback 방식의 차이

| 항목 | matplotlib 방식 | fallback 내장 PNG 방식 |
| --- | --- | --- |
| 필요 라이브러리 | `matplotlib` 필요 | 표준 라이브러리만 사용 |
| 그래픽 품질 | 더 좋음 | 단순함 |
| 글꼴 | matplotlib 기본 글꼴 사용 | `FONT_5X7` 픽셀 글꼴 사용 |
| 코드 길이 | 짧음 | 직접 그려야 해서 김 |
| 저장 방식 | `fig.savefig()` | 직접 PNG bytes 생성 |
| 실패 시 동작 | import 성공하면 사용 | matplotlib `ImportError`일 때만 사용 |

## 초보자가 헷갈릴 수 있는 문법

### `try/except ImportError`

```python
try:
    _write_att_chart_with_matplotlib(rows, output_path)
except ImportError:
    _write_att_chart_with_builtin_png(rows, output_path)
```

`try` 안의 코드를 실행하다가 `ImportError`가 나면 `except`로 이동한다.

여기서는 matplotlib이 없을 때 내장 PNG 생성으로 넘어간다.

### 함수 안 import

```python
def _write_att_chart_with_matplotlib(...):
    import matplotlib
```

파일 전체를 import할 때 matplotlib이 없어도 에러가 나지 않게 하려는 구조다. 실제 그래프를 만들 때만 matplotlib을 요구한다.

### list comprehension

```python
names = [str(row["scheduler_name"]) for row in rows]
atts = [_number(row["ATT"]) for row in rows]
```

반복문으로 리스트를 만드는 짧은 문법이다.

### `enumerate`

```python
for index, (name, att) in enumerate(zip(names, atts)):
```

`enumerate()`는 반복하면서 순번도 함께 준다.

```text
0, ("fcfs", 19.52)
1, ("priority", 22.50)
...
```

### `zip`

`zip(names, atts)`는 두 목록을 같은 위치끼리 묶는다.

```text
["fcfs", "ours"]
[19.52, 19.18]
-> ("fcfs", 19.52), ("ours", 19.18)
```

### `bytes`

```python
bytes((red, green, blue))
```

숫자 3개를 변경 불가능한 바이트 데이터로 바꾼다. 픽셀 하나의 RGB 값으로 사용된다.

### `bytearray`

```python
canvas = bytearray([255] * width * height * 3)
```

`bytearray`는 내용을 바꿀 수 있는 바이트 배열이다. 직접 픽셀 색을 수정해야 하므로 fallback 그래프에서는 `bytearray`가 필요하다.

### `struct.pack`

```python
struct.pack(">I", len(data))
```

숫자를 바이너리 파일 규격에 맞는 bytes로 바꾼다. PNG chunk 길이를 기록할 때 사용한다.

### `zlib.compress`

```python
zlib.compress(bytes(raw), level=9)
```

픽셀 데이터를 압축한다. PNG의 `IDAT` chunk에는 압축된 이미지 데이터가 들어간다.

### `path.write_bytes`

```python
path.write_bytes(png_bytes)
```

텍스트가 아니라 bytes를 그대로 파일에 쓴다. PNG는 텍스트 파일이 아니라 바이너리 파일이므로 `write_text()`가 아니라 `write_bytes()`를 사용한다.

## 다른 파일과의 관계

`scheduler.py`는 `report_utils.py`에서 PNG 생성 함수만 import한다.

```python
from report_utils import write_att_comparison_png
```

시뮬레이션 결과 저장 단계에서는 다음처럼 호출한다.

```python
write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
```

이때 `results` 안의 값은 `models.py`의 `SimulationResult` 객체다. `SimulationResult`에는 `average_turnaround_time` property가 있다.

`report_utils.py`의 `_att_from_result()`는 이 property를 찾아 ATT로 사용한다.

```python
att_value = _get(result, "ATT", "att", "average_turnaround_time", default=None)
if att_value is not None:
    return _number(att_value)
```

즉 연결 흐름은 다음과 같다.

```text
scheduler.py
-> SimulationEngine.run()
-> SimulationResult 생성
-> results 딕셔너리에 저장
-> write_att_comparison_png(results, output_dir, our_scheduler_name="ours")
-> report_utils.py가 ATT 추출
-> matplotlib 또는 fallback으로 att_comparison.png 생성
```

CSV 파일은 현재 `scheduler.py`가 자체 helper로 생성한다. 하지만 `report_utils.py`에도 CSV 생성 함수와 `generate_reports()`가 있으므로, 나중에 `scheduler.py`를 단순화하고 싶다면 CSV 저장도 이 유틸리티로 모을 수 있다.

