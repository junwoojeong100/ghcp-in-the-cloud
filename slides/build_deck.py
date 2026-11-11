#!/usr/bin/env python3
"""Build the Korean presenter deck and its speaker-script outline.

    python slides/build_deck.py

Outputs (next to this file):
  demo-presentation-ko.pptx   16:9 deck, native shapes only, speaker notes on every slide
  demo-presentation-ko.md     outline + full Korean speaker script, generated from the same data

Edit the DATA section (DEMOS, FIXED slides, notes). The render helpers turn it into
slides and the markdown, so deck and script cannot drift apart. Output is deterministic.
"""
from __future__ import annotations

import math
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement as _OxmlElement
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
PPTX_PATH = HERE / "demo-presentation-ko.pptx"
MD_PATH = HERE / "demo-presentation-ko.md"
VIDEO_DIR = HERE / "videos"


def OxmlElement(tag: str, attrs: dict | None = None):
    """python-pptx's OxmlElement without attributes, plus an attrs convenience."""
    el = _OxmlElement(tag)
    for key, value in (attrs or {}).items():
        el.set(key, value)
    return el


DECK_NAME = "GitHub Copilot in the Cloud · 데모 키트"
REPO = "github.com/junwoojeong100/ghcp-in-the-cloud"

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
SLIDE_W, SLIDE_H = 13.333, 7.5
MX = 0.6  # left/right margin
CW = SLIDE_W - 2 * MX  # content width
BODY_TOP, BODY_BOTTOM = 1.62, 6.82

LATIN, EA, MONO = "Segoe UI", "Malgun Gothic", "Consolas"

P = {
    "ink": "111827", "ink2": "374151", "muted": "5B6472",
    "bg": "FFFFFF", "soft": "F3F4F6", "line": "D1D5DB", "line2": "E5E7EB",
    "dark": "0B1220", "dark2": "172033", "dark_line": "2B3753", "dark_text": "E5E7EB", "dark_muted": "A3ADBD",
    "ok": "15803D", "ok_tint": "E8F5EC", "warn": "B45309", "warn_tint": "FEF3C7",
    "code_bg": "0F172A", "code_text": "E2E8F0", "code_dim": "8FA1B8", "code_str": "FCD34D", "code_key": "7DD3FC",
    "identity": "D97706",
}

# One accent family per service: GitHub = purple/graphite, Foundry = violet-blue, ACA = azure, AKS = teal.
THEME = {
    "copilot": dict(accent="8250DF", text="6639BA", panel="2A1A5E", on_dark="B9A0F7", tint="F4EFFD"),
    "repo": dict(accent="57606A", text="3B424B", panel="22272E", on_dark="BAC2CC", tint="F0F2F4"),
    "actions": dict(accent="6F42C1", text="5A32A3", panel="2D2457", on_dark="AFA3F3", tint="F3F0FB"),
    "foundry": dict(accent="4F46E5", text="4338CA", panel="1E1B4B", on_dark="A9B8FF", tint="EEF0FF"),
    "aca": dict(accent="0078D4", text="0B63B8", panel="0B2A4A", on_dark="86C5F7", tint="EAF4FD"),
    "aks": dict(accent="00897B", text="00695C", panel="0B3836", on_dark="5EEAD4", tint="E6F6F3"),
    "neutral": dict(accent="475569", text="334155", panel="0B1220", on_dark="CBD5E1", tint="F1F5F9"),
}

ALIGN = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}
ANCHOR = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}

WARNINGS: list[str] = []
CUR = {"n": 0, "title": ""}


