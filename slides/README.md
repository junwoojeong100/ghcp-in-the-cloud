# 발표 슬라이드

라이브 데모 여섯 개를 시연하면서 넘기는 한국어 발표 자료입니다. PPTX와 진행 대본은 모두 `build_deck.py` 하나가 같은 데이터로 만들기 때문에 서로 어긋나지 않습니다.

| 파일 | 설명 |
|---|---|
| [`demo-presentation-ko.pptx`](demo-presentation-ko.pptx) | 16:9, 31장. 모든 슬라이드에 한국어 발표자 노트(말할 내용, 시연 큐, 예상 시간)가 들어 있습니다. |
| [`demo-presentation-ko.md`](demo-presentation-ko.md) | 슬라이드별 화면 구성, 발표 대본, 시간표. 자동 생성 파일이므로 직접 고치지 않습니다. |
| [`build_deck.py`](build_deck.py) | 위 두 파일을 만드는 유일한 원본입니다. |
| [`requirements.txt`](requirements.txt) | 생성에만 필요한 `python-pptx` 고정 버전입니다. 데모 앱과는 무관합니다. |

## 다시 만들기

저장소 루트에서 실행합니다. 같은 입력이면 항상 같은 파일이 나옵니다.

```bash
pip install -r slides/requirements.txt
python slides/build_deck.py
```

스크립트는 끝에 슬라이드 수, 사용한 글자 크기, 줄바꿈이 넘칠 것 같은 곳(`layout warning`), 오류(`ERROR`)를 출력합니다. 노트가 빠졌거나 도형이 슬라이드 밖으로 나가면 0이 아닌 종료 코드로 끝납니다.

## 미리 보기

PowerPoint에서 열어 보는 것이 가장 정확합니다. 터미널에서 빠르게 확인하려면 LibreOffice와 poppler를 씁니다. 결과물은 저장소 밖 폴더에 두세요.

```bash
OUT=$HOME/deck-render && mkdir -p "$OUT"
soffice --headless --convert-to pdf --outdir "$OUT" slides/demo-presentation-ko.pptx
pdftoppm -r 80 -png "$OUT/demo-presentation-ko.pdf" "$OUT/s"
```

글꼴은 Segoe UI, Malgun Gothic, Consolas를 지정했습니다. 이 글꼴이 없는 환경에서는 대체 글꼴로 보여 줄바꿈이 조금 다를 수 있습니다.

## 슬라이드와 데모의 대응

| 슬라이드 | 내용 |
|---|---|
| 1–5 | 오프닝: 표지, 오늘의 여정(Full·Lite), 전체 그림, 독립 시연 구조, 샘플 앱 |
| 6–8 | 데모 1 GitHub Copilot |
| 9–11 | 데모 2 GitHub Repo |
| 12–14 | 데모 3 GitHub Actions |
| 15–17 | 데모 4 Microsoft Foundry |
| 18–20 | 데모 5 Azure Container Apps |
| 21–23 | 데모 6 AKS |
| 24–28 | 정리: 선택 가이드, End-to-end, 체크리스트, 서비스별 요약, 시작하기·Q&A |
| 29–31 | 부록: 사전 준비, 트러블슈팅 Top 5, 참고 링크 |

데모마다 세 장입니다. 첫 장은 가치(이점 카드), 둘째 장은 시연 흐름(단계별 명령과 성공 기준, Lite 표시), 셋째 장은 핵심 코드와 설명 상자입니다. 단계별 명령과 화면은 [`demos/`](../demos/)의 문서를 따르고, 진행 순서와 시간은 [`DEMO_GUIDE_KO.md`](../DEMO_GUIDE_KO.md)를 따릅니다.

시간은 Full이 데모 여섯 개 합계 약 42분, Lite가 Copilot → Actions → Foundry → Container Apps 약 15분입니다. 오프닝과 마무리에 드는 시간은 별도이며, 슬라이드별 시간표는 [`demo-presentation-ko.md`](demo-presentation-ko.md)의 "진행 시간"에 있습니다.

## 내용 고치기

1. `build_deck.py` 위쪽의 데이터를 고칩니다. 데모별 내용은 `DEMOS`, 나머지 슬라이드는 `FIXED`에 있습니다.
2. 데모 한 개에는 이점 카드, 시연 단계(제목, 시간, 명령 또는 클릭, 성공 기준, Lite 여부), 코드 조각과 설명 상자, 발표자 노트가 있습니다.
3. 노트는 데모의 `notes` 아래에 슬라이드별(`value`, `flow`, `code`)로 있고, 각각 `say`(말할 내용), `cue`(시연 큐), `time`(`[예상 시간] 약 N분` 형식)으로 씁니다. 데모 합계와 Full·Lite 시간표는 `DEMOS`의 `minutes`와 `lite_min`에서 계산합니다.
4. `python slides/build_deck.py`를 다시 실행하고 `layout warning`이 없는지 확인합니다.

지켜야 할 규칙은 다음과 같습니다.

- 본문은 한국어, 제품 이름과 명령은 영어로 씁니다. 이모지는 쓰지 않습니다.
- 가격, 벤치마크 수치, SLA, 확인하지 못한 주소는 넣지 않습니다.
- 명령, 스크립트 이름, 변수, 역할 이름은 `demos/`와 `scripts/`의 실제 내용과 맞춥니다. 앱이나 스크립트가 바뀌면 슬라이드도 함께 고칩니다.
