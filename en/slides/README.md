# Presentation slides

An English deck to flip through while you run the six live demos. The PPTX and the speaker script are both generated from the same data by `build_deck.py`, so they cannot drift apart. The Korean edition of the deck is in [`slides/`](../../slides/).

| File | Description |
|---|---|
| [`demo-presentation-en.pptx`](demo-presentation-en.pptx) | 16:9, 37 slides. Every slide has English speaker notes (what to say, demo cues, estimated time). |
| [`demo-presentation-en.md`](demo-presentation-en.md) | Per-slide layout, speaker script and timetable. Generated file, so do not edit it by hand. |
| [`build_deck.py`](build_deck.py) | The only source for the two files above. |
| [`VIDEO_GUIDE.md`](VIDEO_GUIDE.md) | How to record the six demos and insert the videos into the PPTX. |
| [`slides/requirements.txt`](../../slides/requirements.txt) | The pinned `python-pptx` version, shared with the Korean deck and needed only for generation. Unrelated to the demo app. |

The recorded English demo (a 45-slide deck with 32 videos embedded, and the full video) is a different deck. Those files are assets of a release; see [Slides and guides](../README.md#slides-and-guides).

## Rebuild

Run from the repository root. The same data and the same video files always produce the same PPTX and script.

```bash
pip install -r slides/requirements.txt
python en/slides/build_deck.py
```

At the end the script prints the slide count, the font sizes used, places where a line wrap may overflow (`layout warning`) and errors (`ERROR`). It exits with a non-zero code if notes are missing, a shape leaves the slide, or any Hangul text is found.

## Preview

Opening the deck in PowerPoint is the most accurate way. For a quick look from the terminal, use LibreOffice and poppler. Keep the output outside the repository.

```bash
OUT=$HOME/deck-render && mkdir -p "$OUT"
soffice --headless --convert-to pdf --outdir "$OUT" en/slides/demo-presentation-en.pptx
pdftoppm -r 80 -png "$OUT/demo-presentation-en.pdf" "$OUT/s"
```

The deck specifies Segoe UI and Consolas. In environments without these fonts a substitute font is used, so line breaks may differ slightly.

## Slides and demos

| Slides | Content |
|---|---|
| 1–5 | Opening: cover, today's journey (Full and Lite), big picture, standalone structure, sample app |
| 6–9 | Demo 1 GitHub Copilot: value, demo flow, video, key code |
| 10–13 | Demo 2 GitHub Repo: value, demo flow, video, key code |
| 14–17 | Demo 3 GitHub Actions: value, demo flow, video, key code |
| 18–21 | Demo 4 Microsoft Foundry: value, demo flow, video, key code |
| 22–25 | Demo 5 Azure Container Apps: value, demo flow, video, key code |
| 26–29 | Demo 6 AKS: value, demo flow, video, key code |
| 30–34 | Wrap-up: selection guide, end-to-end, checklist, per-service summary, get started and Q&A |
| 35–37 | Appendix: pre-demo prep, troubleshooting top 5, reference links |

Each demo has four slides. The first is the value slide (benefit cards), the second is the demo flow (commands and success criteria for each step, with `Lite` markers), the third is the recording of that demo, and the fourth is the key code with callouts. If a real recording exists at `en/slides/videos/{copilot,repo,actions,foundry,aca,aks}.mp4`, that video is inserted into the PPTX. If the file is missing, the slide shows where to put the recording. Follow [`VIDEO_GUIDE.md`](VIDEO_GUIDE.md) for the recording. The commands and success criteria for each step follow the guides in [`demos/`](../demos/), and the running order and timing follow [`DEMO_GUIDE.md`](../DEMO_GUIDE.md).

Timing: Full is about 42 minutes of demos for all six, and Lite is about 15 minutes (Copilot → Actions → Foundry → Container Apps). The opening and wrap-up take extra time; the per-slide timetable is in "Timing" in [`demo-presentation-en.md`](demo-presentation-en.md).

## Editing the content

1. Edit the data at the top of `build_deck.py`. Per-demo content is in `DEMOS` and the remaining slides are in `FIXED`.
2. A demo has benefit cards, demo steps (title, time, command or click, success criterion, Lite flag), a code excerpt with callouts, and speaker notes.
3. Notes live under each demo's `notes` per slide (`value`, `flow`, `code`). The notes of the video slide are generated automatically, depending on whether the video file exists. Notes are written as `say` (what to say), `cue` (demo cues) and `time` (format `[Estimated time] about N min`). The demo totals and the Full/Lite timetable are computed from `minutes` and `lite_min` in `DEMOS`.
4. To insert a real video, put the file at `en/slides/videos/<demo key>.mp4` and run `python en/slides/build_deck.py`. If there is no video, the placeholder slide stays.
5. After the build, make sure there is no `layout warning`, and check the video playback in PowerPoint.

Rules to follow:

- Write the body in English; keep product names and commands as they are. No emoji.
- Do not add prices, benchmark numbers, SLAs or unverified URLs.
- Keep commands, script names, variables and role names in line with the actual contents of `demos/` and `scripts/`. When the app or the scripts change, update the slides too, in both languages: the Korean deck in `slides/` and this English deck.