# ---------------------------------------------------------------------------
# Text metrics (conservative estimate used to size boxes and flag overflow)
# ---------------------------------------------------------------------------
def char_w(ch: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Approximate advance width in inches. Deliberately wide so real PowerPoint never overflows."""
    em = size / 72.0
    o = ord(ch)
    if mono:
        return 0.60 * em if o < 0x2E80 else 1.0 * em
    if (0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F or 0x4E00 <= o <= 0x9FFF
            or 0xFF00 <= o <= 0xFFEF or 0x2190 <= o <= 0x21FF or 0x2460 <= o <= 0x27BF):
        w = 1.0
    elif ch == " ":
        w = 0.30
    elif ch in "il|!.,:;'`":
        w = 0.32
    elif ch in "mwMW":
        w = 0.88
    elif ch in "·—–×≈":
        w = 0.62
    elif ch.isupper() or ch.isdigit():
        w = 0.64
    else:
        w = 0.57
    return w * em * (1.06 if bold else 1.0)


def text_w(s: str, size: float, bold: bool = False, mono: bool = False) -> float:
    return sum(char_w(c, size, mono, bold) for c in s)


def est_lines(text: str, size: float, width: float, bold: bool = False, mono: bool = False) -> int:
    if width <= 0.05:
        return 99
    lines, cur = 1, 0.0
    space = char_w(" ", size, mono, bold)
    for word in text.split(" "):
        w = text_w(word, size, bold, mono)
        extra = max(0, math.ceil(w / width) - 1) if w > width else 0
        if cur == 0.0:
            lines += extra
            cur = w - extra * width if extra else w
        elif cur + space + w <= width:
            cur += space + w
        else:
            lines += 1 + extra
            cur = w - extra * width if extra else w
    return lines


LINE_H = 1.36  # font line height / font size (Malgun Gothic and Noto CJK are tall)
LINE_H_MONO = 1.24  # Consolas and DejaVu Sans Mono are about 1.17


def plain(text: str) -> str:
    return text.replace("`", "")


# ---------------------------------------------------------------------------
# Low-level XML helpers
# ---------------------------------------------------------------------------
def rgb(hexstr: str) -> RGBColor:
    return RGBColor.from_string(hexstr)


_AFTER_FONT = [qn(t) for t in ("a:sym", "a:hlinkClick", "a:hlinkMouseOver", "a:rtl", "a:extLst")]


def set_typefaces(rPr, latin: str, ea: str = EA) -> None:
    """python-pptx exposes only <a:latin>; write latin + east-asian + complex-script faces in schema order."""
    for tag in ("a:latin", "a:ea", "a:cs", "a:sym"):
        for el in rPr.findall(qn(tag)):
            rPr.remove(el)
    anchor = next((c for c in rPr if c.tag in _AFTER_FONT), None)
    for tag, face in (("a:latin", latin), ("a:ea", ea), ("a:cs", latin)):
        el = OxmlElement(tag, attrs={"typeface": face})
        if anchor is not None:
            anchor.addprevious(el)
        else:
            rPr.append(el)


def style_run(run, size: float, color: str, bold: bool = False, mono: bool = False, italic: bool = False,
              spc: int | None = None) -> None:
    f = run.font
    f.size = Pt(size)
    f.bold = bool(bold)
    f.italic = bool(italic)
    f.color.rgb = rgb(color)
    rPr = run._r.get_or_add_rPr()
    rPr.set("lang", "en-US" if mono else "ko-KR")
    rPr.set("altLang", "en-US" if not mono else "ko-KR")
    if spc is not None:
        rPr.set("spc", str(spc))
    set_typefaces(rPr, MONO if mono else LATIN)


def set_bullet(p, char: str = "•", indent: float = 0.27, level: int = 0, color: str | None = None) -> None:
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent * (level + 1)))))
    pPr.set("indent", str(-int(Inches(indent))))
    for tag in ("a:buClr", "a:buSzPct", "a:buFont", "a:buNone", "a:buChar", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    if color:
        clr = OxmlElement("a:buClr")
        clr.append(OxmlElement("a:srgbClr", attrs={"val": color}))
        pPr.append(clr)
    pPr.append(OxmlElement("a:buFont", attrs={"typeface": "Arial"}))
    pPr.append(OxmlElement("a:buChar", attrs={"char": char}))


def set_alt(shape, text: str) -> None:
    shape._element.xpath("./*[1]/p:cNvPr")[0].set("descr", text)


def send_to_back(shape) -> None:
    tree = shape._element.getparent()
    tree.remove(shape._element)
    tree.insert(2, shape._element)


_INLINE = re.compile(r"(`[^`]*`)")


def parse_inline(text: str, code_color: str | None) -> list[tuple[str, dict]]:
    out = []
    for seg in _INLINE.split(text):
        if not seg:
            continue
        if seg.startswith("`") and seg.endswith("`") and len(seg) >= 2:
            opts = {"mono": True}
            if code_color:
                opts["color"] = code_color
            out.append((seg[1:-1], opts))
        else:
            out.append((seg, {}))
    return out


def fill_text(tf, paras, *, size: float = 18, color: str | None = None, bold: bool = False, align: str = "l",
              spacing: float = 1.1, after: float = 0, before: float = 0, anchor: str = "t",
              inset=(0.0, 0.0, 0.0, 0.0), mono: bool = False, code_color: str | None = None,
              width: float | None = None) -> float:
    """Fill a text frame from paragraph specs and return the estimated content height in inches."""
    color = color or P["ink"]
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (Inches(v) for v in inset)
    tf.vertical_anchor = ANCHOR[anchor]
    est = inset[1] + inset[3]
    avail = (width - inset[0] - inset[2]) if width else None
    first = True
    for spec in paras:
        if isinstance(spec, str):
            spec = {"t": spec}
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        sz = spec.get("size", size)
        col = spec.get("color", color)
        b = spec.get("bold", bold)
        is_mono = spec.get("mono", mono)
        sp = spec.get("spacing", spacing)
        p.alignment = ALIGN[spec.get("align", align)]
        p.line_spacing = sp
        p.space_after = Pt(spec.get("after", after))
        p.space_before = Pt(spec.get("before", before))
        indent = 0.0
        if spec.get("bullet"):
            indent = spec.get("indent", 0.27)
            set_bullet(p, spec["bullet"] if isinstance(spec["bullet"], str) else "•", indent,
                       color=spec.get("bullet_color"))
        if spec.get("runs"):
            runs = spec["runs"]
        elif is_mono and not spec.get("inline"):
            runs = [(spec["t"], {})]
        else:
            runs = parse_inline(spec["t"], spec.get("code_color", code_color))
        for text, opts in runs:
            r = p.add_run()
            r.text = text
            style_run(r, opts.get("size", sz), opts.get("color", col), bold=opts.get("bold", b),
                      mono=opts.get("mono", is_mono), italic=opts.get("italic", False), spc=spec.get("spc"))
            if opts.get("link"):
                r.hyperlink.address = opts["link"]
        if avail:
            full = plain("".join(t for t, _ in runs))
            n = est_lines(full, sz, avail - indent, b, is_mono)
            est += n * sz * (LINE_H_MONO if is_mono else LINE_H) * sp / 72.0 + (
                spec.get("after", after) + spec.get("before", before)) / 72.0
    return est


def track(name: str, est: float, h: float, slack: float = 1.0) -> None:
    if est > h * slack + 0.01:
        WARNINGS.append(f"slide {CUR['n']} ({CUR['title'][:24]}): '{name}' needs ~{est:.2f}in but box is {h:.2f}in")


def add_text(slide, x, y, w, h, paras, *, name: str | None = None, alt: str | None = None, **kw):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    est = fill_text(tb.text_frame, paras, width=w, **kw)
    track(name or "text", est, h)
    if alt:
        set_alt(tb, alt)
    return tb


def add_box(slide, x, y, w, h, *, fill: str | None = None, line: str | None = None, line_w: float = 1.0,
            radius: float | None = None, shape=MSO_SHAPE.RECTANGLE, name: str | None = None,
            alt: str | None = None, dash=None, text=None, **text_kw):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if (radius is not None and shape == MSO_SHAPE.RECTANGLE) else shape
    sp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        sp.adjustments[0] = min(0.5, radius / min(w, h))
    if fill:
        sp.fill.solid()
        sp.fill.fore_color.rgb = rgb(fill)
    else:
        sp.fill.background()
    if line:
        sp.line.color.rgb = rgb(line)
        sp.line.width = Pt(line_w)
        if dash:
            sp.line.dash_style = dash
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    if name:
        sp.name = name
    if alt:
        set_alt(sp, alt)
    if text is not None:
        text_kw.setdefault("anchor", "m")
        inset = text_kw.pop("inset", (0.12, 0.06, 0.12, 0.06))
        est = fill_text(sp.text_frame, text, inset=inset, width=w, **text_kw)
        track(name or "box text", est, h)
    else:
        sp.text_frame.text = ""
    return sp


def add_arrow(slide, x1, y1, x2, y2, *, color: str, width: float = 2.25, dash=None, head: bool = True,
              tail: bool = False, name: str | None = None, alt: str | None = None):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if dash:
        c.line.dash_style = dash
    ln = c.line._get_or_add_ln()
    if tail:
        ln.append(OxmlElement("a:headEnd", attrs={"type": "triangle", "w": "med", "len": "med"}))
    if head:
        ln.append(OxmlElement("a:tailEnd", attrs={"type": "triangle", "w": "med", "len": "med"}))
    if name:
        c.name = name
    if alt:
        set_alt(c, alt)
    return c


def add_label(slide, cx, cy, text, *, color: str, fill: str = "FFFFFF", size: float = 14, bold: bool = True,
              name: str | None = None, pad: float = 0.1):
    """Small pill centred on (cx, cy); width follows the text so it never wraps."""
    w = text_w(plain(text), size, bold) + 2 * pad + 0.08
    h = size * LINE_H / 72.0 + 0.08
    return add_box(slide, cx - w / 2, cy - h / 2, w, h, fill=fill, radius=h / 2, name=name or f"Label {plain(text)}",
                   text=[{"t": text, "align": "c"}], size=size, bold=bold, color=color, anchor="m",
                   inset=(pad, 0.02, pad, 0.02))


# ---------------------------------------------------------------------------
# Tables (native PowerPoint tables so presenters can edit them)
# ---------------------------------------------------------------------------
def _cell_border(cell, bottom: str | None, color: str, width_pt: float = 0.75) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        for el in tcPr.findall(qn(tag)):
            tcPr.remove(el)
    els = []
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        if tag == "a:lnB" and bottom:
            ln = OxmlElement(tag, attrs={"w": str(int(Pt(width_pt))), "cap": "flat", "cmpd": "sng", "algn": "ctr"})
            fill = OxmlElement("a:solidFill")
            fill.append(OxmlElement("a:srgbClr", attrs={"val": color}))
            ln.append(fill)
            ln.append(OxmlElement("a:prstDash", attrs={"val": "solid"}))
        else:
            ln = OxmlElement(tag, attrs={"w": "0"})
            ln.append(OxmlElement("a:noFill"))
        els.append(ln)
    for i, el in enumerate(els):
        tcPr.insert(i, el)


def add_table(slide, x, y, col_w, rows, *, head_fill: str, size: float = 18, head_size: float = 18,
              min_row_h: float = 0.5, max_h: float | None = None, first_col_bold: bool = True,
              first_col_color: str | None = None, name: str = "Table", alt: str | None = None,
              code_color: str | None = None, zebra: bool = True, head_h: float = 0.52,
              head_fills: list[str] | None = None):
    """rows[0] is the header. Cells are str or list of paragraph specs. Row heights come from the text estimate."""
    n_rows, n_cols = len(rows), len(col_w)
    margin = (0.12, 0.05, 0.12, 0.05)
    heights = [head_h]
    for r in rows[1:]:
        est_max = 0.0
        for ci, cell in enumerate(r):
            paras = [cell] if isinstance(cell, (str, dict)) else cell
            est = margin[1] + margin[3]
            for spec in paras:
                spec = {"t": spec} if isinstance(spec, str) else spec
                sz = spec.get("size", size)
                b = spec.get("bold", first_col_bold and ci == 0)
                n = est_lines(plain(spec["t"]), sz, col_w[ci] - margin[0] - margin[2], b, spec.get("mono", False))
                est += n * sz * LINE_H * 1.05 / 72.0 + spec.get("after", 0) / 72.0
            est_max = max(est_max, est)
        heights.append(max(min_row_h, est_max))
    total_h = sum(heights)
    if max_h and total_h > max_h + 0.01:
        WARNINGS.append(f"slide {CUR['n']} ({CUR['title'][:24]}): table '{name}' needs ~{total_h:.2f}in > {max_h:.2f}in")
    gf = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y), Inches(sum(col_w)), Inches(total_h))
    gf.name = name
    if alt:
        set_alt(gf, alt)
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "1")
    tblPr.set("bandRow", "0")
    style = tblPr.find(qn("a:tableStyleId"))
    if style is None:
        style = OxmlElement("a:tableStyleId")
        tblPr.append(style)
    style.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    for ci, w in enumerate(col_w):
        tbl.columns[ci].width = Inches(w)
    for ri, h in enumerate(heights):
        tbl.rows[ri].height = Inches(h)
    for ri, r in enumerate(rows):
        for ci, cell in enumerate(r):
            c = tbl.cell(ri, ci)
            c.margin_left, c.margin_top, c.margin_right, c.margin_bottom = (Inches(v) for v in margin)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            if ri == 0:
                c.fill.fore_color.rgb = rgb(head_fills[ci] if head_fills else head_fill)
                _cell_border(c, None, P["line"])
                paras = [{"t": cell, "bold": True, "color": "FFFFFF", "size": head_size}]
                fill_text(c.text_frame, paras, size=head_size, anchor="m", inset=(0, 0, 0, 0))
            else:
                c.fill.fore_color.rgb = rgb(P["soft"] if (zebra and ri % 2 == 0) else "FFFFFF")
                _cell_border(c, "line", P["line"])
                paras = [cell] if isinstance(cell, (str, dict)) else cell
                paras = [({"t": s} if isinstance(s, str) else dict(s)) for s in paras]
                for s in paras:
                    if ci == 0 and first_col_bold:
                        s.setdefault("bold", True)
                        if first_col_color:
                            s.setdefault("color", first_col_color)
                fill_text(c.text_frame, paras, size=size, anchor="m", inset=(0, 0, 0, 0), code_color=code_color)
    return gf, total_h


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
def set_notes(slide, notes: dict) -> None:
    tf = slide.notes_slide.notes_text_frame
    lines: list[tuple[str, bool]] = [("[말할 내용]", True)]
    lines += [(s, False) for s in notes["say"]]
    if notes.get("cue"):
        lines.append(("[시연 큐]", True))
        lines += [("- " + c, False) for c in notes["cue"]]
    lines.append((notes["time"], True))
    first = True
    for text, bold in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        r = p.add_run()
        r.text = text
        r.font.size = Pt(14)
        r.font.bold = bold
        rPr = r._r.get_or_add_rPr()
        rPr.set("lang", "ko-KR")
        set_typefaces(rPr, LATIN)


# ===========================================================================
# DATA — edit here, then run `python slides/build_deck.py`.
# Timing follows the demo READMEs (demos/0N-*/README.md): each demo "약 N분" is the live part.
# ===========================================================================
UI_NOTE = "UI 메뉴 이름은 변경될 수 있으니 같은 뜻의 메뉴를 찾아 주세요."

# step = (title, time, command/click lines, 성공 기준, in_lite)
DEMOS = [
    {
        "key": "copilot", "no": 1, "product": "GitHub Copilot", "short": "Copilot",
        "title": "이슈에서 PR까지, AI 팀원과 협업", "minutes": 7, "lite_min": 4,
        "needs": "GitHub 저장소 + Copilot 라이선스", "independent": "Azure 불필요",
        "cards": [
            ("생산성", "이슈를 쓰면 에이전트가 코드와 테스트를 만들어 초안 PR로 올립니다.", "이슈 할당 → 초안 PR"),
            ("팀 표준의 코드화", "지침·프롬프트·전용 에이전트를 코드처럼 버전 관리하고 PR로 리뷰합니다.", ".github/ 아래 설정 파일"),
            ("안전한 자동화", "에이전트는 copilot/ 브랜치에만 쓰고 승인·merge는 사람이 합니다.", "CI + Copilot 리뷰"),
            ("클라우드 연결", "Azure MCP로 리소스를 조회하고 Copilot CLI로 터미널에서 이어 갑니다.", "(옵션) agent mode"),
        ],
        "steps": [
            ("설정 둘러보기", "1분",
             ["GitHub → .github/ 폴더", "copilot-instructions.md", "instructions/ prompts/ agents/"],
             "규칙 목록과 applyTo 줄이 보인다", True),
            ("이슈 만들고 할당", "1.5분",
             ["scripts/create-demo-issues.sh", "  --apply --assign-copilot", "  --only 3"],
             "Copilot 담당자가 붙고 눈 반응이 달린다", False),
            ("세션 · PR · CI", "2분",
             ["View session", "Files changed", "Approve and run workflows"],
             "초안 PR, CI job이 모두 초록색", True),
            ("리뷰와 merge", "2분",
             ["Ready for review", "Reviewers → Copilot", "사람 승인 → merge"],
             "Copilot 코멘트 뒤 사람이 승인·merge", True),
        ],
        "opt": ("옵션", "agent mode", "2분",
                "VS Code Agent 모드 · /add-endpoint GET /api/version · MCP: List Servers → azure"),
        "flow_foot": UI_NOTE,
        "code": {
            "title": "핵심 설정: 팀 규칙을 저장소에 둡니다",
            "blocks": [
                {"type": "code", "label": ".github/copilot-instructions.md (발췌)", "lines": [
                    "# Copilot instructions — Cloud Copilot Demo",
                    "- Python 3.12 + stdlib only; no new dependencies",
                    "- Test: python -m unittest discover -s app/tests -v",
                    "- GET /healthz is the only unauthenticated route",
                    "- Prefer keyless Entra ID (DefaultAzureCredential)",
                    "- Never log or commit secrets, keys or tokens",
                    "- Keep LLM_BACKEND=mock working offline",
                    "- Render model output with textContent, never innerHTML",
                    "- A human reviews and merges; never self-approve",
                ]},
                {"type": "flow", "label": "이슈에서 merge까지", "items": [
                    "이슈", "@copilot", "초안 PR", "CI", "Copilot 리뷰", "사람 merge"]},
            ],
            "callouts": [
                ("한 번 쓰면 모두 적용", "에이전트·VS Code·코드 리뷰가 같은 지침을 읽습니다."),
                ("경로별 규칙", "`applyTo`로 Python·Bicep·K8s마다 다른 규칙을 줍니다."),
                ("사람이 마지막 관문", "에이전트는 승인과 merge를 할 수 없습니다."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "첫 번째는 GitHub Copilot입니다. 이슈 하나를 AI 팀원, 즉 Copilot cloud agent에게 맡기고 결과를 PR로 받습니다.",
                    "핵심은 속도만이 아닙니다. 팀의 규칙이 저장소 안의 파일로 들어 있어서 에이전트도 사람과 같은 규칙을 따릅니다.",
                    "마지막 관문은 항상 사람입니다. 에이전트는 승인도 merge도 할 수 없습니다.",
                ],
                "cue": ["에이전트 작업에는 몇 분이 걸리므로 시연 10~15분 전에 이슈 하나를 미리 할당해 두고, 그 PR 탭을 열어 둡니다."],
                "time": "[예상 시간] 약 1분 · 데모 1 전체 약 7분",
            },
            "flow": {
                "say": [
                    "먼저 .github 폴더의 Copilot 설정을 보여 주고, 이슈를 만들어 Copilot에게 할당합니다.",
                    "작업에는 시간이 걸리므로 미리 만들어 둔 PR로 이동해 세션 로그, 변경 파일, CI를 확인합니다.",
                    "Ready for review로 바꾸고 Copilot code review를 요청한 뒤, 사람이 판단해서 merge합니다.",
                ],
                "cue": [
                    "1) GitHub에서 .github/copilot-instructions.md → instructions/ → prompts/ → agents/ 순서로 엽니다.",
                    "2) scripts/create-demo-issues.sh --apply --assign-copilot --only 3 (또는 이슈 폼 → Assignees → Copilot).",
                    "3) 타임라인의 View session → Files changed → 대기 중이면 Approve and run workflows.",
                    "4) Ready for review → Reviewers에서 Copilot 요청(gh pr edit <PR번호> --add-reviewer \"@copilot\"). 룰셋이 켜져 있으면 에이전트를 시킨 본인은 승인할 수 없으니 관리자 우회나 다른 계정을 준비합니다.",
                    "5) (옵션) VS Code Agent 모드에서 /add-endpoint GET /api/version, MCP: List Servers → azure.",
                    UI_NOTE + " Lite 경로: 1·3·4단계만 진행합니다.",
                ],
                "time": "[예상 시간] 단계 합계 약 6.5분 (옵션 5단계 약 2분 별도)",
            },
            "code": {
                "say": [
                    "왼쪽은 저장소 공통 지침의 발췌입니다. 이 파일은 .github 아래에 있고 에이전트와 코드 리뷰가 자동으로 읽습니다.",
                    "규칙을 바꾸고 싶으면 이 파일을 PR로 고치면 됩니다. 사람이 따르는 코딩 규칙과 에이전트가 따르는 규칙이 한 곳에 있습니다.",
                    "아래 띠는 방금 본 흐름입니다. 이슈에서 시작해 사람의 merge로 끝납니다.",
                ],
                "cue": ["에이전트가 작업하는 대기 시간에 이 슬라이드로 설명하면 시간이 겹쳐서 절약됩니다."],
                "time": "[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)",
            },
        },
    },
    {
        "key": "repo", "no": 2, "product": "GitHub Repo", "short": "Repo",
        "title": "안전한 협업의 기본값: Rulesets·보안·Codespaces", "minutes": 6, "lite_min": 0,
        "needs": "GitHub 저장소(관리자 권한)", "independent": "Azure 불필요",
        "cards": [
            ("main 보호", "PR 필수, 필수 체크, 코드 오너 리뷰를 통과해야 merge됩니다.", "룰셋 Active, 체크 3개"),
            ("책임 분리", "바뀐 경로의 책임자가 자동으로 리뷰어가 되고 승인이 필수가 됩니다.", "CODEOWNERS 한 줄"),
            ("공급망·코드 보안", "CodeQL, Dependency review, Dependabot, secret scanning을 켭니다.", "위험한 PR이 막힘"),
            ("클릭 몇 번으로 시작", "Codespaces로 설치 없이 테스트·앱을 실행하고 설정은 파일로 관리합니다.", "테스트 OK, /healthz 200"),
        ],
        "steps": [
            ("Codespaces 시작", "1분",
             ["Code → Codespaces → Create", "python -m unittest discover", "  -s app/tests -v"],
             "테스트 통과, /healthz 200", False),
            ("Rulesets 확인", "2분",
             ["main-protection.json, CODEOWNERS", "scripts/apply-repo-settings.sh", "  (dry-run) → --apply"],
             "main-protection이 Active로 보인다", False),
            ("위험한 PR", "2분",
             ["demos/02-github-repo/risky-pr/", "  make-risky-pr.sh --apply", "→ PR 체크와 merge 상자 확인"],
             "보안 검사가 잡고 merge가 막힌다", False),
            ("Dependabot", "1분",
             [".github/dependabot.yml", "Security → Dependabot", "gh pr list --label dependencies"],
             "업데이트 기록 또는 PR이 보인다", False),
        ],
        "flow_foot": "설정 스크립트는 저장소 설정을 바꿉니다. 연습용 저장소에서 먼저 리허설하세요. [DEMO – DO NOT MERGE] PR은 merge하지 않습니다.",
        "code": {
            "title": "핵심 설정: 룰셋과 CODEOWNERS",
            "blocks": [
                {"type": "rules", "label": ".github/rulesets/main-protection.json (요약)", "rows": [
                    ("pull_request", ["PR 필수 · 승인 1건", "코드 오너 리뷰 필수"]),
                    ("required_status_checks", ["Unit tests", "Container build and smoke test", "IaC validation"]),
                    ("non_fast_forward", ["강제 푸시(force push) 금지"]),
                    ("code_scanning", ["CodeQL 알림이 기준 이상이면 차단"]),
                ]},
                {"type": "code", "label": ".github/CODEOWNERS", "lines": [
                    "/app/      @junwoojeong100",
                    "/.github/  @junwoojeong100",
                ]},
            ],
            "callouts": [
                ("필수 체크 = job 이름", "룰셋의 체크 이름은 CI job 이름과 같아야 합니다."),
                ("관리자 우회는 타협", "1인 저장소라 열어 뒀습니다. 팀에서는 비우세요."),
                ("설정도 코드", "JSON을 가져오거나 스크립트로 한 번에 적용합니다."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "두 번째는 GitHub 저장소 자체입니다. 좋은 협업은 기능이 아니라 기본값에서 시작합니다.",
                    "main 보호, 코드 오너, 보안 검사가 모두 저장소 안의 파일과 스크립트로 정의되어 있어서 새 저장소에 그대로 가져갈 수 있습니다.",
                    "Codespaces로 설치 없이 개발 환경을 얻고, 마지막에는 일부러 위험하게 만든 PR이 어떻게 걸러지는지 보여 드립니다.",
                ],
                "cue": [
                    "Codespace는 미리 하나 만들어 두고, 위험한 PR도 미리 열어 CodeQL 분석이 끝난 화면을 준비합니다.",
                    "설정 스크립트는 저장소 설정을 바꾸므로 연습용 저장소나 포크에서 먼저 리허설합니다.",
                ],
                "time": "[예상 시간] 약 1분 · 데모 2 전체 약 6분",
            },
            "flow": {
                "say": [
                    "Codespaces에서 테스트와 mock 모드 앱을 실행해 설치할 것이 없다는 점을 보여 줍니다.",
                    "룰셋 JSON을 열어 규칙마다 이유를 설명합니다. apply-repo-settings.sh는 dry-run 출력까지만 청중 앞에서 보여 줍니다.",
                    "위험한 PR에서는 CodeQL, Dependency review, Copilot review, 그리고 막힌 merge 상자를 차례로 짚습니다. 관리자에게 보이는 우회 옵션은 쓰지 않습니다.",
                ],
                "cue": [
                    "1) Code → Codespaces → Create codespace on main → python -m unittest discover -s app/tests -v → LLM_BACKEND=mock python -m app.server (DEMO_PASSWORD는 임시 값).",
                    "2) .github/rulesets/main-protection.json, .github/CODEOWNERS → scripts/apply-repo-settings.sh (dry-run). --apply는 미리 실행해 둡니다.",
                    "3) 로컬 터미널에서 demos/02-github-repo/risky-pr/make-risky-pr.sh --apply. PR 제목은 [DEMO – DO NOT MERGE]이며 절대 merge하지 않습니다.",
                    "4) .github/dependabot.yml → Security → Dependabot, gh pr list --label dependencies.",
                    "secret scanning과 push protection은 토큰 모양 문자열을 만들지 않고 말로만 설명합니다. " + UI_NOTE,
                ],
                "time": "[예상 시간] 단계 합계 약 6분 (1 + 2 + 2 + 1분)",
            },
            "code": {
                "say": [
                    "룰셋은 JSON 하나입니다. PR 필수, 필수 상태 체크 세 개, 코드 오너 리뷰, 강제 푸시와 삭제 금지, CodeQL 알림 기준이 들어 있습니다.",
                    "필수 체크 이름은 CI의 job 표시 이름과 같아야 해서, 워크플로를 바꿀 때 룰셋도 함께 봐야 합니다.",
                    "CODEOWNERS는 경로별 책임자를 지정하고, 룰셋의 코드 오너 리뷰 규칙과 만나 승인이 필수가 됩니다. 이 데모는 1인 저장소라 Admin의 PR 우회를 열어 두었다는 점도 솔직하게 말씀드립니다.",
                ],
                "cue": ["팀 저장소라면 bypass_actors를 비우고 CODEOWNERS를 @org/team으로 바꾸라고 안내합니다."],
                "time": "[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)",
            },
        },
    },
    {
        "key": "actions", "no": 3, "product": "GitHub Actions", "short": "Actions",
        "title": "비밀 없는 CI/CD(OIDC)와 재사용 가능한 파이프라인", "minutes": 7, "lite_min": 4,
        "needs": "GitHub (배포는 Azure 구독)", "independent": "CI는 Azure 불필요",
        "cards": [
            ("빠른 피드백", "독립 job 4개가 병렬로 돌고 pip 의존성은 캐시합니다.", "PR에서 4개 job 동시 실행"),
            ("비밀 없는 배포", "짧게 사는 OIDC 토큰을 Azure가 신뢰합니다. 저장되는 것은 식별자뿐입니다.", "Secrets 목록이 비어 있음"),
            ("최소 권한·승인", "기본은 읽기 전용, 배포 job만 id-token: write. 승인 뒤에 로그인합니다.", "Review deployments 승인"),
            ("공급망 증명", "액션을 커밋 SHA로 고정하고 배포 이미지의 빌드 출처 증명을 남깁니다.", "Attest the build provenance"),
        ],
        "steps": [
            ("CI 병렬 실행", "2분",
             ["gh pr checks --watch", "(PR의 Checks 탭에서도 확인)"],
             "4개 job 초록색, Smoke test 14개 통과", False),
            ("비밀 없는 신뢰", "2분",
             ["scripts/setup-github-oidc.sh", "  (미리보기) → --apply", "Settings → Secrets: 비어 있음"],
             "환경 변수만 있고 Secrets는 비어 있다", True),
            ("승인 → 배포", "3분",
             ["gh workflow run deploy-aca.yml", "Review deployments → 승인", "gh run watch"],
             "앱 버전이 커밋 앞 7자리로 바뀐다", True),
        ],
        "flow_foot": "1단계는 Azure 없이 가능합니다. 2·3단계는 배포 대상이 필요합니다(scripts/deploy-aca.sh --yes).",
        "code": {
            "title": "핵심 코드: 저장된 비밀 0개",
            "blocks": [
                {"type": "code", "label": ".github/workflows/deploy-aca.yml (발췌)", "lines": [
                    "permissions:",
                    "  id-token: write   # OIDC 토큰 발급",
                    "  contents: read",
                    "",
                    "steps:",
                    "  - uses: azure/login@v3",
                    "    with:",
                    "      client-id: ${{ vars.AZURE_CLIENT_ID }}",
                    "      tenant-id: ${{ vars.AZURE_TENANT_ID }}",
                    "      subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}",
                ]},
            ],
            "callouts": [
                ("저장된 비밀 0개", "ID 값은 비밀이 아닌 `vars`에 둡니다."),
                ("좁은 신뢰 범위", "`environment:azure-demo`의 job만 로그인합니다."),
                ("최소 권한", "`id-token: write`는 배포 job에만 줍니다."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "세 번째는 GitHub Actions입니다. PR마다 병렬로 도는 검증, 그리고 저장된 비밀 없이 Azure에 배포하는 방법 두 가지를 보여 드립니다.",
                    "OIDC는 GitHub가 job마다 발급하는 짧은 수명의 토큰을 Azure가 신뢰하게 만드는 방식입니다. 저장소에는 비밀번호도 키도 없고 클라이언트 ID 같은 식별자만 변수로 있습니다.",
                    "배포 전에는 환경 승인 게이트가 있어서, 사람이 승인하기 전에는 Azure에 아무것도 닿지 않습니다.",
                ],
                "cue": ["1단계는 GitHub만 있으면 됩니다. 2·3단계는 Azure 구독이 필요하며 배포 대상은 scripts/deploy-aca.sh --yes로 미리 만들어 둡니다(mock 백엔드)."],
                "time": "[예상 시간] 약 1분 · 데모 3 전체 약 7분",
            },
            "flow": {
                "say": [
                    "먼저 PR을 열고 CI의 job 네 개가 동시에 도는 모습을 보여 드립니다. Azure 자격 증명은 필요 없습니다.",
                    "다음은 setup-github-oidc.sh로 Azure 쪽 신뢰를 구성하는 부분입니다. 끝난 뒤 Settings의 Secrets 목록이 비어 있다는 것을 직접 확인해 주세요.",
                    "마지막으로 배포 워크플로를 실행하고 환경 승인, OIDC 로그인, 새 리비전 순서를 따라갑니다.",
                ],
                "cue": [
                    "1) 작은 변경으로 PR → gh pr checks --watch → Container build and smoke test의 Smoke test 단계 로그(14개 확인).",
                    "2) scripts/setup-github-oidc.sh (미리보기) → --apply → Settings → Secrets and variables → Actions에서 Secrets 없음, 변수만 있음.",
                    "3) gh workflow run deploy-aca.yml → Review deployments에서 azure-demo 승인 → gh run watch → Summary의 앱 주소·리비전, 앱 화면의 버전.",
                    UI_NOTE + " Lite 경로: 2·3단계만(3단계는 미리 돌려 둔 실행을 보여 주고 승인 단계만 라이브).",
                ],
                "time": "[예상 시간] 단계 합계 약 7분 (2 + 2 + 3분)",
            },
            "code": {
                "say": [
                    "이 몇 줄이 비밀 없는 배포의 전부입니다. permissions에서 id-token: write를 주면 job이 OIDC 토큰을 받을 수 있고, azure/login이 그 토큰을 Azure 토큰으로 교환합니다.",
                    "client-id, tenant-id, subscription-id는 비밀이 아니라 식별자라서 secrets가 아니라 vars에 둡니다. 저장된 비밀은 0개입니다.",
                    "Azure 쪽에는 subject가 repo:<owner>/<repo>:environment:azure-demo인 페더레이션 자격 증명이 있어서, 이 저장소의 azure-demo 환경을 쓰는 job만 로그인할 수 있습니다.",
                ],
                "cue": ["발췌는 가독성을 위해 azure/login@v3로 적었고 실제 워크플로는 액션을 커밋 SHA로 고정합니다. <owner>/<repo>는 자신의 저장소 값입니다."],
                "time": "[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)",
            },
        },
    },
    {
        "key": "foundry", "no": 4, "product": "Microsoft Foundry", "short": "Foundry",
        "title": "모델 선택권과 키 없는 보안 연결", "minutes": 7, "lite_min": 3,
        "needs": "Azure 구독 + gpt-6.1-sol 쿼터", "independent": "GitHub·ACA·AKS 불필요",
        "cards": [
            ("Azure 거버넌스", "Entra ID·RBAC·쿼터·리전을 다른 Azure 리소스와 같은 방식으로 씁니다.", "배포 목록의 gpt-6.1-sol 배포"),
            ("배포 이름으로 교체", "앱은 배포 이름만 압니다. 모델 교체는 환경 변수 하나면 됩니다.", "FOUNDRY_MODEL만 변경"),
            ("effort = xhigh", "요청마다 추론 깊이를 지정하고 환경 변수로 low부터 xhigh까지 조절합니다.", "/api/info의 effort: xhigh"),
            ("키 없는 인증", "로컬은 az login, ACA는 관리 ID, AKS는 워크로드 ID로 같은 코드가 동작합니다.", "/api/info의 auth: entra-id"),
        ],
        "steps": [
            ("배포 확인", "1.5분",
             ["az cognitiveservices account", "  deployment list ... -o table", "(또는 ai.azure.com 포털)"],
             "gpt-6.1-sol 배포, API 키 없음", False),
            ("키 없이 호출", "2.5분",
             ["az login", "source .azure/foundry.env", "python -m app.server"],
             "한국어 답변, 인스턴스 표시", True),
            ("/api/info 확인", "1.5분",
             ["curl -s -u \"demo:$DEMO_PASSWORD\"", "  http://127.0.0.1:8080/api/info"],
             "auth: entra-id, model, effort: xhigh", True),
        ],
        "opt": ("옵션", "모델·effort 교체", "1.5분",
                "FOUNDRY_EFFORT=low python -m app.server · FOUNDRY_MODEL=<다른 배포 이름>"),
        "flow_foot": "배포(deploy-foundry.sh)는 시연 전에 끝내 두세요. 역할 부여 직후에는 전파 지연이 있을 수 있습니다.",
        "code": {
            "title": "핵심 코드: OpenAI 호환 엔드포인트 + Entra ID",
            "blocks": [
                {"type": "code", "label": "app/server.py (발췌, 키 없는 경로)", "lines": [
                    "token = get_bearer_token_provider(",
                    "    DefaultAzureCredential(),",
                    "    \"https://ai.azure.com/.default\")",
                    "headers = {\"Authorization\":",
                    "           f\"Bearer {token()}\"}",
                    "body = {",
                    "    \"model\": \"gpt-6.1-sol\",  # 배포 이름",
                    "    \"max_completion_tokens\": 4096,",
                    "    \"reasoning_effort\": \"xhigh\",",
                    "    \"messages\": messages}",
                    "url = f\"https://{resource}.services.ai.azure.com\"",
                    "      \"/openai/v1/chat/completions\"",
                ]},
            ],
            "callouts": [
                ("model = 배포 이름", "모델 ID가 아닌 Foundry 배포 이름입니다."),
                ("키가 없다", "`DefaultAzureCredential`이 토큰을 얻습니다."),
                ("effort = xhigh", "GPT의 최고 단계입니다. 추론은 깊어지고 시간·토큰은 늘어납니다."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "네 번째는 Microsoft Foundry입니다. gpt-6.1-sol을 Azure의 거버넌스 안에서 키 없이 쓰는 방법을 보여 드립니다.",
                    "Entra ID 인증, RBAC, 쿼터와 리전 같은 Azure 리소스의 관리 방식이 그대로 적용됩니다. 앱은 모델이 아니라 배포 이름만 알기 때문에 모델 교체가 설정 변경으로 끝납니다.",
                    "요청마다 effort를 지정해 깊은 추론을 씁니다. 이 키트의 기본값 max는 GPT가 받는 가장 높은 단계인 xhigh로 전달됩니다. 깊게 생각하는 만큼 시간과 토큰을 더 쓴다는 점도 함께 말씀드립니다.",
                ],
                "cue": [
                    "gpt-6.1-sol은 모델 쿼터가 있는 구독이면 배포할 수 있고, 지원 리전은 eastus2, swedencentral, westus2입니다. Claude를 쓰려면 Enterprise 또는 MCA-E 구독과 Anthropic 약관 동의가 필요합니다.",
                    "배포(scripts/deploy-foundry.sh)는 몇 분 걸리므로 시연 전에 끝내 둡니다.",
                ],
                "time": "[예상 시간] 약 1분 · 데모 4 전체 약 7분",
            },
            "flow": {
                "say": [
                    "배포된 모델을 확인하고, 연결 정보 파일에 API 키가 없다는 점을 먼저 보여 드립니다.",
                    "az login만 한 상태에서 로컬 앱을 띄워 한국어로 질문합니다. 코드에는 키가 없고 DefaultAzureCredential이 토큰을 받아 옵니다.",
                    "마지막으로 /api/info에서 인증 방식이 entra-id이고 모델과 effort가 설정대로인지 확인합니다.",
                ],
                "cue": [
                    "1) cat .azure/foundry.env → source .azure/foundry.env → az cognitiveservices account deployment list --resource-group \"$FOUNDRY_RESOURCE_GROUP\" --name \"$FOUNDRY_RESOURCE\" --output table.",
                    "2) az login → source .azure/foundry.env → export DEMO_PASSWORD='<임의 값>' → python -m app.server → http://127.0.0.1:8080(사용자 demo) → 한국어로 질문.",
                    "3) curl -s -u \"demo:$DEMO_PASSWORD\" http://127.0.0.1:8080/api/info → backend foundry · auth entra-id · model gpt-6.1-sol · effort xhigh.",
                    "4) (옵션) FOUNDRY_EFFORT=low python -m app.server로 같은 질문을 비교합니다.",
                    "역할을 방금 부여했다면 전파에 몇 분이 걸려 첫 호출이 권한 오류일 수 있습니다. Lite 경로: 2·3단계.",
                ],
                "time": "[예상 시간] 단계 합계 약 5.5분 + 옵션 1.5분 = 약 7분",
            },
            "code": {
                "say": [
                    "코드는 이 열두 줄입니다. get_bearer_token_provider가 DefaultAzureCredential로 Entra ID 토큰을 받아 오고, 그 토큰을 Authorization 헤더에 실어 Foundry의 OpenAI 호환 엔드포인트를 부릅니다. API 키는 어디에도 없습니다.",
                    "model 인자는 모델 ID가 아니라 Foundry의 배포 이름입니다. 다른 모델을 배포했다면 이름만 바꾸면 됩니다.",
                    "reasoning_effort로 추론 깊이를 지정했고, 낮추려면 환경 변수만 바꾸면 됩니다.",
                ],
                "cue": [
                    "로컬은 az login, ACA는 관리 ID, AKS는 워크로드 ID가 같은 DefaultAzureCredential 경로로 토큰을 만든다고 다음 두 데모의 복선으로 말합니다.",
                    "필요한 역할은 Cognitive Services User 하나입니다. API 키(FOUNDRY_API_KEY)는 선택적 대안일 뿐입니다. Claude 배포는 이름이 claude로 시작하면 자동으로 AnthropicFoundry 경로를 씁니다.",
                ],
                "time": "[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)",
            },
        },
    },
    {
        "key": "aca", "no": 5, "product": "Azure Container Apps", "short": "ACA",
        "title": "서버리스 컨테이너, 스케일 투 제로, 리비전 카나리", "minutes": 7, "lite_min": 4,
        "needs": "Azure 구독", "independent": "mock 백엔드라 Foundry 불필요",
        "cards": [
            ("클러스터 운영 없음", "이미지와 설정만 올리면 HTTPS 주소가 생깁니다. 노드를 관리하지 않습니다.", "deploy-aca.sh → URL"),
            ("스케일 투 제로", "요청이 없으면 복제본이 0개가 되고 다음 요청에 다시 시작합니다.", "Replicas 0 → 1"),
            ("리비전 카나리", "새 리비전에 트래픽 일부만 보내고 승격하거나 즉시 롤백합니다.", "90/10 분할을 probe로 확인"),
            ("관리 ID와 로그", "관리 ID로 비밀 없이 Foundry를 호출하고 로그는 Log Analytics로 모입니다.", "(옵션) auth: entra-id"),
        ],
        "steps": [
            ("스케일 투 제로", "1.5분",
             ["az containerapp revision list", "  -g $RG -n $APP -o table", "curl $APP_URL/healthz  # 2회"],
             "Replicas 0 → 첫 요청 느림 → 1", True),
            ("배포 확인", "1분",
             ["브라우저로 $APP_URL 열기", "scripts/smoke-test.sh $APP_URL", "  --expect-backend mock"],
             "플랫폼 칩 aca, 모든 확인 통과", False),
            ("리비전 카나리", "3분",
             ["scripts/aca-canary.sh", "  deploy v2 → canary 10 → probe 30", "  → promote  (또는 rollback)"],
             "v1·v2가 섞여 응답, promote 후 v2만", True),
            ("부하와 스케일 아웃", "1.5분",
             ["scripts/load-test.sh", "  --url $APP_URL --duration 120", "  --concurrency 20"],
             "복제본이 늘어난다(최대 5)", False),
        ],
        "flow_foot": "배포 후 시연 전까지 요청을 보내지 마세요(브라우저 탭·스모크 테스트도 요청입니다). 그래야 복제본 0개를 보여 줄 수 있습니다.",
        "code": {
            "title": "핵심 명령: 카나리와 스케일 규칙",
            "blocks": [
                {"type": "code", "label": "scripts/aca-canary.sh · az containerapp", "lines": [
                    "scripts/aca-canary.sh deploy v2  # 새 리비전, 0%",
                    "scripts/aca-canary.sh canary 10  # v2 10% · 이전 90%",
                    "scripts/aca-canary.sh probe 30   # 30회 호출 집계",
                    "scripts/aca-canary.sh promote    # v2 100% (또는 rollback)",
                    "",
                    "# 스크립트가 쓰는 az 명령",
                    "az containerapp revision list -g $RG -n $APP -o table",
                    "az containerapp ingress traffic set -g $RG -n $APP \\",
                    "  --label-weight blue=90 green=10",
                ]},
            ],
            "callouts": [
                ("스케일 투 제로", "min 0 · max 5, 유휴 시 복제본이 0개가 됩니다."),
                ("리비전 = 스냅샷", "새 버전은 새 리비전, 레이블로 먼저 확인합니다."),
                ("즉시 롤백", "`rollback`이 이전 리비전에 100%를 돌립니다."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "다섯 번째는 Azure Container Apps입니다. 클러스터를 운영하지 않고 컨테이너를 HTTPS로 서비스하는 서버리스 컨테이너입니다.",
                    "요청이 없으면 복제본이 0개로 줄어 컴퓨팅 비용이 멈추고, 새 버전은 리비전으로 올려 트래픽을 나눠 보냅니다.",
                    "카나리와 롤백이 설정 변경만으로 끝난다는 점이 이 데모의 핵심입니다.",
                ],
                "cue": ["배포 후 시연 시작 전까지 앱에 요청을 보내지 마세요(브라우저 탭과 스모크 테스트도 요청입니다). 그래야 복제본 0개를 보여 줄 수 있습니다."],
                "time": "[예상 시간] 약 1분 · 데모 5 전체 약 7분",
            },
            "flow": {
                "say": [
                    "먼저 아무 요청도 없는 상태에서 Replicas가 0인 것을 보여 주고, 첫 요청이 느린 콜드 스타트를 확인합니다.",
                    "다음은 리비전 카나리입니다. v2를 0%로 올리고 10%만 보낸 뒤 승격하거나 즉시 되돌립니다.",
                    "마지막으로 부하를 걸어 복제본이 늘어나는 모습을 봅니다.",
                ],
                "cue": [
                    "1) az containerapp revision list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo -o table에서 Replicas 0 → curl로 $APP_URL/healthz를 두 번(첫 요청 느림, 두 번째 빠름) → 다시 revision list에서 Replicas 1.",
                    "2) 브라우저로 $APP_URL → 정보 칩의 플랫폼 aca → scripts/smoke-test.sh \"$APP_URL\" --wait 60 --expect-backend mock.",
                    "3) scripts/aca-canary.sh status → deploy v2 → canary 10 → 브라우저의 '트래픽 분포 보기' 또는 probe 30 → promote → probe → rollback.",
                    "4) 터미널 A에서 revision list를 5초마다 반복하고, 터미널 B에서 scripts/load-test.sh --url \"$APP_URL\" --duration 120 --concurrency 20.",
                    "Lite 경로: 1·3단계. 대기 시간이 없다면 1단계는 말로 설명합니다.",
                ],
                "time": "[예상 시간] 단계 합계 약 7분 (1.5 + 1 + 3 + 1.5분)",
            },
            "code": {
                "say": [
                    "카나리는 스크립트 네 줄입니다. deploy가 새 리비전을 트래픽 0%로 만들고, canary 10이 10 대 90으로 나누고, probe가 호출 비율을 집계합니다. 마지막은 promote 또는 rollback입니다.",
                    "스크립트가 쓰는 것은 az containerapp의 트래픽 분할 명령이고, 레이블 가중치로 blue와 green을 나눕니다.",
                    "스케일 규칙은 Bicep에 있습니다. 최소 복제본 0, 최대 5, 동시 요청 5건당 복제본 하나입니다.",
                ],
                "cue": ["rollback은 이전 리비전으로 100%를 되돌릴 뿐 새 리비전은 남아 있어서 다시 승격할 수 있다고 덧붙입니다."],
                "time": "[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)",
            },
        },
    },
    {
        "key": "aks", "no": 6, "product": "AKS", "short": "AKS",
        "title": "롤링 업데이트, 자동 확장, 워크로드 ID, 보안 기본값", "minutes": 8, "lite_min": 0,
        "needs": "Azure 구독", "independent": "mock 백엔드라 Foundry 불필요",
        "cards": [
            ("Kubernetes 그대로", "kubectl·매니페스트·생태계를 그대로 쓰고 컨트롤 플레인은 Azure가 운영합니다.", "kubectl get deploy,hpa,pdb"),
            ("무중단 롤링 업데이트", "새 파드가 준비된 뒤에만 이전 파드가 내려가고, 한 줄로 롤백합니다.", "v1 → v2 → 롤백"),
            ("자동 확장", "HPA는 CPU 50%를 기준으로 파드를 2~5개로, 노드는 오토스케일러가 조절합니다.", "REPLICAS가 늘어남"),
            ("비밀 없는 ID", "워크로드 ID로 비밀 없이 Azure를 호출하고 클러스터 접근은 Entra ID로만 합니다.", "SA 어노테이션 + 주입 변수"),
        ],
        "steps": [
            ("클러스터 둘러보기", "1.5분",
             ["kubectl get deploy,hpa,pdb,svc,pods", "kubectl port-forward \\", "  svc/cloud-copilot-demo 8080:80"],
             "파드 2개 이상 Running, 플랫폼 칩 aks", False),
            ("HPA 자동 확장", "2.5분",
             ["kubectl get hpa,pods -w", "kubectl scale deploy/load-generator", "  --replicas=1"],
             "REPLICAS가 2에서 늘어난다(최대 5)", False),
            ("롤링 업데이트", "2.5분",
             ["kubectl set image \\", "  deploy/cloud-copilot-demo \\", "  app=$IMG:v2"],
             "READY 유지, v2 전환, undo로 복귀", False),
            ("워크로드 ID", "1분",
             ["kubectl get serviceaccount \\", "  cloud-copilot-demo -o yaml", "→ 파드의 AZURE_* 환경 변수 확인"],
             "client-id 어노테이션과 AZURE_* 주입", False),
        ],
        "opt": ("옵션", "보안 기본값", "1분",
                "privileged 파드 적용 → Forbidden: violates PodSecurity \"restricted\""),
        "flow_foot": "kubectl은 --namespace cloud-copilot-demo 기준(생략) · $IMG = $ACR_SERVER/cloud-copilot-demo",
        "code": {
            "title": "핵심 설정: 워크로드 ID와 HPA",
            "blocks": [
                {"type": "code", "label": "infra/aks/k8s/base (발췌)", "lines": [
                    "# serviceaccount.yaml",
                    "annotations:",
                    "  azure.workload.identity/client-id: \"<managed-identity-client-id>\"",
                    "# deployment.yaml (pod template)",
                    "labels:",
                    "  azure.workload.identity/use: \"true\"",
                    "# hpa.yaml",
                    "minReplicas: 2",
                    "maxReplicas: 5",
                    "averageUtilization: 50   # CPU 50%",
                ]},
                {"type": "code", "label": "관찰", "lines": [
                    "kubectl get hpa,pods -n cloud-copilot-demo --watch",
                ]},
            ],
            "callouts": [
                ("워크로드 ID", "파드의 서비스 어카운트 토큰을 Entra ID 토큰으로 교환합니다. 키는 어디에도 없습니다."),
                ("HPA · PDB", "CPU 50% 기준 2~5개로 늘고 줄며, PDB `minAvailable: 1`이 마지막 파드를 지킵니다."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "여섯 번째는 AKS입니다. 쿠버네티스가 잘하는 일을 눈으로 보여 드립니다. 무중단 롤링 업데이트, 부하에 따른 자동 확장, 비밀 없는 워크로드 ID입니다.",
                    "컨트롤 플레인은 Azure가 운영하고, 접근은 로컬 계정 없이 Entra ID와 Azure RBAC로만 합니다. 네임스페이스에는 Pod Security restricted가 강제됩니다.",
                    "ACA보다 손이 가는 만큼 제어할 수 있는 것이 많다는 이야기를 마지막 비교 슬라이드에서 이어 가겠습니다.",
                ],
                "cue": [
                    "클러스터 배포(5~10분)와 v2 이미지 빌드(az acr build ... --image cloud-copilot-demo:v2 --build-arg APP_VERSION=v2)는 시연 전에 끝내 둡니다.",
                    "터미널 셋을 준비합니다: 명령용, --watch용, port-forward용.",
                ],
                "time": "[예상 시간] 약 1분 · 데모 6 전체 약 8분",
            },
            "flow": {
                "say": [
                    "먼저 클러스터에 무엇이 올라와 있는지 한 화면으로 보고, 포트 포워딩으로 앱에 접속합니다. 서비스는 일부러 ClusterIP로 두어 인터넷에 노출하지 않았습니다.",
                    "부하 생성기를 켜면 HPA가 파드를 늘리고, 이미지를 v2로 바꾸면 새 파드가 준비된 뒤에만 이전 파드가 내려갑니다. 문제가 있으면 rollout undo 한 줄로 돌아옵니다.",
                    "마지막으로 서비스 어카운트의 어노테이션과 파드에 주입된 값을 보여 주며 비밀이 어디에도 없다는 점을 확인합니다.",
                ],
                "cue": [
                    "1) kubectl get nodes → kubectl get deployment,hpa,pdb,service,pods --namespace cloud-copilot-demo → kubectl port-forward svc/cloud-copilot-demo 8080:80 --namespace cloud-copilot-demo → http://localhost:8080(사용자 demo).",
                    "2) 터미널 A: kubectl get hpa,pods --namespace cloud-copilot-demo --watch / 터미널 B: kubectl scale deployment/load-generator --replicas=1 --namespace cloud-copilot-demo → 확인 후 --replicas=0.",
                    "3) kubectl set image deployment/cloud-copilot-demo app=\"$ACR_SERVER/cloud-copilot-demo:v2\" --namespace cloud-copilot-demo → kubectl rollout status → kubectl rollout undo deployment/cloud-copilot-demo.",
                    "4) kubectl get serviceaccount cloud-copilot-demo --namespace cloud-copilot-demo -o yaml, 그리고 파드에 주입된 AZURE_* 변수만 걸러서 보여 줍니다. 화면 공유 중에는 printenv를 그대로 실행하지 않습니다(DEMO_PASSWORD 노출).",
                    "(옵션) README의 5단계: privileged 파드를 적용하면 Forbidden, violates PodSecurity \"restricted:latest\"가 출력됩니다.",
                ],
                "time": "[예상 시간] 단계 합계 약 7.5분 (옵션 약 1분 별도)",
            },
            "code": {
                "say": [
                    "워크로드 ID는 세 곳의 설정으로 완성됩니다. 서비스 어카운트의 client-id 어노테이션, 파드 템플릿의 use 레이블, 그리고 Azure 쪽 페더레이션 자격 증명입니다.",
                    "파드는 서비스 어카운트 토큰을 Entra ID 토큰으로 교환하므로 키나 비밀번호를 넣을 곳이 없습니다.",
                    "HPA는 CPU 사용률 50%를 기준으로 파드를 2개에서 5개 사이로 조절하고, PDB가 마지막 파드를 지킵니다.",
                ],
                "cue": ["어노테이션의 client-id는 배포 스크립트가 만든 관리 ID 값으로 치환됩니다(저장소에는 자리 표시자)."],
                "time": "[예상 시간] 약 1분 (시연 대기 시간에 겹쳐 진행)",
            },
        },
    },
]
DEMO_BY_KEY = {d["key"]: d for d in DEMOS}

# ---------------------------------------------------------------------------
# Fixed (non-demo) slides
# ---------------------------------------------------------------------------
AGENDA_WHAT = {
    "copilot": "이슈 → 에이전트 PR → 리뷰 → 사람 merge",
    "repo": "Rulesets · CODEOWNERS · 위험한 PR 차단",
    "actions": "병렬 CI와 비밀 없는 OIDC 배포",
    "foundry": "키 없이 모델 호출 · /api/info",
    "aca": "스케일 투 제로 · 리비전 카나리",
    "aks": "롤링 업데이트 · 자동 확장 · 워크로드 ID",
}
LITE_ORDER = ["copilot", "actions", "foundry", "aca"]  # Lite 경로 (DEMO_GUIDE_KO.md)

FIXED = {
    "title": {
        "title": "GitHub Copilot in the Cloud",
        "subtitle": "아이디어에서 프로덕션까지",
        "tagline": "GitHub × Microsoft Foundry × AKS / ACA",
        "chips": [("GitHub Copilot", "copilot"), ("GitHub Repo", "repo"), ("GitHub Actions", "actions"),
                  ("Microsoft Foundry", "foundry"), ("Container Apps", "aca"), ("AKS", "aks")],
        "foot": "라이브 데모 6개 · Full 약 42분 · Lite 약 15분",
        "notes": {
            "say": [
                "안녕하세요. 오늘은 아이디어 하나가 프로덕션까지 가는 길을 GitHub와 Azure로 직접 만들어 보여 드리겠습니다.",
                "슬라이드는 짧게 쓰고, 대부분의 시간은 라이브 데모에 씁니다. 여섯 가지 서비스를 순서대로 보시되, 각 데모는 단독으로도 시연할 수 있게 만들어져 있습니다.",
            ],
            "cue": [
                "시작 전: 터미널 글꼴을 키우고 알림을 끕니다. DEMO_PASSWORD는 export만 하고 화면에 출력하지 않습니다(printenv 금지).",
                "슬라이드 쇼를 시작하기 전에 데모 1의 이슈를 미리 할당해 두었는지 확인합니다.",
            ],
            "time": "[예상 시간] 약 0.5분",
        },
    },
    "agenda": {
        "title": "오늘의 여정: 데모 6개, 두 가지 경로",
        "notes": {
            "say": [
                "개발에서 운영까지 이어지는 순서로 여섯 가지를 봅니다. Copilot으로 만들고, 저장소 규칙으로 지키고, Actions로 배포하고, Foundry로 모델을 연결하고, Container Apps와 AKS에서 실행합니다.",
                "전부 이어서 하면 데모 합계가 약 42분입니다. 시간이 짧으면 Lite 경로로 Copilot, Actions, Foundry, Container Apps만 핵심 단계로 약 15분에 마칩니다.",
                "오프닝과 마무리 슬라이드는 합쳐서 약 {extra}분이 따로 듭니다. 데모마다 가치 슬라이드는 1분, 핵심 코드 슬라이드는 시연 대기 시간에 겹쳐서 설명합니다.",
            ],
            "cue": [
                "오늘 청중에게 맞는 경로(Full 또는 Lite)를 말로 확정하고, Lite라면 각 흐름 슬라이드의 'Lite' 표시 단계만 진행합니다.",
                "Lite를 15분 슬롯에 맞추려면 3~5번과 24~27번 슬라이드는 한두 문장으로 줄이거나 건너뛰고 28번으로 마무리합니다.",
            ],
            "time": "[예상 시간] 약 1분",
        },
    },
    "arch": {
        "title": "전체 그림: 코드는 GitHub에서, 실행과 AI는 Azure에서",
        "notes": {
            "say": [
                "왼쪽부터 보겠습니다. 개발자는 로컬이나 Codespaces에서 작업하고, 코드는 GitHub 저장소로 갑니다. Copilot이 PR을 만들고, 룰셋과 CI가 검사하고, Actions가 배포합니다.",
                "오른쪽은 Azure입니다. Actions는 이미지를 ACR에 올리고, Container Apps와 AKS가 그 이미지를 받아 실행하며, 앱은 Microsoft Foundry의 gpt-6.1-sol을 호출합니다.",
                "주황색 선에 주목해 주세요. 이 선이 모두 아이덴티티 흐름이고 저장된 키가 없습니다. 로컬은 az login, Actions는 OIDC, Container Apps는 관리 ID, AKS는 워크로드 ID를 씁니다.",
            ],
            "cue": ["선을 손가락이나 포인터로 따라가며 말합니다. 주황색 선 다섯 개를 하나씩 짚는 데 30초면 충분합니다."],
            "time": "[예상 시간] 약 1.5분",
        },
    },
    "matrix": {
        "title": "독립 시연 구조: 어느 데모든 혼자서도 됩니다",
        "rows": [
            ("1 Copilot", "GitHub 저장소, Copilot 라이선스", "Azure 없이 이슈에서 PR까지 GitHub 안에서"),
            ("2 Repo", "GitHub 저장소(관리자 권한)", "설정이 파일이고, 앱은 Codespaces에서 mock 실행"),
            ("3 Actions", "GitHub 저장소 (2·3단계는 Azure)", "CI는 Azure 없이, 배포 대상은 따로 만들기"),
            ("4 Foundry", "Azure 구독(Enterprise 또는 MCA-E)", "az login과 로컬 앱만으로 호출"),
            ("5 ACA", "Azure 구독", "mock 백엔드라 Foundry 없이 시연"),
            ("6 AKS", "Azure 구독", "같은 이미지, 같은 mock 백엔드"),
        ],
        "keys": ["copilot", "repo", "actions", "foundry", "aca", "aks"],
        "foot": "`LLM_BACKEND=mock` — Foundry 없이도 앱 전체가 동작합니다(CI와 데모 5·6의 기본값)",
        "notes": {
            "say": [
                "이 키트의 설계 원칙은 독립 시연입니다. 어떤 데모도 다른 데모를 먼저 할 필요가 없습니다.",
                "비결은 mock 백엔드입니다. LLM_BACKEND를 mock으로 두면 Foundry도 Azure도 없이 앱 전체가 돌아가서, CI와 Container Apps, AKS 데모는 모델 호출 비용 없이 시연됩니다.",
                "그래서 청중과 시간에 맞게 데모를 골라서 쓰시면 됩니다. 필요한 계정과 구독은 표에 있습니다.",
            ],
            "cue": ["README의 독립 실행 매트릭스를 한 번 가리키고 넘어갑니다."],
            "time": "[예상 시간] 약 0.5분",
        },
    },
    "app": {
        "title": "샘플 앱: 이미지 하나가 어디서나 동작합니다",
        "notes": {
            "say": [
                "데모에 쓰는 앱은 아주 작은 챗 앱입니다. 브라우저에서 질문하면 /api/chat이 Microsoft Foundry의 gpt-6.1-sol을 높은 effort로 호출하고, 답변과 함께 어느 플랫폼과 리비전이 응답했는지 화면에 보여 줍니다.",
                "엔드포인트는 셋입니다. /healthz는 플랫폼 프로브용이라 인증이 없고, /api/info는 backend, auth, model, effort 같은 설정을 보여 주며, /api/chat은 데모 인증 뒤에 있습니다.",
                "컨테이너 이미지는 하나입니다. 로컬과 Codespaces, Container Apps, AKS에서 같은 이미지가 돌고, 달라지는 것은 Entra ID 토큰을 얻는 경로뿐입니다.",
            ],
            "cue": ["여기서 앱을 열지는 않습니다. 데모 4에서 처음 실행하므로 구조만 짚고 넘어갑니다."],
            "time": "[예상 시간] 약 1분",
        },
    },
    "compare": {
        "title": "선택 가이드: Container Apps vs AKS",
        "rows": [
            ("운영 부담", "낮음 · 노드 관리 없음", "높음 · 클러스터·노드 풀 직접 운영"),
            ("제어·확장성", "앱 중심 설정, 규칙 기반 스케일", "쿠버네티스 API 전체, 커스텀 확장"),
            ("스케일 투 제로", "기본 지원 (최소 복제본 0)", "HPA 최소 1 · 0은 KEDA 등 추가"),
            ("HTTPS·인그레스", "기본 제공 (자동 HTTPS 주소)", "인그레스·인증서를 직접 구성"),
            ("네트워킹", "VNet 통합 등 관리형 옵션", "CNI·네트워크 정책·사설 클러스터"),
            ("비용 모델(정성)", "쓴 만큼, 유휴 시 0까지", "실행 중인 노드 기준, 상시 비용"),
            ("적합 워크로드", "HTTP API·이벤트, 빠른 출시", "복잡한 서비스, 플랫폼 팀 보유"),
        ],
        "foot": "같은 이미지가 둘 다에서 돕니다. 먼저 ACA로 시작하고, 제어가 더 필요해질 때 AKS로 가도 됩니다.",
        "notes": {
            "say": [
                "두 서비스는 경쟁이 아니라 운영 부담과 제어 수준을 맞바꾸는 선택입니다. Container Apps는 클러스터를 신경 쓰지 않고 HTTPS 서비스를 빨리 올리고, 쓰지 않을 때는 0까지 줄입니다.",
                "AKS는 쿠버네티스의 모든 기능을 쓰는 대신 클러스터와 노드를 운영해야 합니다. 네트워킹, 커스텀 컨트롤러, 플랫폼 팀 표준이 필요하면 AKS가 맞습니다.",
                "오늘 본 것처럼 같은 이미지가 둘 다에서 돌기 때문에, 먼저 ACA로 시작하고 필요가 생길 때 옮겨도 됩니다.",
            ],
            "cue": ["비용은 숫자로 말하지 않고 모델(사용량 기반 대 노드 기반)만 비교합니다. 정확한 비용은 청중이 Azure 가격 계산기로 확인하도록 안내합니다."],
            "time": "[예상 시간] 약 1.5분",
        },
    },
    "pipeline": {
        "title": "End-to-end: 아이디어에서 Foundry까지",
        "stages": [
            ("Idea", "", "neutral", ""),
            ("Issue", "", "repo", "데모 1"),
            ("Copilot", "PR", "copilot", "데모 1"),
            ("Rulesets", "+ CI", "repo", "데모 2"),
            ("Actions", "(OIDC)", "actions", "데모 3"),
            ("ACR", "", "neutral", "데모 3"),
            ("ACA", "또는 AKS", "aca", "데모 5·6"),
            ("Foundry", "", "foundry", "데모 4"),
        ],
        "groups": [
            ("계획", "아이디어를 이슈로 정리합니다.", "copilot"),
            ("구현·검증", "Copilot이 PR을 만들고 룰셋·CI가 검증합니다.", "repo"),
            ("배포", "OIDC로 로그인하고 이미지를 ACR에 올립니다.", "actions"),
            ("실행·AI", "같은 이미지로 실행, Foundry는 키 없이 호출", "aca"),
        ],
        "trust_label": "키 없는 ID 경로",
        "trust": ["로컬 · az login", "Actions · OIDC", "ACA · 관리 ID", "AKS · 워크로드 ID"],
        "notes": {
            "say": [
                "오늘 본 것을 한 줄로 이으면 이렇습니다. 아이디어가 이슈가 되고, Copilot이 PR을 만들고, 룰셋과 CI가 검증합니다.",
                "통과한 코드는 Actions가 OIDC로 Azure에 로그인해 이미지를 ACR에 올리고, Container Apps나 AKS가 그 이미지를 실행하며, 앱은 Foundry의 gpt-6.1-sol을 키 없이 부릅니다.",
                "아래 띠를 보세요. 사람의 로그인부터 CI, 컨테이너까지 모든 구간이 키 대신 아이덴티티로 연결되어 있습니다. 이것이 오늘 전하고 싶은 가장 큰 메시지입니다.",
            ],
            "cue": ["각 단계 아래의 '데모 N' 배지를 따라 어느 데모에서 본 것인지 짚습니다."],
            "time": "[예상 시간] 약 1분",
        },
    },
    "governance": {
        "title": "보안·비용·거버넌스 체크리스트",
        "cards": [
            ("키 없는 인증", "API 키 대신 Entra ID를 씁니다. az login, 관리 ID, 워크로드 ID, OIDC."),
            ("최소 권한", "역할은 필요한 범위에만 주고 `id-token: write`는 배포 job에만 둡니다."),
            ("모델 약관·구독", "gpt-6.1-sol은 쿼터면 충분합니다. Claude는 Enterprise·MCA-E 구독과 Anthropic 약관이 필요합니다."),
            ("쿼터·리전", "지원 리전과 모델 쿼터를 미리 확인하세요. 부족하면 용량이나 리전을 바꿉니다."),
            ("공개 엔드포인트", "`/healthz`만 무인증, 나머지는 데모 비밀번호입니다. 실서비스는 조직 인증으로."),
            ("정리와 비용", "시연 직후 `cleanup.sh`로 정리합니다. AKS는 과금이 이어지고 Foundry는 purge가 필요합니다."),
        ],
        "notes": {
            "say": [
                "도입 전에 확인할 여섯 가지입니다. 첫째, 키가 없습니다. 둘째, 권한은 필요한 범위에만 줍니다. 셋째, 모델 약관과 구독입니다. gpt-6.1-sol은 모델 쿼터만 있으면 되고, Claude를 쓰려면 Enterprise 또는 MCA-E 구독과 Anthropic 약관 동의가 필요합니다.",
                "넷째, 모델 쿼터와 지원 리전을 미리 확인하세요. 다섯째, 데모 앱은 공개 주소에 올라가므로 /healthz를 제외한 모든 경로에 데모 비밀번호를 걸었고, 실서비스에서는 조직의 인증으로 바꿔야 합니다.",
                "마지막으로 정리입니다. 특히 AKS는 노드가 계속 비용을 만들기 때문에 시연이 끝나면 바로 cleanup.sh로 지우고, Foundry는 purge까지 해야 쿼터가 돌아옵니다.",
            ],
            "cue": ["시연 직후 scripts/cleanup.sh aks --yes처럼 대상을 지정해 실행합니다(all은 전부 정리). demo=ghcp-in-the-cloud 태그가 없는 리소스 그룹은 지우지 않는 안전장치가 있습니다."],
            "time": "[예상 시간] 약 1분",
        },
    },
    "summary": {
        "title": "서비스별 핵심 이점 한 장 요약",
        "rows": [
            ("copilot", "GitHub Copilot", "이슈를 PR로, 규칙은 저장소 지침으로", "에이전트 PR + Copilot 리뷰"),
            ("repo", "GitHub Repo", "main 보호·코드 오너·보안 검사를 코드로", "위험한 PR의 merge 차단"),
            ("actions", "GitHub Actions", "병렬 CI, 비밀 없는 OIDC 배포", "Secrets 목록이 비어 있음"),
            ("foundry", "Microsoft Foundry", "Azure 거버넌스 안의 gpt-6.1-sol, 키 없는 호출", "/api/info의 auth: entra-id"),
            ("aca", "Container Apps", "서버리스: 스케일 투 제로와 카나리", "Replicas 0 → 1, 90/10"),
            ("aks", "AKS", "롤링 업데이트·HPA·워크로드 ID", "READY 유지, 파드 증가"),
        ],
        "notes": {
            "say": [
                "한 장으로 정리합니다. 각 서비스가 가져다 주는 이점과, 오늘 화면에서 직접 확인한 증거를 짝지었습니다.",
                "Copilot은 이슈를 PR로 바꾸고, 저장소는 규칙을 코드로 강제하고, Actions는 비밀 없이 배포하고, Foundry는 키 없이 모델을 쓰게 하고, Container Apps와 AKS는 같은 이미지를 서로 다른 운영 방식으로 실행합니다.",
            ],
            "cue": ["오른쪽 '시연에서 본 증거' 열을 읽으며 청중이 기억하도록 합니다."],
            "time": "[예상 시간] 약 1분",
        },
    },
    "closing": {
        "title": "시작하기 · Q&A",
        "repo_label": "저장소",
        "items": [
            ("README.md", "개요 · 빠른 시작 · 독립 실행 매트릭스"),
            ("demos/", "데모 6개 각각의 시연 문서"),
            ("slides/", "이 발표 자료와 재생성 스크립트"),
            ("DEMO_GUIDE_KO.md", "Full·Lite 시간표와 사전 준비"),
        ],
        "start_label": "5분 만에 시작 (Azure 없이)",
        "start": [
            "python -m unittest discover -s app/tests -v",
            "LLM_BACKEND=mock python -m app.server",
        ],
        "foot": "정리: scripts/cleanup.sh <aca|aks|foundry|oidc|all>",
        "notes": {
            "say": [
                "시작하는 가장 쉬운 방법은 저장소를 열어서 README의 빠른 시작을 따라 해 보는 것입니다. Azure 없이 mock 백엔드로 앱과 테스트를 먼저 돌려 보실 수 있습니다.",
                "demos 폴더에는 오늘 본 여섯 가지 데모의 시연 문서가 있고, slides 폴더에는 이 발표 자료와 재생성 스크립트가 있습니다. 필요하면 가져가서 고쳐 쓰세요.",
                "질문 받겠습니다.",
            ],
            "cue": [
                "Q&A 중 자주 나오는 질문은 부록의 트러블슈팅과 체크리스트로 답합니다.",
                "발표 후 반드시 scripts/cleanup.sh로 Azure 리소스를 정리합니다.",
            ],
            "time": "[예상 시간] Q&A 포함 가변 (본문 약 1분)",
        },
    },
    "prep": {
        "title": "부록 A. 사전 준비 체크리스트",
        "cols": [
            ("GitHub", "repo", [
                "연습용 저장소(포크)",
                "저장소 관리자 권한",
                "Copilot 라이선스 (cloud agent)",
                "`gh auth login`",
                "`azure-demo` 환경 승인자 지정",
            ]),
            ("Azure", "aca", [
                "구독 Owner (또는 Contributor + User Access Administrator)",
                "gpt-6.1-sol 쿼터가 있는 구독·리전 (Claude는 Enterprise 또는 MCA-E)",
                "시연 30~60분 전 배포: foundry → aca → aks → oidc",
            ]),
            ("로컬 도구", "aks", [
                "bash 4+, Python 3.12",
                "`az`, `gh`, `jq`",
                "`kubectl` + `kubelogin`, `docker`(선택)",
                "터미널 글꼴 키우기, 알림 끄기",
                "`DEMO_PASSWORD`는 export만 (출력 금지)",
            ]),
        ],
        "notes": {
            "say": [
                "발표 전에 점검할 항목입니다. 질문이 나오면 이 페이지로 돌아와 답하세요.",
                "배포가 오래 걸리는 Foundry, Container Apps, AKS는 시연 30~60분 전에 미리 만들어 둡니다. OIDC 설정은 배포 대상이 먼저 있어야 해서 마지막에 합니다.",
            ],
            "cue": ["상세 체크리스트와 데모별 사전 작업은 DEMO_GUIDE_KO.md의 '발표 전 체크리스트'에 있습니다."],
            "time": "[예상 시간] 부록 (발표 중에는 건너뜀)",
        },
    },
    "trouble": {
        "title": "부록 B. 트러블슈팅 Top 5",
        "rows": [
            ("RBAC 전파 지연", "403 · AuthorizationFailed", "역할 부여 직후에는 수 분이 걸립니다. 잠시 뒤 다시 시도하세요."),
            ("모델 쿼터·리전", "배포가 쿼터·용량 오류", "`CAPACITY`를 줄이거나 `LOCATION`을 바꿉니다. (Claude는 Enterprise·MCA-E 필요)"),
            ("ACR 이름 충돌", "이름이 이미 사용 중", "이름은 전역 고유입니다. `NAME_PREFIX`를 바꿔 다시 배포합니다."),
            ("kubelogin · Azure RBAC", "kubectl 인증 오류", "`az login` → `az aks install-cli` → `kubelogin convert-kubeconfig --login azurecli`"),
            ("OIDC subject 불일치", "AADSTS70021", "저장소·환경 이름 확인, `setup-github-oidc.sh --apply --repo <owner>/<name>`"),
        ],
        "notes": {
            "say": [
                "리허설에서 가장 자주 만나는 문제 다섯 가지입니다. 대부분 몇 분 기다리거나 이름을 맞추면 해결됩니다.",
                "역할을 방금 줬다면 전파에 몇 분이 걸립니다. 모델은 쿼터와 리전이 맞아야 배포되고, ACR 이름은 전역에서 유일해야 합니다.",
                "AKS는 Entra ID와 Azure RBAC로만 접근하므로 kubelogin이 필요하고, OIDC 로그인이 실패하면 subject의 저장소 이름과 환경 이름부터 확인합니다.",
            ],
            "cue": ["데모 문서마다 '문제 해결' 표가 있습니다. 증상별 상세 해결책은 해당 데모의 README를 보라고 안내합니다."],
            "time": "[예상 시간] 부록 (필요할 때만)",
        },
    },
    "links": {
        "title": "부록 C. 참고 링크",
        "rows": [
            ("GitHub Copilot", "docs.github.com/copilot", "https://docs.github.com/copilot"),
            ("GitHub Actions", "docs.github.com/actions", "https://docs.github.com/actions"),
            ("GitHub 저장소", "docs.github.com/repositories", "https://docs.github.com/repositories"),
            ("코드 보안", "docs.github.com/code-security", "https://docs.github.com/code-security"),
            ("Microsoft Foundry", "ai.azure.com", "https://ai.azure.com"),
            ("Azure Container Apps", "learn.microsoft.com/azure/container-apps", "https://learn.microsoft.com/azure/container-apps"),
            ("AKS", "learn.microsoft.com/azure/aks", "https://learn.microsoft.com/azure/aks"),
            ("Workload Identity", "learn.microsoft.com/entra/workload-id", "https://learn.microsoft.com/entra/workload-id"),
            ("이 데모 키트", REPO, "https://" + REPO),
        ],
        "foot": "각 제품의 최신 문서는 위 시작 페이지에서 찾아 들어가세요. UI와 기능 이름은 바뀔 수 있습니다.",
        "notes": {
            "say": [
                "더 깊이 보고 싶은 분을 위한 시작 페이지입니다. 세부 문서 주소는 자주 바뀌므로 각 제품의 문서 첫 화면 링크만 적었습니다.",
            ],
            "cue": ["링크는 PowerPoint에서 클릭할 수 있습니다. Foundry 문서는 learn.microsoft.com에서 'Microsoft Foundry'를 검색하세요."],
            "time": "[예상 시간] 부록",
        },
    },
}


def build_slides() -> list[dict]:
    """Ordered slide list. Each item: kind, title, label, theme, notes, data."""
    f = FIXED
    S: list[dict] = []

    def add(kind, title, label, theme, notes, /, **data):
        S.append(dict(kind=kind, title=title, label=label, theme=theme, notes=notes, data=data))

    add("title", f["title"]["title"], "", "copilot", f["title"]["notes"], **f["title"])
    add("agenda", f["agenda"]["title"], "오프닝 · 오늘의 여정", "neutral", f["agenda"]["notes"])
    add("arch", f["arch"]["title"], "오프닝 · 전체 그림", "neutral", f["arch"]["notes"])
    add("matrix", f["matrix"]["title"], "오프닝 · 독립 시연", "neutral", f["matrix"]["notes"], **f["matrix"])
    add("app", f["app"]["title"], "오프닝 · 샘플 앱", "neutral", f["app"]["notes"])
    for d in DEMOS:
        tag = f"데모 {d['no']} / 6 · {d['product']}"
        add("value", d["title"], tag + " · 가치", d["key"], d["notes"]["value"], demo=d)
        add("flow", f"시연 흐름: {d['product']}", tag + " · 시연 흐름", d["key"], d["notes"]["flow"], demo=d)
        video_path = VIDEO_DIR / f"{d['key']}.mp4"
        add("video", f"데모 영상: {d['product']}", tag + " · 녹화 영상", d["key"],
            {
                "say": [("실제 데모 실행 화면을 녹화한 영상입니다. 영상은 해당 데모 README의 시연 순서를 따릅니다."
                         if video_path.is_file() else
                         "이 데모의 실제 녹화 영상은 아직 없습니다. 녹화 안내의 시연 순서와 성공 기준을 따라 촬영한 뒤 삽입합니다.")],
                "cue": [f"slides/videos/{video_path.name} 파일이 없으면 녹화 안내를 따라 촬영한 뒤 다시 빌드합니다."],
                "time": "[예상 시간] 선택 재생 · 데모 진행 시간에 포함하지 않음",
            },
            demo=d, video_path=video_path)
        add("code", d["code"]["title"], tag + " · 핵심 코드", d["key"], d["notes"]["code"], demo=d)
    add("compare", f["compare"]["title"], "정리 · 선택 가이드", "aks", f["compare"]["notes"], **f["compare"])
    add("pipeline", f["pipeline"]["title"], "정리 · End-to-end", "neutral", f["pipeline"]["notes"], **f["pipeline"])
    add("governance", f["governance"]["title"], "정리 · 거버넌스", "neutral", f["governance"]["notes"], **f["governance"])
    add("summary", f["summary"]["title"], "정리 · 핵심 이점", "neutral", f["summary"]["notes"], **f["summary"])
    add("closing", f["closing"]["title"], "", "copilot", f["closing"]["notes"], **f["closing"])
    add("prep", f["prep"]["title"], "부록", "neutral", f["prep"]["notes"], **f["prep"])
    add("trouble", f["trouble"]["title"], "부록", "neutral", f["trouble"]["notes"], **f["trouble"])
    add("links", f["links"]["title"], "부록", "neutral", f["links"]["notes"], **f["links"])
    return S


# ===========================================================================
# RENDERERS
# ===========================================================================
_DECO_NS = "http://schemas.microsoft.com/office/drawing/2017/decorative"


def mark_decorative(shape):
    """Flag a shape as decorative so screen readers skip it (PowerPoint 2019+; ignored elsewhere)."""
    cnv = shape._element.xpath("./*[1]/p:cNvPr")[0]
    lst = OxmlElement("a:extLst")
    ext = OxmlElement("a:ext", attrs={"uri": "{C183D7F6-B498-43B3-948B-1728B52AA6E4}"})
    dec = etree.SubElement(ext, "{%s}decorative" % _DECO_NS, nsmap={"adec": _DECO_NS})
    dec.set("val", "1")
    lst.append(ext)
    cnv.append(lst)
    return shape


def deco(slide, x, y, w, h, fill, name="Decoration", **kw):
    return mark_decorative(add_box(slide, x, y, w, h, fill=fill, name=name, **kw))


def pill(slide, x, y, text, *, fill, color, size=16, line=None, name=None, pad=0.38):
    """Left-aligned pill whose width follows the text. Returns its width."""
    w = text_w(plain(text), size, True) + pad
    h = size * LINE_H / 72.0 + 0.1
    add_box(slide, x, y, w, h, fill=fill, line=line, radius=h / 2, name=name or f"Pill {plain(text)}",
            text=[{"t": text, "align": "c"}], size=size, bold=True, color=color, anchor="m",
            inset=(0.1, 0.02, 0.1, 0.02))
    return w


def add_slide_number(slide, x, y, w, h, n: int, color: str, size: float = 12) -> None:
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.name = "Slide number"
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    fld = OxmlElement("a:fld", attrs={"id": "{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}", "type": "slidenum"})
    rpr = OxmlElement("a:rPr", attrs={"lang": "en-US", "sz": str(int(size * 100))})
    fill = OxmlElement("a:solidFill")
    fill.append(OxmlElement("a:srgbClr", attrs={"val": color}))
    rpr.append(fill)
    set_typefaces(rpr, LATIN)
    fld.append(rpr)
    t = OxmlElement("a:t")
    t.text = str(n)
    fld.append(t)
    p._p.append(fld)


def footer(slide, n: int, dark: bool = False) -> None:
    col = P["dark_muted"] if dark else P["muted"]
    add_text(slide, MX, 7.04, 8.5, 0.28, [{"t": DECK_NAME}], size=12, color=col, name="Footer", anchor="m",
             spacing=1.0)
    add_slide_number(slide, SLIDE_W - MX - 1.0, 7.04, 1.0, 0.28, n, col)


def set_title(slide, text: str, x, y, w, h, size, color) -> None:
    t = slide.shapes.title
    t.name = "Title"
    t.left, t.top, t.width, t.height = Inches(x), Inches(y), Inches(w), Inches(h)
    fill_text(t.text_frame, [{"t": text, "bold": True}], size=size, color=color, anchor="t", spacing=1.0)
    if est_lines(plain(text), size, w, True) > 1:
        WARNINGS.append(f"slide {CUR['n']}: title '{text}' may wrap to 2 lines")


def new_slide(prs, s, n: int, dark: bool = False):
    CUR["n"], CUR["title"] = n, s["title"]
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # "Title Only": real title placeholder
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = rgb(P["dark"] if dark else P["bg"])
    return slide


def light_frame(prs, s, n: int):
    slide = new_slide(prs, s, n)
    th = THEME[s["theme"]]
    set_title(slide, s["title"], MX, 0.62, CW, 0.78, 30, P["ink"])
    deco(slide, 0, 0, SLIDE_W, 0.1, th["accent"], "Accent strip")
    add_text(slide, MX, 0.27, CW, 0.32, [{"t": s["label"], "spc": 30}], size=14, bold=True, color=th["text"],
             name="Section label", anchor="m", spacing=1.0)
    return slide, th


# ---------------------------------------------------------------------------
# Code highlighting (tiny, dependency-free)
# ---------------------------------------------------------------------------
_KEY_RE = re.compile(r"^(\s*(?:-\s+)?)([A-Za-z0-9_./-]+)(:)(?=\s|$)")
_SH_CMDS = ("scripts/", "az ", "kubectl ", "curl ", "python ", "source ", "gh ", "cat ", "export ")


def _split_comment(line: str) -> tuple[str, str]:
    in_str = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_str = not in_str
        elif ch == "#" and not in_str and (i == 0 or line[i - 1] == " "):
            return line[:i], line[i:]
    return line, ""


def code_runs(line: str) -> list[tuple[str, dict]]:
    if not line.strip():
        return [(" ", {})]
    body, comment = _split_comment(line)
    runs: list[tuple[str, dict]] = []
    m = _KEY_RE.match(body)
    if m:
        runs += [(m.group(1), {}), (m.group(2), {"color": P["code_key"]}), (m.group(3), {})]
        rest = body[m.end():]
    else:
        stripped = body.lstrip()
        if stripped.startswith(_SH_CMDS):
            tok = stripped.split(" ")[0]
            runs += [(body[:len(body) - len(stripped)], {}), (tok, {"color": P["code_key"]})]
            rest = stripped[len(tok):]
        else:
            rest = body
    pos = 0
    for sm in re.finditer(r'"[^"]*"', rest):
        if sm.start() > pos:
            runs.append((rest[pos:sm.start()], {}))
        runs.append((sm.group(0), {"color": P["code_str"]}))
        pos = sm.end()
    if pos < len(rest):
        runs.append((rest[pos:], {}))
    if comment:
        runs.append((comment, {"color": P["code_dim"]}))
    return [(t, o) for t, o in runs if t]


def code_paras(lines: list[str]) -> list[dict]:
    return [{"runs": code_runs(ln), "mono": True, "spacing": 1.0} for ln in lines]


def code_font_size(lines: list[str]) -> int:
    wide = max(text_w(ln, 16, mono=True) for ln in lines) + 0.6
    return 16 if (len(lines) <= 12 and wide <= 7.6) else 14


def code_panel_h(lines: list[str]) -> float:
    return 0.46 + len(lines) * code_font_size(lines) * LINE_H / 72.0 + 0.2


def add_code_panel(slide, x, y, w, label, lines, th, name="Code", h=None):
    size = code_font_size(lines)
    line_h = size * LINE_H / 72.0
    h = max(h or 0.0, code_panel_h(lines))
    add_box(slide, x, y, w, h, fill=P["code_bg"], name=f"{name} panel")
    deco(slide, x, y, w, 0.06, th["accent"], f"{name} accent")
    add_text(slide, x + 0.22, y + 0.14, w - 0.44, 0.28, [{"t": label}], size=14, bold=True, color=P["code_dim"],
             name=f"{name} label", spacing=1.0)
    add_text(slide, x + 0.22, y + 0.48, w - 0.44, len(lines) * line_h + 0.1, code_paras(lines), size=size,
             color=P["code_text"], mono=True, name=f"{name} text", spacing=1.0)
    return h


def code_block_width(lines: list[str]) -> float:
    return max(text_w(ln, code_font_size(lines), mono=True) for ln in lines) + 0.6


def rules_layout(rows, w: float) -> tuple[float, float, float, list[float]]:
    key_w = max(text_w(k, 14, mono=True) for k, _ in rows) + 0.34
    tx = 0.2 + key_w + 0.2
    tw = w - tx - 0.15
    heights = [sum(est_lines(plain(it), 18, tw) for it in items) * 18 * LINE_H / 72.0 + 0.2 for _, items in rows]
    return key_w, tx, tw, heights


def rules_panel_h(rows, w: float) -> float:
    return 0.5 + sum(rules_layout(rows, w)[3]) + 0.08


def add_rules_panel(slide, x, y, w, label, rows, th, h=None):
    key_w, tx_off, tw, heights = rules_layout(rows, w)
    tx = x + tx_off
    natural = 0.5 + sum(heights) + 0.08
    if h and h > natural:
        heights = [v + (h - natural) / len(heights) for v in heights]
    h = 0.5 + sum(heights) + 0.08
    add_box(slide, x, y, w, h, fill=P["soft"], line=P["line"], line_w=0.75, name="Rules panel")
    deco(slide, x, y, w, 0.06, th["accent"], "Rules accent")
    add_text(slide, x + 0.2, y + 0.14, w - 0.4, 0.28, [{"t": label}], size=14, bold=True, color=P["muted"],
             name="Rules label", spacing=1.0)
    cy = y + 0.5
    for i, ((key, items), rh) in enumerate(zip(rows, heights)):
        if i:
            deco(slide, x + 0.2, cy, w - 0.4, 0.012, P["line"], f"Rule divider {i}")
        add_box(slide, x + 0.2, cy + (rh - 0.38) / 2, key_w, 0.38, fill=P["code_bg"], name=f"Rule key {key}",
                text=[{"t": key, "mono": True, "align": "c"}], size=14, bold=True, color=P["code_key"],
                mono=True, anchor="m", inset=(0.05, 0.02, 0.05, 0.02))
        add_text(slide, tx, cy, tw, rh, [{"t": it, "spacing": 1.0} for it in items], size=18, color=P["ink"],
                 name=f"Rule text {key}", anchor="m")
        cy += rh
    return h


def add_chevron(slide, x, y, w, h, depth, fill, paras, *, first=False, size=16, name="Chevron", color="FFFFFF"):
    """Chevron (pentagon when first) plus a separate label box, so text wraps at word breaks inside the visible body."""
    shp = mark_decorative(add_box(slide, x, y, w, h, fill=fill, name=name,
                                  shape=MSO_SHAPE.PENTAGON if first else MSO_SHAPE.CHEVRON))
    shp.adjustments[0] = depth / h
    tx = x + (0.1 if first else depth + 0.04)
    tw = x + w - 0.16 - tx
    for spec in paras:
        longest = max(text_w(word, size, True) for word in plain(spec["t"]).split(" "))
        if longest > tw:
            WARNINGS.append(f"slide {CUR['n']} ({CUR['title'][:24]}): '{name}' word '{spec['t']}' is wider than "
                            f"the chevron body ({longest:.2f} > {tw:.2f}in)")
    add_text(slide, tx, y, tw, h, paras, size=size, bold=True, color=color, anchor="m", spacing=1.0,
             name=f"{name} label")
    return shp


FLOW_H = 0.66  # chevron strip height


def add_flow_band(slide, x, y, w, items, th):
    """Chevron strip with its top edge at y."""
    n = len(items)
    depth = 0.22
    cw_ = (w + (n - 1) * (depth - 0.08)) / n
    step = cw_ - depth + 0.08
    for i, it in enumerate(items):
        add_chevron(slide, x + i * step, y, cw_, FLOW_H, depth, P["ink"] if i == n - 1 else th["accent"],
                    [{"t": it, "align": "c"}], first=i == 0, name=f"Flow step {i + 1}")


CALLOUT_GAP = 0.15


def callout_need(head: str, body: str, w: float) -> float:
    tw = w - 0.5
    hh = est_lines(plain(head), 20, tw, True) * 20 * LINE_H / 72.0 + 3 / 72.0
    bh = est_lines(plain(body), 18, tw) * 18 * LINE_H / 72.0
    return hh + bh + 0.26


def add_callouts(slide, x, y, w, h_total, callouts, th):
    n = len(callouts)
    gap = CALLOUT_GAP
    needs = [callout_need(h, b, w) for h, b in callouts]
    extra = max(0.0, (h_total - gap * (n - 1) - sum(needs)) / n)
    cy = y
    for i, ((head, body), nd) in enumerate(zip(callouts, needs)):
        ch = nd + extra
        add_box(slide, x, cy, w, ch, fill=th["tint"], name=f"Callout {i + 1}")
        deco(slide, x, cy, 0.08, ch, th["accent"], f"Callout {i + 1} bar")
        add_text(slide, x + 0.3, cy + 0.08, w - 0.5, ch - 0.16,
                 [{"t": head, "size": 20, "bold": True, "color": th["text"], "after": 3, "spacing": 1.0},
                  {"t": body}], size=18, color=P["ink"], code_color=th["text"], name=f"Callout {i + 1} text",
                 anchor="m", spacing=1.0)
        cy += ch + gap


# ---------------------------------------------------------------------------
# Demo slides: value / flow / code
# ---------------------------------------------------------------------------
def render_value(slide, s, th):
    d = s["data"]["demo"]
    x0, y0, pw, ph = MX, BODY_TOP, 3.55, 5.2
    add_box(slide, x0, y0, pw, ph, fill=th["panel"], name="Demo summary panel",
            alt=f"데모 {d['no']}: {d['product']}, 약 {d['minutes']}분")
    tx, tw = x0 + 0.3, pw - 0.6
    add_text(slide, tx, y0 + 0.2, tw, 0.85, [{"t": f"{d['no']:02d}"}], size=44, bold=True, color=th["on_dark"],
             spacing=1.0, name="Demo number")
    add_text(slide, tx, y0 + 1.06, tw, 0.95, [{"t": d["product"]}], size=24, bold=True, color="FFFFFF",
             spacing=1.0, name="Product name")
    w1 = pill(slide, tx, y0 + 2.1, f"약 {d['minutes']}분", fill=th["on_dark"], color=th["panel"],
              name="Duration pill")
    if d["lite_min"]:
        pill(slide, tx + w1 + 0.15, y0 + 2.1, f"Lite {d['lite_min']}분", fill=th["accent"], color="FFFFFF",
             name="Lite duration pill")
    deco(slide, tx, y0 + 2.72, tw, 0.02, th["accent"], "Panel divider")
    y = y0 + 2.84
    add_text(slide, tx, y, tw, 0.26, [{"t": "필요한 것"}], size=14, bold=True, color=th["on_dark"],
             spacing=1.0, name="Needs label")
    y += 0.3
    nh = est_lines(plain(d["needs"]), 18, tw) * 18 * LINE_H / 72.0
    add_text(slide, tx, y, tw, nh + 0.04, [{"t": d["needs"]}], size=18, color="FFFFFF", name="Needs", spacing=1.0)
    y += nh + 0.22
    add_text(slide, tx, y, tw, 0.26, [{"t": "독립 시연"}], size=14, bold=True, color=th["on_dark"],
             spacing=1.0, name="Independence label")
    y += 0.3
    ih = est_lines(plain(d["independent"]), 18, tw) * 18 * LINE_H / 72.0
    add_text(slide, tx, y, tw, ih + 0.04, [{"t": d["independent"]}], size=18, color="FFFFFF",
             name="Independence", spacing=1.0)
    if y + ih > y0 + ph - 0.1:
        WARNINGS.append(f"slide {CUR['n']} ({CUR['title'][:24]}): summary panel text runs past the panel")
    gap = 0.25
    cx0 = x0 + pw + 0.3
    cw_ = (SLIDE_W - MX - cx0 - gap) / 2
    chh = (ph - gap) / 2
    for i, (head, body, proof) in enumerate(d["cards"]):
        r, c = divmod(i, 2)
        x, y = cx0 + c * (cw_ + gap), y0 + r * (chh + gap)
        add_box(slide, x, y, cw_, chh, fill=th["tint"], name=f"Benefit card {i + 1}")
        deco(slide, x, y, cw_, 0.08, th["accent"], f"Benefit card {i + 1} accent")
        add_text(slide, x + 0.25, y + 0.2, cw_ - 0.5, chh - 1.0,
                 [{"t": head, "size": 20, "bold": True, "color": th["text"], "after": 3, "spacing": 1.0},
                  {"t": body}], size=18, color=P["ink"], name=f"Benefit {i + 1}", spacing=1.0)
        deco(slide, x + 0.25, y + chh - 0.78, cw_ - 0.5, 0.012, P["line"], f"Benefit {i + 1} divider")
        add_text(slide, x + 0.25, y + chh - 0.72, cw_ - 0.5, 0.66,
                 [{"runs": [("시연  ", {"color": th["text"]}), (proof, {})], "spacing": 1.0}], size=16,
                 bold=True, color=P["ink"], name=f"Benefit {i + 1} proof", anchor="m")


def render_flow(slide, s, th):
    d = s["data"]["demo"]
    steps, opt, foot = d["steps"], d.get("opt"), d.get("flow_foot")
    n = len(steps)
    x_badge, w_badge = MX, 0.8
    x_title, w_title = MX + 0.95, 2.75
    x_cmd, w_cmd = x_title + w_title + 0.1, 4.6
    x_ok = x_cmd + w_cmd + 0.2
    w_ok = SLIDE_W - MX - x_ok
    for x, w, t in ((x_badge, 1.5, "단계"), (x_cmd, w_cmd, "명령 · 클릭"), (x_ok, w_ok, "성공 기준")):
        add_text(slide, x, 1.56, w, 0.28, [{"t": t, "spc": 20}], size=14, bold=True, color=P["muted"],
                 name=f"Column header {t}", spacing=1.0)
    top, gap = 1.9, 0.08
    bottom = BODY_BOTTOM + 0.06
    if foot:
        fh = est_lines(plain(foot), 16, CW) * 16 * LINE_H / 72.0 + 0.02
        add_text(slide, MX, bottom - fh, CW, fh, [{"t": foot}], size=16, color=P["muted"], name="Note",
                 anchor="b", spacing=1.0)
        bottom -= fh + 0.1
    if opt:
        badge, otitle, otime, otext = opt
        ow = SLIDE_W - MX - (MX + 3.3) - 0.2
        oh = max(0.66, est_lines(plain(otext), 16, ow) * 16 * LINE_H / 72.0 + 0.2)
        oy = bottom - oh
        add_box(slide, MX, oy, CW, oh, line=th["accent"], line_w=1.5, dash=MSO_LINE.DASH, name="Optional step",
                alt=f"옵션: {otitle}")
        add_text(slide, MX + 0.2, oy, 3.0, oh,
                 [{"runs": [(f"{badge} · {otitle}", {}), (f"  {otime}", {"bold": False, "color": P["muted"]})],
                   "spacing": 1.0}], size=18, bold=True, color=th["text"], name="Optional step title", anchor="m")
        add_text(slide, MX + 3.3, oy, ow, oh, [{"t": otext}], size=16, color=P["ink2"], name="Optional step text",
                 anchor="m", spacing=1.0)
        bottom = oy - 0.1
    row_h = min(1.5, (bottom - top - gap * (n - 1)) / n)
    for i, (title, time, cmd, ok, lite) in enumerate(steps):
        y = top + i * (row_h + gap)
        add_box(slide, MX, y, CW, row_h, fill=th["tint"], name=f"Step {i + 1} row")
        add_box(slide, x_badge, y, w_badge, row_h, fill=th["accent"], shape=MSO_SHAPE.PENTAGON,
                name=f"Step {i + 1} badge", text=[{"t": str(i + 1), "align": "c"}], size=26, bold=True,
                color="FFFFFF", anchor="m", inset=(0.02, 0, 0.18, 0)).adjustments[0] = 0.22
        tl = est_lines(plain(title), 18, w_title, True)
        th_ = tl * 18 * LINE_H / 72.0
        block = th_ + 16 * LINE_H / 72.0 + 0.02
        by = y + (row_h - block) / 2
        add_text(slide, x_title, by, w_title, th_, [{"t": title}], size=18, bold=True, color=P["ink"],
                 name=f"Step {i + 1} title", spacing=1.0)
        add_text(slide, x_title, by + th_ + 0.02, 1.0, 16 * LINE_H / 72.0, [{"t": time}], size=16,
                 color=P["muted"], name=f"Step {i + 1} time", spacing=1.0)
        if lite:
            pill(slide, x_title + text_w(time, 16) + 0.18, by + th_ - 0.01, "Lite", fill=th["accent"],
                 color="FFFFFF", size=14, name=f"Step {i + 1} Lite tag")
        ch = min(row_h - 0.06, len(cmd) * 14 * LINE_H_MONO / 72.0 + 0.16)
        add_box(slide, x_cmd, y + (row_h - ch) / 2, w_cmd, ch, fill=P["code_bg"], name=f"Step {i + 1} command",
                text=code_paras(cmd), size=14, color=P["code_text"], mono=True, anchor="m",
                inset=(0.14, 0.02, 0.1, 0.02))
        deco(slide, x_ok, y + 0.12, 0.06, row_h - 0.24, P["ok"], f"Step {i + 1} success bar")
        add_text(slide, x_ok + 0.2, y + 0.04, w_ok - 0.2, row_h - 0.08, [{"t": ok}], size=18, color=P["ink"],
                 name=f"Step {i + 1} success criterion", anchor="m")


def render_video(slide, s, th):
    video_path = s["data"]["video_path"]
    x, y, w, h = MX, BODY_TOP, CW, 4.75
    add_box(slide, x, y, w, h, fill=P["code_bg"], name="Demo video frame",
            alt=f"{s['data']['demo']['product']} 실제 시연 영상")
    if video_path.is_file():
        movie = slide.shapes.add_movie(
            str(video_path), Inches(x), Inches(y), Inches(w), Inches(h), mime_type="video/mp4")
        movie.name = f"Demo video {s['data']['demo']['key']}"
    else:
        add_text(slide, x + 0.4, y + 1.3, w - 0.8, 0.7,
                 [{"t": "녹화 영상이 아직 없습니다", "align": "c"}], size=28, bold=True,
                 color=P["dark_text"], name="Video not recorded", anchor="m")
        add_text(slide, x + 0.4, y + 2.15, w - 0.8, 0.7,
                 [{"t": f"녹화 후 여기에 저장: slides/videos/{video_path.name}", "align": "c"}],
                 size=20, color=P["dark_muted"], name="Video file path", anchor="m")
    add_text(slide, x, y + h + 0.18, w, 0.35,
             [{"t": "실제 화면 녹화 · 발표자 노트와 slides/VIDEO_GUIDE_KO.md 참고"}],
             size=16, color=P["muted"], name="Video playback note", spacing=1.0)


def render_code(slide, s, th):
    d = s["data"]["demo"]
    c = d["code"]
    flows = [b for b in c["blocks"] if b["type"] == "flow"]
    blocks = [b for b in c["blocks"] if b["type"] != "flow"]
    band_y = BODY_BOTTOM - FLOW_H
    cap_h = 0.3
    # The strip caption sits under the left column, so the callouts may run lower than the code panel.
    bottom_l = (band_y - cap_h - 0.16) if flows else BODY_BOTTOM
    bottom_r = (band_y - 0.12) if flows else BODY_BOTTOM
    avail_l, avail_r = bottom_l - BODY_TOP, bottom_r - BODY_TOP
    need = []
    for b in blocks:
        if b["type"] == "code":
            need.append(code_block_width(b["lines"]))
        else:
            kw = max(text_w(k, 14, mono=True) for k, _ in b["rows"]) + 0.34
            tw = max(text_w(plain(it), 18) for _, items in b["rows"] for it in items)
            need.append(0.2 + kw + 0.2 + tw + 0.3)
    lw = min(max(max(need), 5.2), CW - 3.6 - 0.25)
    cwid = CW - lw - 0.25
    nat = [code_panel_h(b["lines"]) if b["type"] == "code" else rules_panel_h(b["rows"], lw) for b in blocks]
    gap = 0.15
    left_nat = sum(nat) + gap * (len(nat) - 1)
    right_nat = sum(callout_need(h, b, cwid) for h, b in c["callouts"]) + CALLOUT_GAP * (len(c["callouts"]) - 1)
    for what, got, avail in (("left column", left_nat, avail_l), ("callouts", right_nat, avail_r)):
        if got > avail + 0.01:
            WARNINGS.append(f"slide {CUR['n']} ({CUR['title'][:24]}): {what} needs ~{got:.2f}in but only {avail:.2f}in")
    height = max(left_nat, right_nat, 3.4)
    height_l, height_r = min(avail_l, height), min(avail_r, height)
    grow = nat.index(max(nat))
    extra = max(0.0, height_l - left_nat)
    y = BODY_TOP
    for i, b in enumerate(blocks):
        h = nat[i] + (extra if i == grow else 0.0)
        if b["type"] == "code":
            add_code_panel(slide, MX, y, lw, b["label"], b["lines"], th, name=f"Code {b['label'][:20]}", h=h)
        else:
            add_rules_panel(slide, MX, y, lw, b["label"], b["rows"], th, h=h)
        y += h + gap
    add_callouts(slide, MX + lw + 0.25, BODY_TOP, cwid, height_r, c["callouts"], th)
    for b in flows:
        add_text(slide, MX, bottom_l + 0.08, lw, cap_h, [{"t": b["label"]}], size=14, bold=True, color=P["muted"],
                 name="Flow label", spacing=1.0)
        add_flow_band(slide, MX, band_y, CW, b["items"], th)


# ---------------------------------------------------------------------------
# Opening slides
# ---------------------------------------------------------------------------
def render_title(prs, s, n):
    d = s["data"]
    slide = new_slide(prs, s, n, dark=True)
    for i, (_, key) in enumerate(d["chips"]):
        deco(slide, 0, i * SLIDE_H / 6, 0.2, SLIDE_H / 6, THEME[key]["accent"], f"Color spine {i + 1}")
    x, w = 0.95, SLIDE_W - 0.95 - MX
    set_title(slide, d["title"], x, 1.3, w, 0.95, 40, "FFFFFF")
    add_text(slide, x, 2.3, w, 0.65, [{"t": d["subtitle"]}], size=32, bold=True, color=THEME["copilot"]["on_dark"],
             name="Subtitle", spacing=1.0)
    add_text(slide, x, 3.05, w, 0.5, [{"t": d["tagline"]}], size=24, color=P["dark_text"], name="Tagline",
             spacing=1.0)
    chips = d["chips"]
    cw_, gap = 3.55, 0.2
    for row, (label, grp) in enumerate((("GitHub", chips[:3]), ("Azure", chips[3:]))):
        y = 4.0 + row * 1.05
        add_text(slide, x, y, 3.0, 0.28, [{"t": label, "spc": 40}], size=14, bold=True, color=P["dark_muted"],
                 name=f"{label} group label", spacing=1.0)
        for i, (name, key) in enumerate(grp):
            cx = x + i * (cw_ + gap)
            add_box(slide, cx, y + 0.34, cw_, 0.58, fill=P["dark2"], line=THEME[key]["accent"], line_w=1.5,
                    name=f"Service chip {name}", text=[{"t": name}], size=20, bold=True, color="FFFFFF",
                    anchor="m", inset=(0.5, 0.02, 0.1, 0.02))
            deco(slide, cx + 0.2, y + 0.34 + 0.19, 0.2, 0.2, THEME[key]["accent"], f"{name} dot",
                 shape=MSO_SHAPE.OVAL)
    add_text(slide, x, 6.15, w, 0.4, [{"t": d["foot"]}], size=18, color=P["dark_muted"], name="Run of show",
             spacing=1.0)
    add_text(slide, x, 6.62, w, 0.4, [{"t": REPO}], size=16, color=P["dark_muted"], mono=True, name="Repository",
             spacing=1.0, anchor="m")
    return slide


def render_agenda(slide, s, th):
    left_w, row_h, gap, y0 = 8.55, 0.76, 0.08, 1.68
    for i, d in enumerate(DEMOS):
        t = THEME[d["key"]]
        y = y0 + i * (row_h + gap)
        add_box(slide, MX, y, left_w, row_h, fill=t["tint"], name=f"Agenda row {d['no']}")
        add_box(slide, MX, y, 0.62, row_h, fill=t["accent"], name=f"Agenda number {d['no']}",
                text=[{"t": str(d["no"]), "align": "c"}], size=24, bold=True, color="FFFFFF", anchor="m",
                inset=(0, 0, 0, 0))
        add_text(slide, MX + 0.8, y, 2.45, row_h, [{"t": d["short"]}], size=20, bold=True, color=t["text"],
                 name=f"Agenda name {d['no']}", anchor="m", spacing=1.0)
        add_text(slide, MX + 3.3, y, 3.7, row_h, [{"t": AGENDA_WHAT[d["key"]]}], size=18, color=P["ink"],
                 name=f"Agenda summary {d['no']}", anchor="m", spacing=1.0)
        add_text(slide, MX + 7.0, y, 0.65, row_h, [{"t": f"{d['minutes']}분", "align": "r"}], size=20, bold=True,
                 color=P["ink"], name=f"Agenda minutes {d['no']}", anchor="m", spacing=1.0)
        if d["key"] in LITE_ORDER:
            ph = 14 * LINE_H / 72.0 + 0.1
            pill(slide, MX + 7.72, y + (row_h - ph) / 2, "Lite", fill=t["accent"], color="FFFFFF", size=14,
                 name=f"Agenda Lite tag {d['no']}", pad=0.3)
    rx = MX + left_w + 0.3
    rw = SLIDE_W - MX - rx
    bar_w = rw - 0.5

    def bar_card(y, h, head, items, cap):
        add_box(slide, rx, y, rw, h, fill=THEME["neutral"]["tint"], name=f"{head} card")
        deco(slide, rx, y, rw, 0.08, THEME["neutral"]["accent"], f"{head} accent")
        add_text(slide, rx + 0.25, y + 0.2, rw - 0.5, 0.4, [{"t": head}], size=20, bold=True, color=P["ink"],
                 name=f"{head} title", spacing=1.0)
        total = sum(m for _, m, _ in items)
        bx = rx + 0.25
        for key, m, label in items:
            sw = bar_w * m / total
            add_box(slide, bx, y + 0.72, sw - 0.03, 0.5, fill=THEME[key]["accent"], name=f"{head} segment {label}",
                    alt=f"데모 {label}: {m}분", text=[{"t": label, "align": "c"}], size=16, bold=True,
                    color="FFFFFF", anchor="m", inset=(0, 0, 0, 0))
            bx += sw
        add_text(slide, rx + 0.25, y + 1.34, rw - 0.5, h - 1.4, cap, size=16, color=P["ink2"],
                 name=f"{head} caption", spacing=1.0)

    bar_card(1.68, 2.55, "Full · 약 42분",
             [(d["key"], d["minutes"], str(d["no"])) for d in DEMOS],
             [{"t": "7 + 6 + 7 + 7 + 7 + 8분", "after": 4}, {"t": f"오프닝·마무리는 약 {fmt_min(TIMING['extra'])}분 별도"}])
    bar_card(4.43, 2.38, "Lite · 약 15분",
             [(k, DEMO_BY_KEY[k]["lite_min"], str(DEMO_BY_KEY[k]["no"])) for k in LITE_ORDER],
             [{"t": "4 + 4 + 3 + 4분", "after": 4}, {"t": "Copilot → Actions → Foundry → ACA"}])


# ---------------------------------------------------------------------------
# Architecture diagram (native shapes + straight connectors)
# ---------------------------------------------------------------------------
def arch_box(slide, x, y, w, h, key, title, caption, name, alt):
    t = THEME[key]
    return add_box(slide, x, y, w, h, fill=t["tint"], line=t["accent"], line_w=1.5, name=name, alt=alt,
                   text=[{"t": title, "size": 18, "bold": True, "color": t["text"], "spacing": 1.0},
                         {"t": caption, "size": 16, "color": P["ink2"], "spacing": 1.0}],
                   anchor="m", inset=(0.14, 0.04, 0.1, 0.04))


def render_arch(slide, s, th):
    amber, amber_text, graphite = P["identity"], P["warn"], P["ink2"]
    gh, az = THEME["copilot"], THEME["aca"]
    dx, dw = MX, 1.7
    ghx, ghw = 3.65, 3.3
    azx = 7.9
    azw = SLIDE_W - MX - azx
    # Containers first so connectors and boxes sit on top
    add_box(slide, dx, 3.5, dw, 2.8, fill=P["soft"], line=P["line"], line_w=1.5, name="Developer",
            alt="개발자: VS Code, Codespaces, Copilot CLI, 로컬 앱",
            text=[{"t": "개발자", "size": 20, "bold": True, "color": P["ink"], "after": 6, "spacing": 1.0}] +
                 [{"t": t, "size": 16, "color": P["ink2"], "after": 4, "spacing": 1.0}
                  for t in ("VS Code", "Codespaces", "Copilot CLI", "로컬 앱")],
            anchor="m", inset=(0.18, 0.1, 0.1, 0.1))
    add_box(slide, ghx, 2.95, ghw, 3.5, fill="FAF8FE", line=gh["accent"], line_w=1.75, name="GitHub",
            alt="GitHub: Copilot, 저장소, Actions", text=[{"t": "GitHub", "size": 20, "bold": True,
                                                         "color": gh["text"], "spacing": 1.0}],
            anchor="t", inset=(0.25, 0.1, 0.1, 0.05))
    add_box(slide, azx, 1.5, azw, 4.95, fill="F6FAFE", line=az["accent"], line_w=1.75, name="Azure",
            alt="Microsoft Azure: Foundry, Container Apps, AKS, ACR",
            text=[{"t": "Microsoft Azure", "size": 20, "bold": True, "color": az["text"], "spacing": 1.0}],
            anchor="t", inset=(0.25, 0.1, 0.1, 0.05))
    gx, gw, gh_ = ghx + 0.2, ghw - 0.4, 0.82
    gcx = gx + gw / 2
    arch_box(slide, gx, 3.45, gw, gh_, "copilot", "Copilot", "이슈 → PR 에이전트", "Copilot", "GitHub Copilot")
    arch_box(slide, gx, 4.5, gw, gh_, "repo", "저장소", "룰셋 · CODEOWNERS", "Repo", "GitHub 저장소")
    arch_box(slide, gx, 5.55, gw, gh_, "actions", "Actions", "CI/CD · OIDC 로그인", "Actions", "GitHub Actions")
    ax, aw = azx + 0.2, azw - 0.4
    sw = (aw - 0.12) / 2
    arch_box(slide, ax, 2.0, aw, 0.95, "foundry", "Microsoft Foundry", "gpt-6.1-sol · effort xhigh",
             "Foundry", "Microsoft Foundry")
    arch_box(slide, ax, 3.85, sw, 1.1, "aca", "Container Apps", "관리 ID", "Container Apps", "Azure Container Apps")
    arch_box(slide, ax + sw + 0.12, 3.85, sw, 1.1, "aks", "AKS", "워크로드 ID", "AKS", "Azure Kubernetes Service")
    arch_box(slide, ax, 5.55, aw, 0.82, "neutral", "ACR", "컨테이너 이미지 저장", "ACR", "Azure Container Registry")
    cx1, cx2 = ax + sw / 2, ax + sw + 0.12 + sw / 2
    dcx = dx + dw / 2
    # code / image flows (graphite)
    add_arrow(slide, dx + dw, 4.91, gx, 4.91, color=graphite, name="Arrow push", alt="개발자에서 저장소로 push·PR")
    add_arrow(slide, gcx, 4.27, gcx, 4.5, color=graphite, name="Arrow Copilot to repo", alt="Copilot PR을 저장소로")
    add_arrow(slide, gcx, 5.32, gcx, 5.55, color=graphite, name="Arrow repo to Actions", alt="저장소에서 Actions 실행")
    add_arrow(slide, cx1, 5.55, cx1, 4.95, color=graphite, name="Arrow ACR to ACA", alt="ACR 이미지를 Container Apps가 pull")
    add_arrow(slide, cx2, 5.55, cx2, 4.95, color=graphite, name="Arrow ACR to AKS", alt="ACR 이미지를 AKS가 pull")
    # identity flows (amber): no stored keys
    add_arrow(slide, gx + gw, 5.96, ax, 5.96, color=amber, width=3, name="Arrow OIDC",
              alt="Actions가 OIDC로 Azure에 로그인하고 이미지를 ACR에 push")
    add_arrow(slide, cx1, 3.85, cx1, 2.95, color=amber, width=3, name="Arrow managed identity",
              alt="Container Apps가 관리 ID로 Foundry 호출")
    add_arrow(slide, cx2, 3.85, cx2, 2.95, color=amber, width=3, name="Arrow workload identity",
              alt="AKS가 워크로드 ID로 Foundry 호출")
    add_arrow(slide, dcx, 3.5, dcx, 2.475, color=amber, width=3, head=False, name="Arrow az login up")
    add_arrow(slide, dcx, 2.475, ax, 2.475, color=amber, width=3, name="Arrow az login",
              alt="개발자가 az login으로 Foundry 호출")
    # labels
    add_label(slide, (dx + dw + ghx) / 2, 4.6, "push · PR", color=graphite, fill="FFFFFF", name="Label push")
    add_label(slide, (ghx + ghw + azx) / 2, 5.62, "OIDC", color=amber_text, name="Label OIDC")
    add_label(slide, (dcx + azx) / 2, 2.475, "az login", color=amber_text, name="Label az login")
    add_label(slide, cx1, 3.4, "관리 ID", color=amber_text, name="Label managed identity")
    add_label(slide, cx2, 3.4, "워크로드 ID", color=amber_text, name="Label workload identity")
    add_label(slide, (cx1 + cx2) / 2, 5.27, "이미지 pull", color=graphite, name="Label image pull")
    # legend
    add_arrow(slide, MX, 6.72, MX + 0.55, 6.72, color=amber, width=3, name="Legend identity line")
    add_text(slide, MX + 0.7, 6.55, 5.0, 0.34, [{"t": "ID 흐름 — 저장된 키 없음"}], size=16, bold=True,
             color=amber_text, name="Legend identity", anchor="m", spacing=1.0)
    add_arrow(slide, 6.2, 6.72, 6.75, 6.72, color=graphite, name="Legend flow line")
    add_text(slide, 6.9, 6.55, 5.0, 0.34, [{"t": "코드 · 이미지 흐름"}], size=16, bold=True, color=graphite,
             name="Legend flow", anchor="m", spacing=1.0)


# ---------------------------------------------------------------------------
# Matrix + sample app
# ---------------------------------------------------------------------------
def render_matrix(slide, s, th):
    d = s["data"]
    rows = [["데모", "필요한 것", "혼자서도 되는 이유"]]
    for (a, b, c), key in zip(d["rows"], d["keys"]):
        rows.append([{"t": a, "bold": True, "color": THEME[key]["text"]}, b, c])
    _, h = add_table(slide, MX, BODY_TOP, [1.75, 4.55, 5.83], rows, head_fill=P["ink"], size=18, min_row_h=0.6,
                     max_h=BODY_BOTTOM - BODY_TOP - 0.55, name="Independence matrix",
                     alt="데모별 필요한 것과 독립 실행이 가능한 이유", code_color=THEME["aca"]["text"])
    add_text(slide, MX, BODY_TOP + h + 0.2, CW, 0.5, [{"t": d["foot"]}], size=18, color=P["ink2"],
             code_color=THEME["aca"]["text"], name="Mock backend note", spacing=1.0)


def render_app(slide, s, th):
    amber = P["identity"]
    ww = [2.8, 2.8, 2.9]
    gap = (CW - sum(ww)) / 2
    xs = [MX, MX + ww[0] + gap, MX + ww[0] + gap + ww[1] + gap]
    y, h = 1.7, 1.35
    specs = [("neutral", "브라우저 UI", "질문 입력 · 답변과 인스턴스 표시"),
             ("aca", "Python 앱", "stdlib만 · app/server.py"),
             ("foundry", "Microsoft Foundry", "gpt-6.1-sol · effort xhigh")]
    for x, w, (key, title, cap) in zip(xs, ww, specs):
        arch_box(slide, x, y, w, h, key, title, cap, f"Flow {title}", title)
    cy = y + h / 2
    add_arrow(slide, xs[0] + ww[0], cy, xs[1], cy, color=P["ink2"], name="Arrow UI to app", alt="브라우저가 /api/chat 호출")
    add_arrow(slide, xs[1] + ww[1], cy, xs[2], cy, color=amber, width=3, name="Arrow app to Foundry",
              alt="앱이 Entra ID 토큰으로 Foundry 호출")
    add_label(slide, (xs[0] + ww[0] + xs[1]) / 2, cy - 0.3, "POST /api/chat", color=P["ink2"], size=14,
              name="Label chat")
    add_label(slide, (xs[1] + ww[1] + xs[2]) / 2, cy - 0.3, "Entra ID 토큰", color=amber, size=14, name="Label token")
    eps = [("GET /healthz", "인증 없음", "ok", "플랫폼 프로브가 호출합니다. 앱이 살아 있으면 200을 돌려줍니다."),
           ("GET /api/info", "인증 필요", "aca",
            "`backend` `auth` `model` `effort` `platform` `instance` `revision`을 보여 줍니다."),
           ("POST /api/chat", "데모 인증", "aca", "질문을 Foundry(또는 mock)에 전달하고 답을 돌려줍니다.")]
    cw_, ey, eh = (CW - 0.5) / 3, 3.3, 2.3
    for i, (route, badge, kind, body) in enumerate(eps):
        x = MX + i * (cw_ + 0.25)
        add_box(slide, x, ey, cw_, eh, fill=P["soft"], name=f"Endpoint {route}")
        deco(slide, x, ey, cw_, 0.08, P["ok"] if kind == "ok" else THEME["aca"]["accent"], f"{route} accent")
        add_text(slide, x + 0.25, ey + 0.2, cw_ - 0.5, 0.4, [{"t": route}], size=20, bold=True, color=P["ink"],
                 mono=True, name=f"{route} route", spacing=1.0)
        pill(slide, x + 0.25, ey + 0.7, badge, fill=P["ok_tint"] if kind == "ok" else THEME["aca"]["tint"],
             color=P["ok"] if kind == "ok" else THEME["aca"]["text"], size=14, name=f"{route} auth")
        add_text(slide, x + 0.25, ey + 1.16, cw_ - 0.5, eh - 1.24, [{"t": body}], size=18, color=P["ink"],
                 code_color=THEME["aca"]["text"], name=f"{route} description", spacing=1.0)
    add_text(slide, MX, 5.76, CW, 0.4, [{"t": "같은 컨테이너 이미지가 모든 곳에서 돌고, 달라지는 것은 토큰을 얻는 경로뿐입니다."}],
             size=18, bold=True, color=P["ink"], name="One image", spacing=1.0)
    chips = [("neutral", "로컬 · Codespaces", "az login"), ("aca", "Container Apps", "관리 ID"),
             ("aks", "AKS", "워크로드 ID")]
    cw2 = (CW - 0.5) / 3
    for i, (key, name, ident) in enumerate(chips):
        x = MX + i * (cw2 + 0.25)
        t = THEME[key]
        add_box(slide, x, 6.24, cw2, 0.55, fill=t["tint"], line=t["accent"], line_w=1.5, name=f"Runs on {name}",
                text=[{"runs": [(name, {"bold": True, "color": t["text"]}), (f"  ·  {ident}", {"color": P["identity"],
                       "bold": True})], "align": "c", "spacing": 1.0}], size=18, anchor="m",
                inset=(0.1, 0.02, 0.1, 0.02))


# ---------------------------------------------------------------------------
# Wrap-up slides
# ---------------------------------------------------------------------------
def render_compare(slide, s, th):
    d = s["data"]
    rows = [["기준", "Container Apps", "AKS"]] + [list(r) for r in d["rows"]]
    _, h = add_table(slide, MX, BODY_TOP, [2.7, 4.7, 4.73], rows, head_fill=P["ink"],
                     head_fills=[P["ink"], THEME["aca"]["accent"], THEME["aks"]["accent"]], size=18, min_row_h=0.56,
                     max_h=BODY_BOTTOM - BODY_TOP - 0.7, name="Container Apps vs AKS",
                     alt="Container Apps와 AKS의 운영 부담, 제어, 스케일, 네트워킹, 비용 모델, 적합 워크로드 비교")
    add_text(slide, MX, BODY_TOP + h + 0.18, CW, 0.62, [{"t": d["foot"]}], size=18, bold=True, color=P["ink"],
             name="Takeaway", spacing=1.0)


def render_pipeline(slide, s, th):
    d = s["data"]
    stages, groups = d["stages"], d["groups"]
    n, h, depth = len(stages), 0.95, 0.28
    cw_ = (CW + (n - 1) * (depth - 0.06)) / n
    step = cw_ - depth + 0.06
    y = 1.72
    for i, (l1, l2, key, badge) in enumerate(stages):
        x = MX + i * step
        paras = [{"t": l1, "align": "c"}] + ([{"t": l2, "align": "c"}] if l2 else [])
        add_chevron(slide, x, y, cw_, h, depth, THEME[key]["accent"], paras, first=i == 0,
                    name=f"Stage {i + 1} {l1} {l2}".strip())
        if badge:
            pill(slide, x + (cw_ - depth) / 2 + 0.05 - (text_w(badge, 14, True) + 0.38) / 2 + depth / 2, y + h + 0.1,
                 badge, fill=THEME[key]["tint"], color=THEME[key]["text"], size=14, name=f"Stage {i + 1} demo tag")
    gy, gh = 3.5, 2.05
    for j, (head, body, key) in enumerate(groups):
        x = MX + 2 * j * step
        w = 2 * step - 0.1
        t = THEME[key]
        add_box(slide, x, gy, w, gh, fill=t["tint"], name=f"Phase {head}")
        deco(slide, x, gy, w, 0.08, t["accent"], f"Phase {head} accent")
        add_text(slide, x + 0.2, gy + 0.2, w - 0.35, gh - 0.3,
                 [{"t": head, "size": 20, "bold": True, "color": t["text"], "after": 3, "spacing": 1.0}, {"t": body}],
                 size=18, color=P["ink"], name=f"Phase {head} text", spacing=1.05)
    ty = 5.85
    add_box(slide, MX, ty, CW, 0.9, fill=P["warn_tint"], name="Keyless identity strip",
            alt="로컬 az login, Actions OIDC, ACA 관리 ID, AKS 워크로드 ID: 모두 키 없는 ID 경로")
    add_text(slide, MX + 0.25, ty, 2.4, 0.9, [{"t": d["trust_label"]}], size=18, bold=True, color=P["warn"],
             name="Keyless label", anchor="m", spacing=1.0)
    px = MX + 2.8
    for label in d["trust"]:
        px += pill(slide, px, ty + 0.2, label, fill="FFFFFF", color=P["warn"], line=P["identity"], size=16,
                   name=f"Identity path {label}") + 0.15


def render_governance(slide, s, th):
    cards = s["data"]["cards"]
    gap = 0.25
    cw_ = (CW - gap) / 2
    ch = (BODY_BOTTOM - BODY_TOP - 2 * 0.2) / 3
    for i, (head, body) in enumerate(cards):
        r, c = divmod(i, 2)
        x, y = MX + c * (cw_ + gap), BODY_TOP + r * (ch + 0.2)
        add_box(slide, x, y, cw_, ch, fill=THEME["neutral"]["tint"], name=f"Checklist card {i + 1}")
        add_box(slide, x + 0.22, y + (ch - 0.58) / 2, 0.58, 0.58, fill=P["ink"], shape=MSO_SHAPE.OVAL,
                name=f"Checklist number {i + 1}", text=[{"t": str(i + 1), "align": "c"}], size=20, bold=True,
                color="FFFFFF", anchor="m", inset=(0, 0, 0, 0))
        add_text(slide, x + 1.0, y + 0.08, cw_ - 1.2, ch - 0.16,
                 [{"t": head, "size": 20, "bold": True, "color": P["ink"], "after": 2, "spacing": 1.0}, {"t": body}],
                 size=18, color=P["ink2"], code_color=THEME["aca"]["text"], name=f"Checklist {i + 1}", anchor="m",
                 spacing=1.0)


def render_summary(slide, s, th):
    rows = s["data"]["rows"]
    xn, wn = MX + 0.3, 2.95
    xb, wb = MX + 3.4, 4.7
    xp, wp = MX + 8.25, 3.7
    for x, w, t in ((xn, wn, "서비스"), (xb, wb, "핵심 이점"), (xp, wp, "시연에서 본 증거")):
        add_text(slide, x, 1.56, w, 0.28, [{"t": t, "spc": 20}], size=14, bold=True, color=P["muted"],
                 name=f"Column header {t}", spacing=1.0)
    rh, gap, y0 = 0.76, 0.07, 1.9
    for i, (key, name, benefit, proof) in enumerate(rows):
        t = THEME[key]
        y = y0 + i * (rh + gap)
        add_box(slide, MX, y, CW, rh, fill=t["tint"], name=f"Summary row {name}")
        deco(slide, MX, y, 0.14, rh, t["accent"], f"Summary bar {name}")
        add_text(slide, xn, y, wn, rh, [{"t": name}], size=20, bold=True, color=t["text"], name=f"{name} name",
                 anchor="m", spacing=1.0)
        add_text(slide, xb, y, wb, rh, [{"t": benefit}], size=18, color=P["ink"], name=f"{name} benefit",
                 anchor="m", spacing=1.0)
        add_text(slide, xp, y, wp, rh, [{"t": proof}], size=18, bold=True, color=t["text"], name=f"{name} proof",
                 anchor="m", spacing=1.0)


def render_closing(prs, s, n):
    d = s["data"]
    slide = new_slide(prs, s, n, dark=True)
    for i, k in enumerate(("copilot", "repo", "actions", "foundry", "aca", "aks")):
        deco(slide, 0, i * SLIDE_H / 6, 0.2, SLIDE_H / 6, THEME[k]["accent"], f"Color spine {i + 1}")
    x, w = 0.95, SLIDE_W - 0.95 - MX
    set_title(slide, d["title"], x, 0.55, w, 0.8, 40, "FFFFFF")
    add_text(slide, x, 1.5, 3.0, 0.28, [{"t": d["repo_label"], "spc": 40}], size=14, bold=True, color=P["dark_muted"],
             name="Repository label", spacing=1.0)
    add_text(slide, x, 1.82, w, 0.62, [{"t": REPO}], size=30, bold=True, color=THEME["copilot"]["on_dark"], mono=True,
             name="Repository URL", spacing=1.0)
    gap = 0.2
    cw_ = (w - 3 * gap) / 4
    for i, ((name, desc), key) in enumerate(zip(d["items"], ("copilot", "aca", "foundry", "aks"))):
        cx = x + i * (cw_ + gap)
        t = THEME[key]
        add_box(slide, cx, 2.8, cw_, 1.6, fill=P["dark2"], name=f"Resource {name}")
        deco(slide, cx, 2.8, cw_, 0.08, t["accent"], f"Resource {name} accent")
        add_text(slide, cx + 0.2, 3.0, cw_ - 0.35, 1.3,
                 [{"t": name, "size": 18, "bold": True, "color": t["on_dark"], "mono": True, "after": 4,
                   "spacing": 1.0}, {"t": desc}], size=18, color=P["dark_text"], name=f"Resource {name} text",
                 spacing=1.0)
    add_box(slide, x, 4.7, w, 1.5, fill=P["code_bg"], line=P["dark_line"], line_w=1.0, name="Quick start panel")
    add_text(slide, x + 0.25, 4.82, w - 0.5, 0.3, [{"t": d["start_label"]}], size=14, bold=True, color=P["code_dim"],
             name="Quick start label", spacing=1.0)
    add_text(slide, x + 0.25, 5.2, w - 0.5, 0.9, code_paras(d["start"]), size=16, color=P["code_text"], mono=True,
             name="Quick start commands", spacing=1.0)
    add_text(slide, x, 6.4, w, 0.4, [{"t": d["foot"]}], size=16, color=P["dark_muted"], name="Cleanup reminder",
             spacing=1.0)
    footer(slide, n, dark=True)
    return slide


# ---------------------------------------------------------------------------
# Appendix slides
# ---------------------------------------------------------------------------
def render_prep(slide, s, th):
    cols = s["data"]["cols"]
    gap = 0.25
    cw_ = (CW - 2 * gap) / 3
    top, hh = BODY_TOP, 0.56
    for i, (head, key, bullets) in enumerate(cols):
        x = MX + i * (cw_ + gap)
        t = THEME[key]
        add_box(slide, x, top, cw_, hh, fill=t["accent"], name=f"{head} header", text=[{"t": head}], size=20,
                bold=True, color="FFFFFF", anchor="m", inset=(0.25, 0.02, 0.1, 0.02))
        add_box(slide, x, top + hh, cw_, BODY_BOTTOM - top - hh, fill=t["tint"], name=f"{head} body")
        add_text(slide, x + 0.25, top + hh + 0.2, cw_ - 0.45, BODY_BOTTOM - top - hh - 0.3,
                 [{"t": b, "bullet": True, "bullet_color": t["accent"], "after": 14, "spacing": 1.0} for b in bullets],
                 size=18, color=P["ink"], code_color=t["text"], name=f"{head} checklist")


def render_trouble(slide, s, th):
    rows = [["문제", "해결"]]
    for name, symptom, fix in s["data"]["rows"]:
        rows.append([[{"t": name, "bold": True}, {"t": symptom, "size": 16, "bold": False, "color": P["muted"]}], fix])
    add_table(slide, MX, BODY_TOP, [3.7, 8.43], rows, head_fill=P["ink"], size=18, min_row_h=0.8,
              max_h=BODY_BOTTOM - BODY_TOP, name="Troubleshooting top 5", alt="자주 겪는 문제 다섯 가지와 해결 방법",
              code_color=THEME["aca"]["text"], first_col_bold=False)


def render_links(slide, s, th):
    d = s["data"]
    rows = [["주제", "시작 페이지"]]
    for label, display, url in d["rows"]:
        rows.append([label, {"t": display, "runs": [(display, {"link": url, "color": THEME["aca"]["text"]})]}])
    _, h = add_table(slide, MX, BODY_TOP, [4.0, 8.13], rows, head_fill=P["ink"], size=18, min_row_h=0.46, head_h=0.46,
                     max_h=BODY_BOTTOM - BODY_TOP - 0.5, name="Reference links", alt="공식 문서 시작 페이지 링크")
    add_text(slide, MX, BODY_TOP + h + 0.15, CW, 0.34, [{"t": d["foot"]}], size=16, color=P["muted"],
             name="Links note", spacing=1.0)


# ===========================================================================
# TIMING, MARKDOWN OUTLINE, BUILD
# ===========================================================================
APPENDIX_KINDS = ("prep", "trouble", "links")
KIND_LABEL = {
    "title": "표지", "agenda": "개요", "arch": "다이어그램", "matrix": "표", "app": "다이어그램",
    "value": "가치", "flow": "시연 흐름", "video": "데모 영상", "code": "핵심 코드", "compare": "비교표", "pipeline": "다이어그램",
    "governance": "체크리스트", "summary": "요약", "closing": "마무리", "prep": "부록", "trouble": "부록",
    "links": "부록",
}
TIMING: dict = {}


def fmt_min(x: float) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.1f}"


def minutes_of(notes: dict) -> float:
    m = re.search(r"약\s*([0-9]+(?:\.[0-9]+)?)\s*분", notes["time"])
    return float(m.group(1)) if m else 0.0


def compute_timing(S: list[dict]) -> None:
    first = next(i for i, s in enumerate(S) if s["kind"] == "value")
    last = max(i for i, s in enumerate(S) if s["kind"] == "code")
    closing = next(i for i, s in enumerate(S) if s["kind"] == "closing")
    opening = sum(minutes_of(s["notes"]) for s in S[:first])
    wrap = sum(minutes_of(s["notes"]) for s in S[last + 1:] if s["kind"] not in APPENDIX_KINDS)
    TIMING.update(
        opening=opening, wrap=wrap, extra=opening + wrap,
        full=sum(d["minutes"] for d in DEMOS), lite=sum(DEMO_BY_KEY[k]["lite_min"] for k in LITE_ORDER),
        first=first + 1, last=last + 1, closing=closing + 1,
    )


def fill_timing(text: str) -> str:
    return (text.replace("{extra}", fmt_min(TIMING["extra"])).replace("{full}", fmt_min(TIMING["full"]))
            .replace("{lite}", fmt_min(TIMING["lite"])))


def esc_cell(text: str) -> str:
    return text.replace("|", "\\|")


def md_table(head: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(esc_cell(c) for c in r) + " |" for r in rows]
    return out


def outline_for(s: dict) -> list[str]:
    k, d = s["kind"], s["data"]
    o: list[str] = []
    if k == "title":
        o += [f"- 제목: {d['title']}", f"- 부제: {d['subtitle']}", f"- 태그라인: {d['tagline']}",
              "- 서비스 칩: " + " · ".join(n for n, _ in d["chips"]), f"- 하단: {fill_timing(d['foot'])}"]
    elif k == "agenda":
        rows = [[str(x["no"]), x["short"], AGENDA_WHAT[x["key"]], f"{x['minutes']}분",
                 f"{x['lite_min']}분" if x["key"] in LITE_ORDER else "–"] for x in DEMOS]
        o += md_table(["#", "데모", "내용", "시간", "Lite"], rows)
        o += ["", f"- Full: 데모 합계 약 {fmt_min(TIMING['full'])}분 · Lite: 약 {fmt_min(TIMING['lite'])}분",
              f"- 오프닝·마무리는 약 {fmt_min(TIMING['extra'])}분 별도"]
    elif k == "arch":
        o += ["- 흐름: 개발자 → GitHub(Copilot · 저장소 · Actions) → Azure(ACR → Container Apps / AKS → Microsoft Foundry)",
              "- ID 흐름(주황색, 저장된 키 없음): 개발자 `az login` → Foundry · Actions `OIDC` → Azure · "
              "Container Apps `관리 ID` → Foundry · AKS `워크로드 ID` → Foundry",
              "- 코드·이미지 흐름(회색): push · PR, Copilot PR, 저장소 → Actions, ACR 이미지 pull"]
    elif k == "matrix":
        o += md_table(["데모", "필요한 것", "혼자서도 되는 이유"], [list(r) for r in d["rows"]])
        o += ["", "- " + plain(d["foot"])]
    elif k == "app":
        o += ["- 흐름: 브라우저 UI → `POST /api/chat` → Python 앱(stdlib, `app/server.py`) → Entra ID 토큰 → "
              "Microsoft Foundry(gpt-6.1-sol, effort `xhigh`)",
              "- `GET /healthz`: 인증 없음, 플랫폼 프로브용",
              "- `GET /api/info`: 인증 필요, `backend` `auth` `model` `effort` `platform` `instance` `revision`",
              "- `POST /api/chat`: 데모 인증 뒤",
              "- 같은 이미지: 로컬·Codespaces(`az login`) · Container Apps(관리 ID) · AKS(워크로드 ID)"]
    elif k == "value":
        x = d["demo"]
        lite = f" (Lite {x['lite_min']}분)" if x["lite_min"] else ""
        o += [f"- 데모 {x['no']} · {x['product']} · 약 {x['minutes']}분{lite}", f"- 필요한 것: {x['needs']}",
              f"- 독립 시연: {x['independent']}", "- 이점 카드:"]
        o += [f"  - **{h}** — {b} (시연: {p})" for h, b, p in x["cards"]]
    elif k == "flow":
        x = d["demo"]
        rows = [[f"{i}. {t}", tm, "<br>".join(f"`{ln.strip()}`" for ln in cmd), ok, "Lite" if lite else ""]
                for i, (t, tm, cmd, ok, lite) in enumerate(x["steps"], 1)]
        o += md_table(["단계", "시간", "명령 · 클릭", "성공 기준", "Lite"], rows)
        if x.get("opt"):
            _, ot, otime, otext = x["opt"]
            o += ["", f"- 옵션 · {ot} ({otime}): {otext}"]
        if x.get("flow_foot"):
            o += [f"- 참고: {x['flow_foot']}"]
    elif k == "video":
        o += [f"- 영상 파일: `slides/videos/{d['video_path'].name}`",
              "- 파일이 있으면 PPTX에 삽입하고, 없으면 녹화 위치 안내를 표시합니다.",
              "- 실제 화면 녹화 지침: `slides/VIDEO_GUIDE_KO.md`"]
    elif k == "code":
        c = d["demo"]["code"]
        for b in c["blocks"]:
            if b["type"] == "code":
                o += [f"**{b['label']}**", "", "```", *b["lines"], "```", ""]
            elif b["type"] == "rules":
                o += [f"**{b['label']}**", ""]
                o += [f"- `{key}` — {' · '.join(items)}" for key, items in b["rows"]] + [""]
            else:
                o += [f"**{b['label']}**: " + " → ".join(b["items"]), ""]
        o += ["- 콜아웃:"] + [f"  - **{h}** — {b}" for h, b in c["callouts"]]
    elif k == "compare":
        o += md_table(["기준", "Container Apps", "AKS"], [list(r) for r in d["rows"]])
        o += ["", f"- {d['foot']}"]
    elif k == "pipeline":
        o += ["- 단계: " + " → ".join((l1 + (" " + l2 if l2 else "")).strip() + (f" ({b})" if b else "")
                                    for l1, l2, _, b in d["stages"])]
        o += [f"- {h}: {b}" for h, b, _ in d["groups"]]
        o += [f"- {d['trust_label']}: " + " · ".join(d["trust"])]
    elif k == "governance":
        o += [f"{i}. **{h}** — {b}" for i, (h, b) in enumerate(d["cards"], 1)]
    elif k == "summary":
        o += md_table(["서비스", "핵심 이점", "시연에서 본 증거"], [[n, b, p] for _, n, b, p in d["rows"]])
    elif k == "closing":
        o += [f"- {d['repo_label']}: `{REPO}`"] + [f"- `{n}` — {t}" for n, t in d["items"]]
        o += [f"- {d['start_label']}:", "", "```", *d["start"], "```", "", f"- {d['foot']}"]
    elif k == "prep":
        for head, _, bullets in d["cols"]:
            o += [f"- **{head}**"] + [f"  - {b}" for b in bullets]
    elif k == "trouble":
        o += md_table(["문제", "증상", "해결"], [list(r) for r in d["rows"]])
    elif k == "links":
        o += md_table(["주제", "시작 페이지"], [[a, f"[{b}]({u})"] for a, b, u in d["rows"]])
        o += ["", f"- {d['foot']}"]
    return o


def render_markdown(S: list[dict]) -> str:
    T = TIMING
    L: list[str] = []
    a = L.append
    a("# GitHub Copilot in the Cloud — 발표 개요와 진행 대본")
    a("")
    a("> 이 파일은 `slides/build_deck.py`가 `demo-presentation-ko.pptx`와 같은 데이터로 만든 자동 생성 파일입니다. "
      "직접 고치지 말고 스크립트의 데이터를 수정한 뒤 `python slides/build_deck.py`를 실행하세요. "
      "각 슬라이드의 발표자 노트(PowerPoint의 노트 창)에도 같은 대본이 들어 있습니다.")
    a("")
    a("## 진행 시간")
    a("")
    rows = [["오프닝", f"1–{T['first'] - 1}", f"약 {fmt_min(T['opening'])}분", f"약 {fmt_min(T['opening'])}분"]]
    for i, d in enumerate(DEMOS):
        base = T["first"] + 4 * i
        rows.append([f"데모 {d['no']} · {d['product']}", f"{base}–{base + 3}", f"{d['minutes']}분",
                     f"{d['lite_min']}분" if d["lite_min"] else "건너뜀"])
    rows.append(["마무리", f"{T['last'] + 1}–{T['closing']}", f"약 {fmt_min(T['wrap'])}분 + Q&A",
                 f"약 {fmt_min(T['wrap'])}분 + Q&A"])
    rows.append(["**데모 합계**", "", f"**약 {fmt_min(T['full'])}분**", f"**약 {fmt_min(T['lite'])}분**"])
    rows.append(["발표 전체(참고)", "", f"약 {fmt_min(T['full'] + T['extra'])}분 + Q&A",
                 f"약 {fmt_min(T['lite'] + T['extra'])}분 + Q&A"])
    L += md_table(["구간", "슬라이드", "Full", "Lite"], rows)
    a("")
    a("- 각 데모의 시간은 데모 README의 목표 시간입니다. 가치 슬라이드 설명(약 1분)은 그 안에 넣어 말하고, 핵심 코드 슬라이드는 시연 대기 시간에 겹쳐 설명합니다. 단계 시간의 합이 조금 길면 설명을 줄여 맞추세요.")
    a("- Lite 경로는 Copilot → Actions → Foundry → Container Apps 순서이고, 각 흐름 슬라이드의 `Lite` 표시 단계만 진행합니다. "
      "15분 슬롯에 맞추려면 오프닝(3–5)과 정리(24–27) 슬라이드는 한두 문장으로 줄이거나 건너뜁니다.")
    a("- 부록 슬라이드(체크리스트·트러블슈팅·링크)는 발표 중에는 건너뛰고 Q&A에서 사용합니다.")
    a("")
    a("## 슬라이드 목록")
    a("")
    rows = [[str(n), s["title"], KIND_LABEL[s["kind"]], ("약 " + fmt_min(minutes_of(s["notes"])) + "분")
             if minutes_of(s["notes"]) else "–"] for n, s in enumerate(S, 1)]
    L += md_table(["#", "제목", "종류", "예상 시간"], rows)
    a("")
    for n, s in enumerate(S, 1):
        a("---")
        a("")
        a(f"## {n}. {s['title']}")
        a("")
        a(f"*{KIND_LABEL[s['kind']]}" + (f" · {s['label']}" if s["label"] else "") + "*")
        a("")
        a("### 화면 구성")
        a("")
        L += outline_for(s)
        a("")
        a("### 말할 내용")
        a("")
        L += [f"- {t}" for t in s["notes"]["say"]]
        if s["notes"].get("cue"):
            a("")
            a("### 시연 큐")
            a("")
            L += [f"- {t}" for t in s["notes"]["cue"]]
        a("")
        a(s["notes"]["time"])
        a("")
    return "\n".join(L).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
LIGHT_RENDERERS = {
    "agenda": render_agenda, "arch": render_arch, "matrix": render_matrix, "app": render_app,
    "value": render_value, "flow": render_flow, "video": render_video, "code": render_code, "compare": render_compare,
    "pipeline": render_pipeline, "governance": render_governance, "summary": render_summary,
    "prep": render_prep, "trouble": render_trouble, "links": render_links,
}
DARK_RENDERERS = {"title": render_title, "closing": render_closing}


def patch_theme_fonts(prs) -> None:
    """Make Segoe UI / Malgun Gothic the theme fonts so new slides added in PowerPoint match the deck."""
    theme = prs.slide_master.part.part_related_by(RT.THEME)
    root = etree.fromstring(theme.blob)
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    for tag in ("majorFont", "minorFont"):
        font = root.find(f".//a:fontScheme/a:{tag}", ns)
        font.find("a:latin", ns).set("typeface", LATIN)
        font.find("a:ea", ns).set("typeface", EA)
    theme._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def rescale_template(prs) -> None:
    """The stock template is 4:3; stretch master/layout shapes to 16:9 so 'New slide' looks sane."""
    k = 12192000 / 9144000
    for part in [prs.slide_master, *prs.slide_layouts]:
        for sh in part.shapes:
            if sh.left is None or sh.width is None:
                continue
            sh.left, sh.width = int(sh.left * k), int(sh.width * k)


def normalize_zip(path: Path) -> None:
    """Rewrite the package with fixed timestamps so two builds are byte-identical."""
    with zipfile.ZipFile(path) as zin:
        items = [(i.filename, zin.read(i.filename)) for i in zin.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in items:
            zi = zipfile.ZipInfo(name, date_time=(2025, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            zout.writestr(zi, data)


def verify(path: Path, expected: int) -> tuple[list[str], dict]:
    prs = Presentation(str(path))
    sw, sh = prs.slide_width, prs.slide_height
    problems: list[str] = []
    sizes: dict[float, int] = {}
    if len(prs.slides) != expected:
        problems.append(f"slide count {len(prs.slides)} != {expected}")
    tol = 2000
    for i, slide in enumerate(prs.slides, 1):
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        if len(notes.strip()) < 40 or not re.search("[가-힣]", notes):
            problems.append(f"slide {i}: Korean speaker notes missing")
        if slide.shapes.title is None or not slide.shapes.title.text_frame.text.strip():
            problems.append(f"slide {i}: no title text")
        for shp in slide.shapes:
            box = (shp.left, shp.top, shp.width, shp.height)
            if None not in box and (box[0] < -tol or box[1] < -tol or box[0] + box[2] > sw + tol
                                    or box[1] + box[3] > sh + tol):
                problems.append(f"slide {i}: shape '{shp.name}' leaves the slide")
            frames = []
            if shp.has_text_frame:
                frames.append(shp.text_frame)
            if getattr(shp, "has_table", False) and shp.has_table:
                frames += [c.text_frame for r in shp.table.rows for c in r.cells]
            for tf in frames:
                for p in tf.paragraphs:
                    for r in p.runs:
                        if r.font.size is not None and r.text.strip():
                            pt = r.font.size.pt
                            sizes[pt] = sizes.get(pt, 0) + 1
    return problems, sizes


def build() -> int:
    slides = build_slides()
    compute_timing(slides)
    for s in slides:
        s["notes"] = {k: ([fill_timing(t) for t in v] if isinstance(v, list) else fill_timing(v))
                      for k, v in s["notes"].items()}
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    rescale_template(prs)
    patch_theme_fonts(prs)
    for n, s in enumerate(slides, 1):
        if s["kind"] in DARK_RENDERERS:
            slide = DARK_RENDERERS[s["kind"]](prs, s, n)
        else:
            slide, th = light_frame(prs, s, n)
            LIGHT_RENDERERS[s["kind"]](slide, s, th)
            footer(slide, n)
        set_notes(slide, s["notes"])
    cp = prs.core_properties
    cp.title = "GitHub Copilot in the Cloud — 데모 발표 자료"
    cp.subject = "GitHub Copilot, Microsoft Foundry, Azure Container Apps, AKS 라이브 데모"
    cp.author = "ghcp-in-the-cloud"
    cp.last_modified_by = "ghcp-in-the-cloud"
    cp.keywords = "GitHub Copilot, Foundry, Container Apps, AKS, OIDC"
    cp.language = "ko-KR"
    cp.created = cp.modified = datetime(2025, 1, 1, 0, 0, 0)
    cp.revision = 1
    prs.save(str(PPTX_PATH))
    normalize_zip(PPTX_PATH)
    MD_PATH.write_text(render_markdown(slides), encoding="utf-8")
    problems, sizes = verify(PPTX_PATH, len(slides))
    print(f"wrote {PPTX_PATH.relative_to(HERE.parent)} ({len(slides)} slides) and {MD_PATH.relative_to(HERE.parent)}")
    print("font sizes (pt: runs): " + ", ".join(f"{k:g}: {v}" for k, v in sorted(sizes.items())))
    for w in WARNINGS:
        print("layout warning:", w)
    for p in problems:
        print("ERROR:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(build())
