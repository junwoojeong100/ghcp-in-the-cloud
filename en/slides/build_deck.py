#!/usr/bin/env python3
"""Build the English presenter deck and its speaker-script outline.

    python en/slides/build_deck.py

Outputs (next to this file):
  demo-presentation-en.pptx   16:9 deck, native shapes only, speaker notes on every slide
  demo-presentation-en.md     outline + full English speaker script, generated from the same data

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
ROOT = HERE.parent.parent  # repository root; this script lives in en/slides/
PPTX_PATH = HERE / "demo-presentation-en.pptx"
MD_PATH = HERE / "demo-presentation-en.md"
VIDEO_DIR = HERE / "videos"


def OxmlElement(tag: str, attrs: dict | None = None):
    """python-pptx's OxmlElement without attributes, plus an attrs convenience."""
    el = _OxmlElement(tag)
    for key, value in (attrs or {}).items():
        el.set(key, value)
    return el


DECK_NAME = "GitHub Copilot in the Cloud · Demo Kit"
REPO = "github.com/junwoojeong100/ghcp-in-the-cloud"

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
SLIDE_W, SLIDE_H = 13.333, 7.5
MX = 0.6  # left/right margin
CW = SLIDE_W - 2 * MX  # content width
BODY_TOP, BODY_BOTTOM = 1.62, 6.82

LATIN, MONO = "Segoe UI", "Consolas"
EA = LATIN  # no East Asian text in this deck; keep the same face so nothing falls back

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
    if o >= 0x2E80 or 0x2190 <= o <= 0x21FF or 0x2460 <= o <= 0x27BF:  # wide glyphs, arrows, dingbats
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


LINE_H = 1.36  # font line height / font size (Segoe UI is about 1.33; kept generous for fallback fonts)
LINE_H_MONO = 1.24  # Consolas and DejaVu Sans Mono are about 1.17


def plain(text: str) -> str:
    return text.replace("`", "")


# ---------------------------------------------------------------------------
# Low-level XML helpers
# ---------------------------------------------------------------------------
def rgb(hexstr: str) -> RGBColor:
    return RGBColor.from_string(hexstr)


_AFTER_FONT = [qn(t) for t in ("a:sym", "a:hlinkClick", "a:hlinkMouseOver", "a:rtl", "a:extLst")]


def set_typefaces(rPr, latin: str) -> None:
    """python-pptx exposes only <a:latin>; write latin + east-asian + complex-script faces in schema order."""
    for tag in ("a:latin", "a:ea", "a:cs", "a:sym"):
        for el in rPr.findall(qn(tag)):
            rPr.remove(el)
    anchor = next((c for c in rPr if c.tag in _AFTER_FONT), None)
    for tag, face in (("a:latin", latin), ("a:ea", latin), ("a:cs", latin)):
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
    rPr.set("lang", "en-US")
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
    lines: list[tuple[str, bool]] = [("[What to say]", True)]
    lines += [(s, False) for s in notes["say"]]
    if notes.get("cue"):
        lines.append(("[Demo cues]", True))
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
        rPr.set("lang", "en-US")
        set_typefaces(rPr, LATIN)


# ===========================================================================
# DATA — edit here, then run `python en/slides/build_deck.py`.
# Timing follows the demo READMEs (en/demos/0N-*/README.md): each demo's "about N min" is the live part.
# ===========================================================================
UI_NOTE = "UI menu names may change, so look for the equivalent menu."

# step = (title, time, command/click lines, success criterion, in_lite)
DEMOS = [
    {
        "key": "copilot", "no": 1, "product": "GitHub Copilot", "short": "Copilot",
        "title": "From issue to PR, working with an AI teammate", "minutes": 7, "lite_min": 4,
        "needs": "GitHub repository + Copilot license", "independent": "No Azure needed",
        "cards": [
            ("Productivity", "Write an issue; the agent writes code and tests and opens a draft PR.", "Assign issue → draft PR"),
            ("Standards as code", "Keep instructions, prompts and custom agents in Git, reviewed in PRs.", "Config files under .github/"),
            ("Safe automation", "The agent pushes only to copilot/ branches. Humans approve and merge.", "CI + Copilot review"),
            ("Cloud connection", "Query Azure with Azure MCP; continue in the terminal with Copilot CLI.", "(optional) agent mode"),
        ],
        "steps": [
            ("Tour the config", "1 min",
             ["GitHub → .github/ folder", "copilot-instructions.md", "instructions/ prompts/ agents/"],
             "Rule list and applyTo lines are visible", True),
            ("Assign to Copilot", "1.5 min",
             ["scripts/create-demo-issues.sh", "  --apply --assign-copilot", "  --only 3"],
             "Copilot assigned; eyes reaction appears", False),
            ("Session · PR · CI", "2 min",
             ["View session", "Files changed", "Approve and run workflows"],
             "Draft PR open, all CI jobs green", True),
            ("Review and merge", "2 min",
             ["Ready for review", "Reviewers → Copilot", "Human approves → merge"],
             "Copilot comments; human approves, merges", True),
        ],
        "opt": ("Optional", "agent mode", "2 min",
                "VS Code Agent mode · /add-endpoint GET /api/version · MCP: List Servers → azure"),
        "flow_foot": UI_NOTE,
        "code": {
            "title": "Key config: team rules live in the repository",
            "blocks": [
                {"type": "code", "label": ".github/copilot-instructions.md (excerpt)", "lines": [
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
                {"type": "flow", "label": "From issue to merge", "items": [
                    "Issue", "@copilot", "Draft PR", "CI", "Copilot review", "Human merge"]},
            ],
            "callouts": [
                ("Write once, applies to all", "The agent, VS Code and code review read the same file."),
                ("Path-specific rules", "`applyTo` gives Python, Bicep and K8s their own rules."),
                ("A human is the last gate", "Agents cannot approve or merge."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "First up is GitHub Copilot. You hand one issue to an AI teammate, the Copilot cloud agent, and get the result back as a PR.",
                    "It is not only about speed. Your team's rules live in files inside the repository, so the agent follows the same rules as your people.",
                    "The last gate is always a human. The agent can neither approve nor merge.",
                ],
                "cue": ["Agent work takes a few minutes, so assign one issue 10-15 minutes before the demo and keep that PR tab open."],
                "time": "[Estimated time] about 1 min · Demo 1 total about 7 min",
            },
            "flow": {
                "say": [
                    "First show the Copilot configuration in the .github folder, then create an issue and assign it to Copilot.",
                    "The agent needs time, so jump to a PR you prepared earlier and walk through the session log, the changed files and CI.",
                    "Switch it to Ready for review, request a Copilot code review, and let a human make the call and merge.",
                ],
                "cue": [
                    "1) On GitHub, open .github/copilot-instructions.md → instructions/ → prompts/ → agents/ in that order.",
                    "2) scripts/create-demo-issues.sh --apply --assign-copilot --only 3 (or issue form → Assignees → Copilot).",
                    "3) On the timeline, View session → Files changed → if workflows are waiting, Approve and run workflows.",
                    "4) Ready for review → request Copilot under Reviewers (gh pr edit <PR number> --add-reviewer \"@copilot\"). If a ruleset is on, the person who tasked the agent cannot approve, so prepare an admin bypass or another account.",
                    "5) (Optional) In VS Code Agent mode, run /add-endpoint GET /api/version, then MCP: List Servers → azure.",
                    UI_NOTE + " Lite path: steps 1, 3 and 4 only.",
                ],
                "time": "[Estimated time] Steps total about 6.5 min (optional step 5 adds about 2 min)",
            },
            "code": {
                "say": [
                    "On the left is an excerpt of the repository-wide instructions. The file lives under .github, and both the agent and code review read it automatically.",
                    "To change a rule, edit this file in a PR. The coding rules people follow and the rules the agent follows live in one place.",
                    "The strip below is the flow you just saw. It starts with an issue and ends with a human merge.",
                ],
                "cue": ["Explaining this slide while the agent works overlaps with the wait and saves time."],
                "time": "[Estimated time] about 1 min (overlaps with the demo wait)",
            },
        },
    },
    {
        "key": "repo", "no": 2, "product": "GitHub Repo", "short": "Repo",
        "title": "Safe defaults: Rulesets, security, Codespaces", "minutes": 6, "lite_min": 0,
        "needs": "GitHub repository (admin access)", "independent": "No Azure needed",
        "cards": [
            ("Protect main", "A PR, required checks and a code owner review must pass before merge.", "Ruleset Active, 3 checks"),
            ("Clear ownership", "Owners of changed paths are auto-requested and must approve.", "One CODEOWNERS line"),
            ("Security scanning", "Turn on CodeQL, dependency review, Dependabot and secret scanning.", "Risky PR gets blocked"),
            ("One-click start", "Codespaces runs tests and the app with no setup; config is in files.", "Tests OK, /healthz 200"),
        ],
        "steps": [
            ("Start Codespaces", "1 min",
             ["Code → Codespaces → Create", "python -m unittest discover", "  -s app/tests -v"],
             "Tests pass, /healthz 200", False),
            ("Review Rulesets", "2 min",
             ["main-protection.json, CODEOWNERS", "scripts/apply-repo-settings.sh", "  (dry-run) → --apply"],
             "main-protection shows as Active", False),
            ("Risky PR", "2 min",
             ["demos/02-github-repo/risky-pr/", "  make-risky-pr.sh --apply", "→ inspect PR checks, merge box"],
             "Security checks flag it; merge is blocked", False),
            ("Dependabot", "1 min",
             [".github/dependabot.yml", "Security → Dependabot", "gh pr list --label dependencies"],
             "Update history or PRs are visible", False),
        ],
        "flow_foot": "Setup scripts change repository settings, so rehearse on a practice repo first. Never merge the [DEMO – DO NOT MERGE] PR.",
        "code": {
            "title": "Key config: Ruleset and CODEOWNERS",
            "blocks": [
                {"type": "rules", "label": ".github/rulesets/main-protection.json (summary)", "rows": [
                    ("pull_request", ["PR required · 1 approval", "Code owner review required"]),
                    ("required_status_checks", ["Unit tests", "Container build and smoke test", "IaC validation"]),
                    ("non_fast_forward", ["Force push blocked"]),
                    ("code_scanning", ["Blocks on CodeQL alert threshold"]),
                ]},
                {"type": "code", "label": ".github/CODEOWNERS", "lines": [
                    "/app/      @junwoojeong100",
                    "/.github/  @junwoojeong100",
                ]},
            ],
            "callouts": [
                ("Check = job name", "Ruleset check names must match CI job names."),
                ("Bypass is a trade-off", "Admin bypass is open (solo repo). Clear it on a team."),
                ("Settings as code", "Import the JSON or apply it with one script."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "Second is the GitHub repository itself. Good collaboration starts with defaults, not features.",
                    "Main protection, code owners and security checks are all defined as files and scripts in the repository, so you can take them straight to a new repo.",
                    "Codespaces gives you a development environment with nothing to install, and at the end I'll show how a deliberately risky PR gets filtered out.",
                ],
                "cue": [
                    "Create one Codespace ahead of time, and open the risky PR in advance so you have the screen ready after CodeQL analysis finishes.",
                    "The setup scripts change repository settings, so rehearse on a practice repo or a fork first.",
                ],
                "time": "[Estimated time] about 1 min · Demo 2 total about 6 min",
            },
            "flow": {
                "say": [
                    "In Codespaces, run the tests and the mock-mode app to show there is nothing to install.",
                    "Open the ruleset JSON and explain the reason behind each rule. For apply-repo-settings.sh, show only the dry-run output in front of the audience.",
                    "On the risky PR, point out CodeQL, Dependency review, Copilot review and the blocked merge box in turn. Do not use the bypass option that admins can see.",
                ],
                "cue": [
                    "1) Code → Codespaces → Create codespace on main → python -m unittest discover -s app/tests -v → LLM_BACKEND=mock python -m app.server (use a throwaway value for DEMO_PASSWORD).",
                    "2) .github/rulesets/main-protection.json, .github/CODEOWNERS → scripts/apply-repo-settings.sh (dry-run). Run --apply beforehand.",
                    "3) From a local terminal, run demos/02-github-repo/risky-pr/make-risky-pr.sh --apply. The PR title is [DEMO – DO NOT MERGE]; never merge it.",
                    "4) .github/dependabot.yml → Security → Dependabot, gh pr list --label dependencies.",
                    "Explain secret scanning and push protection in words only, without creating token-shaped strings. " + UI_NOTE,
                ],
                "time": "[Estimated time] Steps total about 6 min (1 + 2 + 2 + 1 min)",
            },
            "code": {
                "say": [
                    "The ruleset is a single JSON file. It holds the required PR, three required status checks, the code owner review, the block on force pushes and deletions, and the CodeQL alert threshold.",
                    "The required check names must match the display names of the CI jobs, so when you change a workflow, check the ruleset too.",
                    "CODEOWNERS assigns an owner to each path, and together with the ruleset's code owner review rule it makes approval mandatory. I will also be upfront that this demo is a one-person repository, so the admin PR bypass is left open.",
                ],
                "cue": ["For a team repository, tell the audience to empty bypass_actors and change CODEOWNERS to @org/team."],
                "time": "[Estimated time] about 1 min (overlaps with the demo wait)",
            },
        },
    },
    {
        "key": "actions", "no": 3, "product": "GitHub Actions", "short": "Actions",
        "title": "Secret-free CI/CD (OIDC) and reusable pipelines", "minutes": 7, "lite_min": 4,
        "needs": "GitHub, plus Azure to deploy", "independent": "CI needs no Azure",
        "cards": [
            ("Fast feedback", "4 independent jobs run in parallel; pip dependencies are cached.", "4 jobs run in parallel"),
            ("Secret-free deploys", "Azure trusts a short-lived OIDC token; only IDs are stored.", "Secrets list is empty"),
            ("Least privilege", "Read-only by default; the approved deploy job alone gets id-token: write.", "Approve under Review deployments"),
            ("Supply-chain proof", "Pin actions to commit SHAs and attest the deployed image's provenance.", "Attest the build provenance"),
        ],
        "steps": [
            ("Parallel CI run", "2 min",
             ["gh pr checks --watch", "(or the PR's Checks tab)"],
             "4 jobs green, 14 smoke checks pass", False),
            ("Secret-free trust", "2 min",
             ["scripts/setup-github-oidc.sh", "  (preview) → --apply", "Settings → Secrets: empty"],
             "Only variables are set; Secrets is empty", True),
            ("Approve → deploy", "3 min",
             ["gh workflow run deploy-aca.yml", "Review deployments → approve", "gh run watch"],
             "App version becomes the short commit SHA", True),
        ],
        "flow_foot": "Step 1 works without Azure. Steps 2 and 3 need a deployment target (scripts/deploy-aca.sh --yes).",
        "code": {
            "title": "Key code: zero stored secrets",
            "blocks": [
                {"type": "code", "label": ".github/workflows/deploy-aca.yml (excerpt)", "lines": [
                    "permissions:",
                    "  id-token: write   # allows OIDC token issuance",
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
                ("Zero stored secrets", "ID values go in `vars`, not in secrets."),
                ("Narrow trust scope", "Login is limited to jobs in `environment:azure-demo`."),
                ("Least privilege", "`id-token: write` goes only to the deploy job."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "Third is GitHub Actions. I'll show two things: validation that runs in parallel on every PR, and how to deploy to Azure without any stored secret.",
                    "OIDC lets Azure trust a short-lived token that GitHub issues for each job. The repository holds no password and no key, only identifiers such as the client ID, stored as variables.",
                    "There is an environment approval gate before deployment, so nothing touches Azure until a person approves.",
                ],
                "cue": ["Step 1 needs only GitHub. Steps 2 and 3 need an Azure subscription, and you create the deployment target beforehand with scripts/deploy-aca.sh --yes (mock backend)."],
                "time": "[Estimated time] about 1 min · Demo 3 total about 7 min",
            },
            "flow": {
                "say": [
                    "First, open a PR and show the four CI jobs running at the same time. No Azure credentials are needed.",
                    "Next, setup-github-oidc.sh configures the trust on the Azure side. When it finishes, check for yourselves that the Secrets list in Settings is empty.",
                    "Finally, run the deploy workflow and follow the sequence: environment approval, OIDC login, new revision.",
                ],
                "cue": [
                    "1) Open a PR with a small change → gh pr checks --watch → in Container build and smoke test, open the Smoke test step log (confirm 14 checks).",
                    "2) scripts/setup-github-oidc.sh (preview) → --apply → Settings → Secrets and variables → Actions: no secrets, only variables.",
                    "3) gh workflow run deploy-aca.yml → approve azure-demo under Review deployments → gh run watch → app URL and revision in the Summary, version on the app screen.",
                    UI_NOTE + " Lite path: steps 2 and 3 only (show a run you started earlier for step 3 and keep only the approval live).",
                ],
                "time": "[Estimated time] Steps total about 7 min (2 + 2 + 3 min)",
            },
            "code": {
                "say": [
                    "These few lines are the whole secret-free deployment. Granting id-token: write in permissions lets the job receive an OIDC token, and azure/login exchanges it for an Azure token.",
                    "The client-id, tenant-id and subscription-id are identifiers, not secrets, so they go in vars rather than secrets. The number of stored secrets is zero.",
                    "On the Azure side there is a federated credential whose subject is repo:<owner>/<repo>:environment:azure-demo, so only jobs that use this repository's azure-demo environment can log in.",
                ],
                "cue": ["The excerpt shows azure/login@v3 for readability; the real workflow pins the action to a commit SHA. <owner>/<repo> is your own repository value."],
                "time": "[Estimated time] about 1 min (overlaps with the demo wait)",
            },
        },
    },
    {
        "key": "foundry", "no": 4, "product": "Microsoft Foundry", "short": "Foundry",
        "title": "Model choice and secure, keyless access", "minutes": 7, "lite_min": 3,
        "needs": "Azure subscription + gpt-6.1-sol quota", "independent": "No GitHub, ACA or AKS",
        "cards": [
            ("Azure governance", "Use Entra ID, RBAC, quota and regions like any other Azure resource.", "gpt-6.1-sol in the deployment list"),
            ("Easy model swap", "The app knows only a deployment name; a model swap is one env var.", "Only FOUNDRY_MODEL changes"),
            ("effort = xhigh", "Set reasoning depth per request; tune from low to xhigh with an env var.", "effort: xhigh in /api/info"),
            ("Keyless auth", "Same code: az login locally, Managed Identity on ACA, Workload Identity on AKS.", "auth: entra-id in /api/info"),
        ],
        "steps": [
            ("Check deployment", "1.5 min",
             ["az cognitiveservices account", "  deployment list ... -o table", "(or the ai.azure.com portal)"],
             "gpt-6.1-sol deployed, no API key", False),
            ("Keyless call", "2.5 min",
             ["az login", "source .azure/foundry.env", "python -m app.server"],
             "Answer appears, instance is shown", True),
            ("Check /api/info", "1.5 min",
             ["curl -s -u \"demo:$DEMO_PASSWORD\"", "  http://127.0.0.1:8080/api/info"],
             "auth: entra-id, model, effort: xhigh", True),
        ],
        "opt": ("Optional", "swap model · effort", "1.5 min",
                "FOUNDRY_EFFORT=low python -m app.server · FOUNDRY_MODEL=<other deployment name>"),
        "flow_foot": "Finish the deployment (deploy-foundry.sh) before the demo. Role assignments can take a few minutes to propagate.",
        "code": {
            "title": "Key code: OpenAI-compatible endpoint + Entra ID",
            "blocks": [
                {"type": "code", "label": "app/server.py (excerpt, keyless path)", "lines": [
                    "token = get_bearer_token_provider(",
                    "    DefaultAzureCredential(),",
                    "    \"https://ai.azure.com/.default\")",
                    "headers = {\"Authorization\":",
                    "           f\"Bearer {token()}\"}",
                    "body = {",
                    "    \"model\": \"gpt-6.1-sol\",  # deployment name",
                    "    \"max_completion_tokens\": 4096,",
                    "    \"reasoning_effort\": \"xhigh\",",
                    "    \"messages\": messages}",
                    "url = f\"https://{resource}.services.ai.azure.com\"",
                    "      \"/openai/v1/chat/completions\"",
                ]},
            ],
            "callouts": [
                ("model = deployment name", "The Foundry deployment name, not the model ID."),
                ("No key anywhere", "`DefaultAzureCredential` obtains the token."),
                ("effort = xhigh", "The highest level GPT accepts. Deeper reasoning, but more time and tokens."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "Fourth is Microsoft Foundry. I'll show how to use gpt-6.1-sol inside Azure governance, without any key.",
                    "Azure's usual resource management applies as is: Entra ID authentication, RBAC, quota and regions. The app knows only the deployment name, not the model, so swapping models is just a configuration change.",
                    "Each request sets the effort level to get deep reasoning. The kit's default, max, is sent to GPT as xhigh, the highest level GPT accepts. I'll also mention that thinking this hard costs more time and more tokens.",
                ],
                "cue": [
                    "You can deploy gpt-6.1-sol in any subscription that has model quota, and the supported regions are eastus2, swedencentral and westus2. Claude needs an Enterprise or MCA-E subscription and acceptance of Anthropic's terms.",
                    "The deployment (scripts/deploy-foundry.sh) takes a few minutes, so finish it before the demo.",
                ],
                "time": "[Estimated time] about 1 min · Demo 4 total about 7 min",
            },
            "flow": {
                "say": [
                    "Check the deployed model, and first show that the connection file contains no API key.",
                    "With only az login done, start the local app and ask a question. There is no key in the code; DefaultAzureCredential fetches the token.",
                    "Finally, check in /api/info that the auth method is entra-id and that the model and effort match the configuration.",
                ],
                "cue": [
                    "1) cat .azure/foundry.env → source .azure/foundry.env → az cognitiveservices account deployment list --resource-group \"$FOUNDRY_RESOURCE_GROUP\" --name \"$FOUNDRY_RESOURCE\" --output table.",
                    "2) az login → source .azure/foundry.env → export DEMO_PASSWORD='<any value>' → python -m app.server → http://127.0.0.1:8080 (user demo) → ask a question.",
                    "3) curl -s -u \"demo:$DEMO_PASSWORD\" http://127.0.0.1:8080/api/info → backend foundry · auth entra-id · model gpt-6.1-sol · effort xhigh.",
                    "4) (Optional) Compare the same question with FOUNDRY_EFFORT=low python -m app.server.",
                    "If you just assigned the role, propagation can take a few minutes and the first call may fail with a permissions error. Lite path: steps 2 and 3.",
                ],
                "time": "[Estimated time] Steps total about 5.5 min + optional 1.5 min = about 7 min",
            },
            "code": {
                "say": [
                    "The code is these twelve lines. get_bearer_token_provider gets an Entra ID token through DefaultAzureCredential, and the token goes in the Authorization header of a call to Foundry's OpenAI-compatible endpoint. There is no API key anywhere.",
                    "The model argument is the Foundry deployment name, not the model ID. If you deployed a different model, just change the name.",
                    "reasoning_effort sets the reasoning depth; to lower it, change only the environment variable.",
                ],
                "cue": [
                    "As a teaser for the next two demos, say that the same DefaultAzureCredential path produces the token from az login locally, from Managed Identity on ACA and from Workload Identity on AKS.",
                    "The only role needed is Cognitive Services User. An API key (FOUNDRY_API_KEY) is just an optional alternative. A Claude deployment whose name starts with claude automatically uses the AnthropicFoundry path.",
                ],
                "time": "[Estimated time] about 1 min (overlaps with the demo wait)",
            },
        },
    },
    {
        "key": "aca", "no": 5, "product": "Azure Container Apps", "short": "ACA",
        "title": "Serverless, scale-to-zero, revision canaries", "minutes": 7, "lite_min": 4,
        "needs": "Azure subscription", "independent": "No Foundry needed (mock backend)",
        "cards": [
            ("No cluster ops", "Upload an image and settings, get an HTTPS URL. No nodes to manage.", "deploy-aca.sh → URL"),
            ("Scale-to-zero", "With no requests, replicas drop to 0 and restart on the next request.", "Replicas 0 → 1"),
            ("Revision canary", "Send some traffic to a new revision; promote or roll back at once.", "Probe confirms the 90/10 split"),
            ("Identity and logs", "Managed Identity calls Foundry keylessly; logs go to Log Analytics.", "(optional) auth: entra-id"),
        ],
        "steps": [
            ("Scale-to-zero", "1.5 min",
             ["az containerapp revision list", "  -g $RG -n $APP -o table", "curl $APP_URL/healthz  # twice"],
             "Replicas 0 → slow first request → 1", True),
            ("Check deployment", "1 min",
             ["Open $APP_URL in a browser", "scripts/smoke-test.sh $APP_URL", "  --expect-backend mock"],
             "Platform chip shows aca, all checks pass", False),
            ("Revision canary", "3 min",
             ["scripts/aca-canary.sh", "  deploy v2 → canary 10 → probe 30", "  → promote  (or rollback)"],
             "v1 and v2 mix; only v2 after promote", True),
            ("Load & scale-out", "1.5 min",
             ["scripts/load-test.sh", "  --url $APP_URL --duration 120", "  --concurrency 20"],
             "Replicas increase (max 5)", False),
        ],
        "flow_foot": "After deploying, send no requests until the demo (a browser tab or the smoke test counts as a request). That is how you can show 0 replicas.",
        "code": {
            "title": "Key commands: canary and scale rules",
            "blocks": [
                {"type": "code", "label": "scripts/aca-canary.sh · az containerapp", "lines": [
                    "scripts/aca-canary.sh deploy v2  # new revision, 0%",
                    "scripts/aca-canary.sh canary 10  # v2 10% · previous 90%",
                    "scripts/aca-canary.sh probe 30   # tally 30 calls",
                    "scripts/aca-canary.sh promote    # v2 100% (or rollback)",
                    "",
                    "# az commands the script uses",
                    "az containerapp revision list -g $RG -n $APP -o table",
                    "az containerapp ingress traffic set -g $RG -n $APP \\",
                    "  --label-weight blue=90 green=10",
                ]},
            ],
            "callouts": [
                ("Scale-to-zero", "min 0 · max 5; idle replicas drop to 0."),
                ("Revision = snapshot", "A new version is a new revision; check it by label first."),
                ("Instant rollback", "`rollback` sends 100% back to the previous revision."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "Fifth is Azure Container Apps, a serverless container service that serves your containers over HTTPS without you running a cluster.",
                    "When there are no requests, replicas shrink to zero and compute cost stops, and you roll out a new version as a revision and split the traffic.",
                    "The point of this demo is that canary and rollback are just configuration changes.",
                ],
                "cue": ["After deploying, send no requests to the app until the demo starts (a browser tab or the smoke test counts as a request). That is how you can show 0 replicas."],
                "time": "[Estimated time] about 1 min · Demo 5 total about 7 min",
            },
            "flow": {
                "say": [
                    "First, with no requests at all, show that Replicas is 0, then watch the cold start on the slow first request.",
                    "Next is the revision canary. Deploy v2 at 0%, send only 10% to it, then promote it or roll back instantly.",
                    "Finally, apply load and watch the replicas increase.",
                ],
                "cue": [
                    "1) az containerapp revision list --resource-group rg-cloud-copilot-aca --name cloud-copilot-demo -o table shows Replicas 0 → curl $APP_URL/healthz twice (slow first, fast second) → revision list again shows Replicas 1.",
                    "2) Open $APP_URL in the browser → platform chip says aca → scripts/smoke-test.sh \"$APP_URL\" --wait 60 --expect-backend mock.",
                    "3) scripts/aca-canary.sh status → deploy v2 → canary 10 → the browser's 'Show traffic distribution' button or probe 30 → promote → probe → rollback.",
                    "4) In terminal A, repeat revision list every 5 seconds; in terminal B, run scripts/load-test.sh --url \"$APP_URL\" --duration 120 --concurrency 20.",
                    "Lite path: steps 1 and 3. If there is no time to wait, explain step 1 in words.",
                ],
                "time": "[Estimated time] Steps total about 7 min (1.5 + 1 + 3 + 1.5 min)",
            },
            "code": {
                "say": [
                    "The canary is four script lines. deploy creates the new revision at 0% traffic, canary 10 splits traffic 10 to 90, and probe tallies the call ratio. The last step is promote or rollback.",
                    "What the script uses is the az containerapp traffic-split command, with label weights dividing traffic between blue and green.",
                    "The scale rule is in Bicep: minimum replicas 0, maximum 5, and one replica per 5 concurrent requests.",
                ],
                "cue": ["Add that rollback only moves 100% back to the previous revision; the new revision is still there and can be promoted again."],
                "time": "[Estimated time] about 1 min (overlaps with the demo wait)",
            },
        },
    },
    {
        "key": "aks", "no": 6, "product": "AKS", "short": "AKS",
        "title": "Rolling updates, autoscaling, Workload Identity", "minutes": 8, "lite_min": 0,
        "needs": "Azure subscription", "independent": "No Foundry needed (mock backend)",
        "cards": [
            ("Standard Kubernetes", "Keep kubectl, manifests and the ecosystem; Azure runs the control plane.", "kubectl get deploy,hpa,pdb"),
            ("Rolling updates", "Old pods stop only once new ones are ready; roll back in one line.", "v1 → v2 → rollback"),
            ("Autoscaling", "HPA scales 2 to 5 pods at 50% CPU; the autoscaler handles nodes.", "REPLICAS increases"),
            ("Keyless identity", "Workload Identity, no secrets; cluster access only through Entra ID.", "SA annotation + injected env vars"),
        ],
        "steps": [
            ("Tour the cluster", "1.5 min",
             ["kubectl get deploy,hpa,pdb,svc,pods", "kubectl port-forward \\", "  svc/cloud-copilot-demo 8080:80"],
             "2+ pods Running, platform chip aks", False),
            ("HPA autoscaling", "2.5 min",
             ["kubectl get hpa,pods -w", "kubectl scale deploy/load-generator", "  --replicas=1"],
             "REPLICAS grows from 2 (max 5)", False),
            ("Rolling update", "2.5 min",
             ["kubectl set image \\", "  deploy/cloud-copilot-demo \\", "  app=$IMG:v2"],
             "READY holds, v2 rolls out, undo reverts", False),
            ("Workload Identity", "1 min",
             ["kubectl get serviceaccount \\", "  cloud-copilot-demo -o yaml", "→ check AZURE_* vars in the pod"],
             "client-id annotation and injected AZURE_*", False),
        ],
        "opt": ("Optional", "Secure defaults", "1 min",
                "Apply a privileged pod → Forbidden: violates PodSecurity \"restricted\""),
        "flow_foot": "kubectl uses --namespace cloud-copilot-demo (omitted) · $IMG = $ACR_SERVER/cloud-copilot-demo",
        "code": {
            "title": "Key config: Workload Identity and HPA",
            "blocks": [
                {"type": "code", "label": "infra/aks/k8s/base (excerpt)", "lines": [
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
                {"type": "code", "label": "Observe", "lines": [
                    "kubectl get hpa,pods -n cloud-copilot-demo --watch",
                ]},
            ],
            "callouts": [
                ("Workload Identity", "The pod's ServiceAccount token is exchanged for an Entra ID token. No key anywhere."),
                ("HPA · PDB", "Scales between 2 and 5 pods at 50% CPU; PDB `minAvailable: 1` protects the last pod."),
            ],
        },
        "notes": {
            "value": {
                "say": [
                    "Sixth is AKS. I'll show you what Kubernetes does well: zero-downtime rolling updates, autoscaling under load, and secret-free Workload Identity.",
                    "Azure runs the control plane, and access is only through Entra ID and Azure RBAC, with no local accounts. Pod Security restricted is enforced on the namespace.",
                    "AKS takes more effort than ACA, but you get more control in return. I'll pick that up again on the final comparison slide.",
                ],
                "cue": [
                    "Finish the cluster deployment (5-10 minutes) and the v2 image build (az acr build ... --image cloud-copilot-demo:v2 --build-arg APP_VERSION=v2) before the demo.",
                    "Prepare three terminals: one for commands, one for --watch and one for port-forward.",
                ],
                "time": "[Estimated time] about 1 min · Demo 6 total about 8 min",
            },
            "flow": {
                "say": [
                    "First, see what is running on the cluster in one screen, then connect to the app with port forwarding. The service is deliberately ClusterIP so it is not exposed to the internet.",
                    "Start the load generator and HPA adds pods; switch the image to v2 and old pods go down only after new pods are ready. If something is wrong, one rollout undo line brings you back.",
                    "Finally, show the ServiceAccount annotation and the values injected into the pod, and confirm that there is no secret anywhere.",
                ],
                "cue": [
                    "1) kubectl get nodes → kubectl get deployment,hpa,pdb,service,pods --namespace cloud-copilot-demo → kubectl port-forward svc/cloud-copilot-demo 8080:80 --namespace cloud-copilot-demo → http://localhost:8080 (user demo).",
                    "2) Terminal A: kubectl get hpa,pods --namespace cloud-copilot-demo --watch / Terminal B: kubectl scale deployment/load-generator --replicas=1 --namespace cloud-copilot-demo → after checking, set --replicas=0.",
                    "3) kubectl set image deployment/cloud-copilot-demo app=\"$ACR_SERVER/cloud-copilot-demo:v2\" --namespace cloud-copilot-demo → kubectl rollout status → kubectl rollout undo deployment/cloud-copilot-demo.",
                    "4) kubectl get serviceaccount cloud-copilot-demo --namespace cloud-copilot-demo -o yaml, then filter the pod's environment to show only the injected AZURE_* variables. Never run a bare printenv while sharing your screen (it exposes DEMO_PASSWORD).",
                    "(Optional) Step 5 of the README: applying a privileged pod prints Forbidden, violates PodSecurity \"restricted:latest\".",
                ],
                "time": "[Estimated time] Steps total about 7.5 min (optional step adds about 1 min)",
            },
            "code": {
                "say": [
                    "Workload Identity comes together from three settings: the client-id annotation on the ServiceAccount, the use label on the pod template, and the federated credential on the Azure side.",
                    "The pod exchanges its ServiceAccount token for an Entra ID token, so there is nowhere to put a key or a password.",
                    "HPA scales pods between 2 and 5 based on 50% CPU utilization, and the PDB protects the last pod.",
                ],
                "cue": ["The client-id in the annotation is replaced with the Managed Identity value the deploy script creates (the repository holds a placeholder)."],
                "time": "[Estimated time] about 1 min (overlaps with the demo wait)",
            },
        },
    },
]
DEMO_BY_KEY = {d["key"]: d for d in DEMOS}

# ---------------------------------------------------------------------------
# Fixed (non-demo) slides
# ---------------------------------------------------------------------------
AGENDA_WHAT = {
    "copilot": "Issue → agent PR → review → human merge",
    "repo": "Rulesets · CODEOWNERS · blocking risky PRs",
    "actions": "Parallel CI and secret-free OIDC deploys",
    "foundry": "Keyless model calls · /api/info",
    "aca": "Scale-to-zero · revision canary",
    "aks": "Rolling updates · autoscaling · Workload Identity",
}
LITE_ORDER = ["copilot", "actions", "foundry", "aca"]  # Lite path (en/DEMO_GUIDE.md)

FIXED = {
    "title": {
        "title": "GitHub Copilot in the Cloud",
        "subtitle": "From idea to production",
        "tagline": "GitHub × Microsoft Foundry × AKS / ACA",
        "chips": [("GitHub Copilot", "copilot"), ("GitHub Repo", "repo"), ("GitHub Actions", "actions"),
                  ("Microsoft Foundry", "foundry"), ("Container Apps", "aca"), ("AKS", "aks")],
        "foot": "6 live demos · Full about 42 min · Lite about 15 min",
        "notes": {
            "say": [
                "Hello, everyone. Today I'll show you, live, how a single idea travels all the way to production with GitHub and Azure.",
                "The slides are short, and most of the time goes to live demos. We'll go through six services in order, but each demo is built so it can also run on its own.",
            ],
            "cue": [
                "Before you start: enlarge the terminal font and turn off notifications. Only export DEMO_PASSWORD; never print it on screen (no printenv).",
                "Before starting the slide show, confirm that you have already assigned the Demo 1 issue.",
            ],
            "time": "[Estimated time] about 0.5 min",
        },
    },
    "agenda": {
        "title": "Today's journey: 6 demos, two paths",
        "notes": {
            "say": [
                "We'll cover six things in the order that runs from development to operations: build with Copilot, protect with repository rules, deploy with Actions, connect a model with Foundry, and run on Container Apps and AKS.",
                "Running them all back to back takes about 42 minutes of demos. If time is short, take the Lite path: only Copilot, Actions, Foundry and Container Apps, core steps only, in about 15 minutes.",
                "The opening and wrap-up slides take about {extra} minutes on top of that. In each demo, spend about a minute on the value slide and cover the key-code slide while you wait during the demo.",
            ],
            "cue": [
                "Say out loud which path fits today's audience (Full or Lite). On Lite, run only the steps marked 'Lite' on each flow slide.",
                "To fit Lite into a 15-minute slot, cut slides 3-5 and 30-33 to a sentence or two, or skip them, and finish with slide 34.",
            ],
            "time": "[Estimated time] about 1 min",
        },
    },
    "arch": {
        "title": "Code on GitHub, runtime and AI on Azure",
        "notes": {
            "say": [
                "Let's read it from the left. Developers work locally or in Codespaces, and the code goes to a GitHub repository. Copilot opens PRs, rulesets and CI check them, and Actions deploys.",
                "On the right is Azure. Actions pushes the image to ACR, Container Apps and AKS pull and run that image, and the app calls gpt-6.1-sol on Microsoft Foundry.",
                "Look at the orange lines. All of them are identity flows, and there are no stored keys: locally it is az login, Actions uses OIDC, Container Apps uses Managed Identity and AKS uses Workload Identity.",
            ],
            "cue": ["Trace the lines with your finger or pointer as you speak. Thirty seconds is enough to point out the five orange lines one by one."],
            "time": "[Estimated time] about 1.5 min",
        },
    },
    "matrix": {
        "title": "Standalone demos: any demo can run on its own",
        "rows": [
            ("1 Copilot", "GitHub repository, Copilot license", "Issue to PR inside GitHub, no Azure"),
            ("2 Repo", "GitHub repository (admin access)", "Settings are files; mock app in Codespaces"),
            ("3 Actions", "GitHub, plus Azure for steps 2-3", "CI needs no Azure; deploy needs a target"),
            ("4 Foundry", "Azure subscription + gpt-6.1-sol quota", "Just az login and the local app"),
            ("5 ACA", "Azure subscription", "Mock backend, so no Foundry needed"),
            ("6 AKS", "Azure subscription", "Same image, same mock backend"),
        ],
        "keys": ["copilot", "repo", "actions", "foundry", "aca", "aks"],
        "foot": "`LLM_BACKEND=mock` — the whole app runs without Foundry (default for CI and demos 5 and 6)",
        "notes": {
            "say": [
                "The design principle of this kit is standalone demos. No demo requires you to run another one first.",
                "The trick is the mock backend. With LLM_BACKEND set to mock, the whole app runs without Foundry or Azure, so CI and the Container Apps and AKS demos run with no model-call cost.",
                "So you can pick demos to fit your audience and your time. The accounts and subscriptions you need are in the table.",
            ],
            "cue": ["Point once to the standalone-run matrix in en/README.md, then move on."],
            "time": "[Estimated time] about 0.5 min",
        },
    },
    "app": {
        "title": "Sample app: one image runs everywhere",
        "notes": {
            "say": [
                "The app used in the demos is a very small chat app. When you ask a question in the browser, /api/chat calls gpt-6.1-sol on Microsoft Foundry at a high effort level, and the page shows the answer together with which platform and revision responded.",
                "There are three endpoints. /healthz is for platform probes, so it has no authentication. /api/info shows settings such as backend, auth, model and effort, and /api/chat sits behind the demo authentication.",
                "There is one container image. The same image runs locally, in Codespaces, on Container Apps and on AKS. The only difference is how it obtains the Entra ID token.",
            ],
            "cue": ["Don't open the app here. It first runs in Demo 4, so just point out the structure and move on."],
            "time": "[Estimated time] about 1 min",
        },
    },
    "compare": {
        "title": "Selection guide: Container Apps vs AKS",
        "rows": [
            ("Operational load", "Low · no node management", "High · you run clusters and nodes"),
            ("Control · scaling", "App-centric, rule-based scaling", "Full Kubernetes API, extensible"),
            ("Scale-to-zero", "Built in (min replicas 0)", "HPA min 1; zero needs KEDA"),
            ("HTTPS · ingress", "Built in, automatic HTTPS URL", "Configure ingress and certs"),
            ("Networking", "Managed, e.g. VNet integration", "CNI, policies, private clusters"),
            ("Cost model", "Pay for use, down to 0 when idle", "Per running node, always-on cost"),
            ("Best fit", "HTTP APIs, events, fast launch", "Complex services, platform team"),
        ],
        "foot": "The same image runs on both. Start with ACA, move to AKS for more control.",
        "notes": {
            "say": [
                "These two services are not rivals. The choice trades operational load against level of control. Container Apps gets an HTTPS service up fast without you worrying about a cluster, and shrinks to zero when unused.",
                "AKS gives you every Kubernetes feature, but you have to run the cluster and its nodes. If you need networking control, custom controllers or platform-team standards, AKS is the right fit.",
                "As you saw today, the same image runs on both, so you can start with ACA and move over when the need arises.",
            ],
            "cue": ["Don't quote cost figures; compare only the models (usage-based versus node-based). Point the audience to the Azure pricing calculator for exact costs."],
            "time": "[Estimated time] about 1.5 min",
        },
    },
    "pipeline": {
        "title": "End-to-end: from idea to Foundry",
        "stages": [
            ("Idea", "", "neutral", ""),
            ("Issue", "", "repo", "Demo 1"),
            ("Copilot", "PR", "copilot", "Demo 1"),
            ("Rulesets", "+ CI", "repo", "Demo 2"),
            ("Actions", "(OIDC)", "actions", "Demo 3"),
            ("ACR", "", "neutral", "Demo 3"),
            ("ACA", "or AKS", "aca", "Demo 5·6"),
            ("Foundry", "", "foundry", "Demo 4"),
        ],
        "groups": [
            ("Plan", "Turn the idea into an issue.", "copilot"),
            ("Build and verify", "Copilot opens the PR; rulesets and CI verify it.", "repo"),
            ("Deploy", "Sign in with OIDC and push the image to ACR.", "actions"),
            ("Run and AI", "Run the same image; call Foundry without keys.", "aca"),
        ],
        "trust_label": "Keyless identity paths",
        "trust": ["Local · az login", "Actions · OIDC", "ACA · Managed ID", "AKS · Workload ID"],
        "notes": {
            "say": [
                "Here is everything you saw today in one line. An idea becomes an issue, Copilot opens the PR, and rulesets and CI verify it.",
                "Code that passes is deployed when Actions signs in to Azure with OIDC and pushes the image to ACR. Container Apps or AKS runs that image, and the app calls gpt-6.1-sol on Foundry without keys.",
                "Look at the strip below. From a person's login through CI to the containers, every leg is connected by identity instead of keys. This is the biggest message I want you to take away today.",
            ],
            "cue": ["Follow the 'Demo N' badge under each stage to point out which demo it came from."],
            "time": "[Estimated time] about 1 min",
        },
    },
    "governance": {
        "title": "Security, cost and governance checklist",
        "cards": [
            ("Keyless authentication", "Entra ID instead of API keys: az login, Managed Identity, Workload Identity, OIDC."),
            ("Least privilege", "Give `id-token: write` only to the deploy job and assign roles at the narrowest scope."),
            ("Model terms and subscription", "gpt-6.1-sol needs only quota. Claude needs an Enterprise or MCA-E subscription and Anthropic's terms."),
            ("Quota and regions", "Check supported regions and model quota first; if short, change capacity or region."),
            ("Public endpoint", "Only `/healthz` is open; the rest needs a demo password. Use org auth in production."),
            ("Cleanup and cost", "Run `cleanup.sh` right after the demo. AKS keeps billing and Foundry needs a purge."),
        ],
        "notes": {
            "say": [
                "Here are six things to check before you adopt this. First, there are no keys. Second, grant permissions only at the scope you need. Third, model terms and subscription: gpt-6.1-sol needs only model quota, while Claude requires an Enterprise or MCA-E subscription and acceptance of Anthropic's terms.",
                "Fourth, check model quota and supported regions in advance. Fifth, the demo app runs at a public address, so every path except /healthz is protected with the demo password; in production, replace it with your organization's authentication.",
                "Last is cleanup. AKS nodes keep generating cost, so delete everything with cleanup.sh as soon as the demo ends, and for Foundry you also need to purge before the quota comes back.",
            ],
            "cue": ["Right after the demo, run it with a target, such as scripts/cleanup.sh aks --yes (all cleans up everything). It has a safeguard that refuses to delete resource groups without the demo=ghcp-in-the-cloud tag."],
            "time": "[Estimated time] about 1 min",
        },
    },
    "summary": {
        "title": "Key benefits of each service on one slide",
        "rows": [
            ("copilot", "GitHub Copilot", "Issues become PRs; rules live in repo instructions", "Agent PR + Copilot review"),
            ("repo", "GitHub Repo", "Main protection, code owners and security checks as code", "Risky PR cannot merge"),
            ("actions", "GitHub Actions", "Parallel CI, secret-free OIDC deploys", "Secrets list is empty"),
            ("foundry", "Microsoft Foundry", "gpt-6.1-sol under Azure governance, called without keys", "auth: entra-id in /api/info"),
            ("aca", "Container Apps", "Serverless: scale-to-zero and canaries", "Replicas 0 → 1, 90/10"),
            ("aks", "AKS", "Rolling updates, HPA, Workload Identity", "READY holds, pods scale up"),
        ],
        "notes": {
            "say": [
                "Let me wrap up on one slide. Each service's benefit is paired with the evidence you saw on screen today.",
                "Copilot turns issues into PRs, the repository enforces rules as code, Actions deploys without secrets, Foundry lets you use a model without keys, and Container Apps and AKS run the same image with different operating models.",
            ],
            "cue": ["Read the 'Evidence from the demo' column on the right so the audience remembers it."],
            "time": "[Estimated time] about 1 min",
        },
    },
    "closing": {
        "title": "Get started · Q&A",
        "repo_label": "Repository",
        "items": [
            ("en/README.md", "Overview, quick start, matrix"),
            ("en/demos/", "Guides for all 6 demos"),
            ("en/slides/", "This deck and its generator"),
            ("en/DEMO_GUIDE.md", "Full/Lite timings and prep"),
        ],
        "start_label": "Start in 5 minutes (no Azure)",
        "start": [
            "python -m unittest discover -s app/tests -v",
            "LLM_BACKEND=mock python -m app.server",
        ],
        "foot": "Clean up: scripts/cleanup.sh <aca|aks|foundry|oidc|all>",
        "notes": {
            "say": [
                "The easiest way to start is to open the repository and follow the quick start in en/README.md. You can run the app and the tests first with the mock backend, without Azure.",
                "The en/demos folder has the guides for the six demos you saw today, and the en/slides folder has this deck and its generator script. Take them and adapt them as you like.",
                "I'll take your questions now.",
            ],
            "cue": [
                "For frequent Q&A questions, answer from the troubleshooting and checklist slides in the appendix.",
                "After the talk, always clean up the Azure resources with scripts/cleanup.sh.",
            ],
            "time": "[Estimated time] varies with Q&A (about 1 min for the slide itself)",
        },
    },
    "prep": {
        "title": "Appendix A. Pre-demo checklist",
        "cols": [
            ("GitHub", "repo", [
                "Practice repository (fork or template)",
                "Repository admin access",
                "Copilot license (cloud agent)",
                "`gh auth login`",
                "Reviewer set on the `azure-demo` environment",
            ]),
            ("Azure", "aca", [
                "Subscription Owner (or Contributor + User Access Administrator)",
                "Subscription and region with gpt-6.1-sol quota (Claude needs Enterprise or MCA-E)",
                "Deploy 30-60 min ahead: foundry → aca → aks → oidc",
            ]),
            ("Local tools", "aks", [
                "bash 4+, Python 3.12",
                "`az`, `gh`, `jq`",
                "`kubectl` + `kubelogin`, `docker` (optional)",
                "Enlarge terminal font, mute notifications",
                "Only export `DEMO_PASSWORD` (never print it)",
            ]),
        ],
        "notes": {
            "say": [
                "These are the items to check before the talk. If a question comes up, come back to this page to answer it.",
                "Foundry, Container Apps and AKS take a long time to deploy, so create them 30 to 60 minutes before the demo. The OIDC setup needs the deployment target to exist first, so do it last.",
            ],
            "cue": ["The detailed checklist and the per-demo prep are in the 'Before you present' checklist in en/DEMO_GUIDE.md."],
            "time": "[Estimated time] Appendix (skipped during the talk)",
        },
    },
    "trouble": {
        "title": "Appendix B. Troubleshooting top 5",
        "rows": [
            ("RBAC propagation delay", "403 · AuthorizationFailed", "Right after a role assignment it takes a few minutes. Try again shortly."),
            ("Model quota · region", "Deployment fails with a quota or capacity error", "Lower `CAPACITY` or change `LOCATION`. (Claude needs Enterprise or MCA-E.)"),
            ("ACR name conflict", "Name already in use", "Names are globally unique. Change `NAME_PREFIX` and deploy again."),
            ("kubelogin · Azure RBAC", "kubectl authentication error", "`az login` → `az aks install-cli` → `kubelogin convert-kubeconfig --login azurecli`"),
            ("OIDC subject mismatch", "AADSTS70021", "Check the repository and environment names: `setup-github-oidc.sh --apply --repo <owner>/<name>`"),
        ],
        "notes": {
            "say": [
                "These are the five problems you hit most often in rehearsal. Most go away if you wait a few minutes or fix a name.",
                "If you just assigned a role, propagation takes a few minutes. A model deploys only when quota and region line up, and an ACR name must be unique worldwide.",
                "AKS is accessed only through Entra ID and Azure RBAC, so you need kubelogin, and if OIDC login fails, check the repository name and environment name in the subject first.",
            ],
            "cue": ["Each demo guide has a troubleshooting table. For symptom-by-symptom fixes, point people to that demo's README."],
            "time": "[Estimated time] Appendix (only when needed)",
        },
    },
    "links": {
        "title": "Appendix C. Reference links",
        "rows": [
            ("GitHub Copilot", "docs.github.com/copilot", "https://docs.github.com/copilot"),
            ("GitHub Actions", "docs.github.com/actions", "https://docs.github.com/actions"),
            ("GitHub repositories", "docs.github.com/repositories", "https://docs.github.com/repositories"),
            ("Code security", "docs.github.com/code-security", "https://docs.github.com/code-security"),
            ("Microsoft Foundry", "ai.azure.com", "https://ai.azure.com"),
            ("Azure Container Apps", "learn.microsoft.com/azure/container-apps", "https://learn.microsoft.com/azure/container-apps"),
            ("AKS", "learn.microsoft.com/azure/aks", "https://learn.microsoft.com/azure/aks"),
            ("Workload Identity", "learn.microsoft.com/entra/workload-id", "https://learn.microsoft.com/entra/workload-id"),
            ("This demo kit", REPO, "https://" + REPO),
        ],
        "foot": "Find each product's latest docs from the start pages above. UI and feature names may change.",
        "notes": {
            "say": [
                "These are starting pages for anyone who wants to go deeper. Detailed doc URLs change often, so I listed only the landing page link for each product's docs.",
            ],
            "cue": ["The links are clickable in PowerPoint. For the Foundry docs, search for 'Microsoft Foundry' on learn.microsoft.com."],
            "time": "[Estimated time] Appendix",
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
    add("agenda", f["agenda"]["title"], "Opening · Today's journey", "neutral", f["agenda"]["notes"])
    add("arch", f["arch"]["title"], "Opening · Big picture", "neutral", f["arch"]["notes"])
    add("matrix", f["matrix"]["title"], "Opening · Standalone demos", "neutral", f["matrix"]["notes"], **f["matrix"])
    add("app", f["app"]["title"], "Opening · Sample app", "neutral", f["app"]["notes"])
    for d in DEMOS:
        tag = f"Demo {d['no']} / 6 · {d['product']}"
        add("value", d["title"], tag + " · Value", d["key"], d["notes"]["value"], demo=d)
        add("flow", f"Demo flow: {d['product']}", tag + " · Demo flow", d["key"], d["notes"]["flow"], demo=d)
        video_path = VIDEO_DIR / f"{d['key']}.mp4"
        add("video", f"Demo video: {d['product']}", tag + " · Recorded video", d["key"],
            {
                "say": [("This is a screen recording of the real demo run. It follows the demo order in that demo's README."
                         if video_path.is_file() else
                         "There is no recording of this demo yet. Record it by following the demo order and success criteria in the recording guide, then insert it.")],
                "cue": [f"If en/slides/videos/{video_path.name} is missing, record the demo by following the recording guide, then rebuild."],
                "time": "[Estimated time] Optional playback · not included in the demo time",
            },
            demo=d, video_path=video_path)
        add("code", d["code"]["title"], tag + " · Key code", d["key"], d["notes"]["code"], demo=d)
    add("compare", f["compare"]["title"], "Wrap-up · Selection guide", "aks", f["compare"]["notes"], **f["compare"])
    add("pipeline", f["pipeline"]["title"], "Wrap-up · End-to-end", "neutral", f["pipeline"]["notes"], **f["pipeline"])
    add("governance", f["governance"]["title"], "Wrap-up · Governance", "neutral", f["governance"]["notes"], **f["governance"])
    add("summary", f["summary"]["title"], "Wrap-up · Key benefits", "neutral", f["summary"]["notes"], **f["summary"])
    add("closing", f["closing"]["title"], "", "copilot", f["closing"]["notes"], **f["closing"])
    add("prep", f["prep"]["title"], "Appendix", "neutral", f["prep"]["notes"], **f["prep"])
    add("trouble", f["trouble"]["title"], "Appendix", "neutral", f["trouble"]["notes"], **f["trouble"])
    add("links", f["links"]["title"], "Appendix", "neutral", f["links"]["notes"], **f["links"])
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
            alt=f"Demo {d['no']}: {d['product']}, about {d['minutes']} min")
    tx, tw = x0 + 0.3, pw - 0.6
    add_text(slide, tx, y0 + 0.2, tw, 0.85, [{"t": f"{d['no']:02d}"}], size=44, bold=True, color=th["on_dark"],
             spacing=1.0, name="Demo number")
    add_text(slide, tx, y0 + 1.06, tw, 0.95, [{"t": d["product"]}], size=24, bold=True, color="FFFFFF",
             spacing=1.0, name="Product name")
    w1 = pill(slide, tx, y0 + 2.1, f"{d['minutes']} min", fill=th["on_dark"], color=th["panel"],
              name="Duration pill")
    if d["lite_min"]:
        pill(slide, tx + w1 + 0.15, y0 + 2.1, f"Lite {d['lite_min']} min", fill=th["accent"], color="FFFFFF",
             name="Lite duration pill")
    deco(slide, tx, y0 + 2.72, tw, 0.02, th["accent"], "Panel divider")
    y = y0 + 2.84
    add_text(slide, tx, y, tw, 0.26, [{"t": "What you need"}], size=14, bold=True, color=th["on_dark"],
             spacing=1.0, name="Needs label")
    y += 0.3
    nh = est_lines(plain(d["needs"]), 18, tw) * 18 * LINE_H / 72.0
    add_text(slide, tx, y, tw, nh + 0.04, [{"t": d["needs"]}], size=18, color="FFFFFF", name="Needs", spacing=1.0)
    y += nh + 0.22
    add_text(slide, tx, y, tw, 0.26, [{"t": "Standalone"}], size=14, bold=True, color=th["on_dark"],
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
                 [{"runs": [("Demo  ", {"color": th["text"]}), (proof, {})], "spacing": 1.0}], size=16,
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
    for x, w, t in ((x_badge, 1.5, "Step"), (x_cmd, w_cmd, "Command · click"), (x_ok, w_ok, "Success criteria")):
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
        oh = max(0.7, est_lines(plain(otext), 16, ow) * 16 * LINE_H / 72.0 + 0.2)
        oy = bottom - oh
        add_box(slide, MX, oy, CW, oh, line=th["accent"], line_w=1.5, dash=MSO_LINE.DASH, name="Optional step",
                alt=f"Optional: {otitle}")
        add_text(slide, MX + 0.2, oy, 3.0, oh,
                 [{"runs": [(f"{badge} · {otitle}", {}),
                            (f"  {otime.replace(' ', chr(0xA0))}", {"bold": False, "color": P["muted"]})],
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
            alt=f"Recording of the real {s['data']['demo']['product']} demo")
    if video_path.is_file():
        movie = slide.shapes.add_movie(
            str(video_path), Inches(x), Inches(y), Inches(w), Inches(h), mime_type="video/mp4")
        movie.name = f"Demo video {s['data']['demo']['key']}"
    else:
        add_text(slide, x + 0.4, y + 1.3, w - 0.8, 0.7,
                 [{"t": "No recorded video yet", "align": "c"}], size=28, bold=True,
                 color=P["dark_text"], name="Video not recorded", anchor="m")
        add_text(slide, x + 0.4, y + 2.15, w - 0.8, 0.7,
                 [{"t": f"After recording, save it here: en/slides/videos/{video_path.name}", "align": "c"}],
                 size=20, color=P["dark_muted"], name="Video file path", anchor="m")
    add_text(slide, x, y + h + 0.18, w, 0.35,
             [{"t": "Real screen recording · see the speaker notes and en/slides/VIDEO_GUIDE.md"}],
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
        add_text(slide, MX + 0.8, y, 1.7, row_h, [{"t": d["short"]}], size=20, bold=True, color=t["text"],
                 name=f"Agenda name {d['no']}", anchor="m", spacing=1.0)
        add_text(slide, MX + 2.55, y, 4.15, row_h, [{"t": AGENDA_WHAT[d["key"]]}], size=18, color=P["ink"],
                 name=f"Agenda summary {d['no']}", anchor="m", spacing=1.0)
        add_text(slide, MX + 6.75, y, 0.9, row_h, [{"t": f"{d['minutes']} min", "align": "r"}], size=20, bold=True,
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
                    alt=f"Demo {label}: {m} min", text=[{"t": label, "align": "c"}], size=16, bold=True,
                    color="FFFFFF", anchor="m", inset=(0, 0, 0, 0))
            bx += sw
        add_text(slide, rx + 0.25, y + 1.34, rw - 0.5, h - 1.4, cap, size=16, color=P["ink2"],
                 name=f"{head} caption", spacing=1.0)

    bar_card(1.68, 2.55, "Full · 42 min",
             [(d["key"], d["minutes"], str(d["no"])) for d in DEMOS],
             [{"t": "7 + 6 + 7 + 7 + 7 + 8 min", "after": 4},
              {"t": f"Opening and wrap-up add about {fmt_min(TIMING['extra'])} min"}])
    bar_card(4.43, 2.38, "Lite · 15 min",
             [(k, DEMO_BY_KEY[k]["lite_min"], str(DEMO_BY_KEY[k]["no"])) for k in LITE_ORDER],
             [{"t": "4 + 4 + 3 + 4 min", "after": 4}, {"t": "Copilot → Actions → Foundry → ACA"}])


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
            alt="Developer: VS Code, Codespaces, Copilot CLI, local app",
            text=[{"t": "Developer", "size": 20, "bold": True, "color": P["ink"], "after": 6, "spacing": 1.0}] +
                 [{"t": t, "size": 16, "color": P["ink2"], "after": 4, "spacing": 1.0}
                  for t in ("VS Code", "Codespaces", "Copilot CLI", "Local app")],
            anchor="m", inset=(0.12, 0.1, 0.08, 0.1))
    add_box(slide, ghx, 2.95, ghw, 3.5, fill="FAF8FE", line=gh["accent"], line_w=1.75, name="GitHub",
            alt="GitHub: Copilot, repository, Actions", text=[{"t": "GitHub", "size": 20, "bold": True,
                                                         "color": gh["text"], "spacing": 1.0}],
            anchor="t", inset=(0.25, 0.1, 0.1, 0.05))
    add_box(slide, azx, 1.5, azw, 4.95, fill="F6FAFE", line=az["accent"], line_w=1.75, name="Azure",
            alt="Microsoft Azure: Foundry, Container Apps, AKS, ACR",
            text=[{"t": "Microsoft Azure", "size": 20, "bold": True, "color": az["text"], "spacing": 1.0}],
            anchor="t", inset=(0.25, 0.1, 0.1, 0.05))
    gx, gw, gh_ = ghx + 0.2, ghw - 0.4, 0.82
    gcx = gx + gw / 2
    arch_box(slide, gx, 3.45, gw, gh_, "copilot", "Copilot", "Issue → PR agent", "Copilot", "GitHub Copilot")
    arch_box(slide, gx, 4.5, gw, gh_, "repo", "Repository", "Rulesets, CODEOWNERS", "Repo", "GitHub repository")
    arch_box(slide, gx, 5.55, gw, gh_, "actions", "Actions", "CI/CD · OIDC login", "Actions", "GitHub Actions")
    ax, aw = azx + 0.2, azw - 0.4
    sw = (aw - 0.12) / 2
    arch_box(slide, ax, 2.0, aw, 0.95, "foundry", "Microsoft Foundry", "gpt-6.1-sol · effort xhigh",
             "Foundry", "Microsoft Foundry")
    arch_box(slide, ax, 3.85, sw, 1.1, "aca", "Container Apps", "Managed ID", "Container Apps", "Azure Container Apps")
    arch_box(slide, ax + sw + 0.12, 3.85, sw, 1.1, "aks", "AKS", "Workload ID", "AKS", "Azure Kubernetes Service")
    arch_box(slide, ax, 5.55, aw, 0.82, "neutral", "ACR", "Container image store", "ACR", "Azure Container Registry")
    cx1, cx2 = ax + sw / 2, ax + sw + 0.12 + sw / 2
    dcx = dx + dw / 2
    # code / image flows (graphite)
    add_arrow(slide, dx + dw, 4.91, gx, 4.91, color=graphite, name="Arrow push", alt="Developer pushes and opens PRs to the repository")
    add_arrow(slide, gcx, 4.27, gcx, 4.5, color=graphite, name="Arrow Copilot to repo", alt="Copilot PRs go to the repository")
    add_arrow(slide, gcx, 5.32, gcx, 5.55, color=graphite, name="Arrow repo to Actions", alt="Repository triggers Actions")
    add_arrow(slide, cx1, 5.55, cx1, 4.95, color=graphite, name="Arrow ACR to ACA", alt="Container Apps pulls the image from ACR")
    add_arrow(slide, cx2, 5.55, cx2, 4.95, color=graphite, name="Arrow ACR to AKS", alt="AKS pulls the image from ACR")
    # identity flows (amber): no stored keys
    add_arrow(slide, gx + gw, 5.96, ax, 5.96, color=amber, width=3, name="Arrow OIDC",
              alt="Actions signs in to Azure with OIDC and pushes the image to ACR")
    add_arrow(slide, cx1, 3.85, cx1, 2.95, color=amber, width=3, name="Arrow managed identity",
              alt="Container Apps calls Foundry with its Managed Identity")
    add_arrow(slide, cx2, 3.85, cx2, 2.95, color=amber, width=3, name="Arrow workload identity",
              alt="AKS calls Foundry with Workload Identity")
    add_arrow(slide, dcx, 3.5, dcx, 2.475, color=amber, width=3, head=False, name="Arrow az login up")
    add_arrow(slide, dcx, 2.475, ax, 2.475, color=amber, width=3, name="Arrow az login",
              alt="Developer calls Foundry after az login")
    # labels
    add_label(slide, (dx + dw + ghx) / 2, 4.6, "push · PR", color=graphite, fill="FFFFFF", name="Label push")
    add_label(slide, (ghx + ghw + azx) / 2, 5.62, "OIDC", color=amber_text, name="Label OIDC")
    add_label(slide, (dcx + azx) / 2, 2.475, "az login", color=amber_text, name="Label az login")
    add_label(slide, cx1, 3.4, "Managed Identity", color=amber_text, name="Label managed identity")
    add_label(slide, cx2, 3.4, "Workload Identity", color=amber_text, name="Label workload identity")
    add_label(slide, (cx1 + cx2) / 2, 5.27, "image pull", color=graphite, name="Label image pull")
    # legend
    add_arrow(slide, MX, 6.72, MX + 0.55, 6.72, color=amber, width=3, name="Legend identity line")
    add_text(slide, MX + 0.7, 6.55, 5.0, 0.34, [{"t": "Identity flow — no stored keys"}], size=16, bold=True,
             color=amber_text, name="Legend identity", anchor="m", spacing=1.0)
    add_arrow(slide, 6.2, 6.72, 6.75, 6.72, color=graphite, name="Legend flow line")
    add_text(slide, 6.9, 6.55, 5.0, 0.34, [{"t": "Code · image flow"}], size=16, bold=True, color=graphite,
             name="Legend flow", anchor="m", spacing=1.0)


# ---------------------------------------------------------------------------
# Matrix + sample app
# ---------------------------------------------------------------------------
def render_matrix(slide, s, th):
    d = s["data"]
    rows = [["Demo", "What you need", "Why it works alone"]]
    for (a, b, c), key in zip(d["rows"], d["keys"]):
        rows.append([{"t": a, "bold": True, "color": THEME[key]["text"]}, b, c])
    _, h = add_table(slide, MX, BODY_TOP, [1.75, 4.55, 5.83], rows, head_fill=P["ink"], size=18, min_row_h=0.6,
                     max_h=BODY_BOTTOM - BODY_TOP - 0.55, name="Independence matrix",
                     alt="What each demo needs and why it can run on its own", code_color=THEME["aca"]["text"])
    add_text(slide, MX, BODY_TOP + h + 0.2, CW, 0.5, [{"t": d["foot"]}], size=18, color=P["ink2"],
             code_color=THEME["aca"]["text"], name="Mock backend note", spacing=1.0)


def render_app(slide, s, th):
    amber = P["identity"]
    ww = [2.8, 2.8, 2.9]
    gap = (CW - sum(ww)) / 2
    xs = [MX, MX + ww[0] + gap, MX + ww[0] + gap + ww[1] + gap]
    y, h = 1.7, 1.35
    specs = [("neutral", "Browser UI", "Question in, answer + instance out"),
             ("aca", "Python app", "stdlib only · app/server.py"),
             ("foundry", "Microsoft Foundry", "gpt-6.1-sol · effort xhigh")]
    for x, w, (key, title, cap) in zip(xs, ww, specs):
        arch_box(slide, x, y, w, h, key, title, cap, f"Flow {title}", title)
    cy = y + h / 2
    add_arrow(slide, xs[0] + ww[0], cy, xs[1], cy, color=P["ink2"], name="Arrow UI to app", alt="Browser calls /api/chat")
    add_arrow(slide, xs[1] + ww[1], cy, xs[2], cy, color=amber, width=3, name="Arrow app to Foundry",
              alt="App calls Foundry with an Entra ID token")
    add_label(slide, (xs[0] + ww[0] + xs[1]) / 2, cy - 0.3, "POST /api/chat", color=P["ink2"], size=14,
              name="Label chat")
    add_label(slide, (xs[1] + ww[1] + xs[2]) / 2, cy - 0.3, "Entra ID token", color=amber, size=14, name="Label token")
    eps = [("GET /healthz", "No auth", "ok", "Called by platform probes. Returns 200 while the app is alive."),
           ("GET /api/info", "Auth required", "aca",
            "Shows `backend` `auth` `model` `effort` `platform` `instance` `revision`."),
           ("POST /api/chat", "Demo auth", "aca", "Sends the question to Foundry (or mock) and returns the answer.")]
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
    add_text(slide, MX, 5.76, CW, 0.4, [{"t": "The same container image runs everywhere; only how it gets a token differs."}],
             size=18, bold=True, color=P["ink"], name="One image", spacing=1.0)
    chips = [("neutral", "Local · Codespaces", "az login"), ("aca", "ACA", "Managed Identity"),
             ("aks", "AKS", "Workload Identity")]
    cw2 = (CW - 0.5) / 3
    for i, (key, name, ident) in enumerate(chips):
        x = MX + i * (cw2 + 0.25)
        t = THEME[key]
        add_box(slide, x, 6.24, cw2, 0.55, fill=t["tint"], line=t["accent"], line_w=1.5, name=f"Runs on {name}",
                text=[{"runs": [(name, {"bold": True, "color": t["text"]}), (f"  ·  {ident}", {"color": P["identity"],
                       "bold": True})], "align": "c", "spacing": 1.0}], size=16, anchor="m",
                inset=(0.1, 0.02, 0.1, 0.02))


# ---------------------------------------------------------------------------
# Wrap-up slides
# ---------------------------------------------------------------------------
def render_compare(slide, s, th):
    d = s["data"]
    rows = [["Criterion", "Container Apps", "AKS"]] + [list(r) for r in d["rows"]]
    _, h = add_table(slide, MX, BODY_TOP, [2.7, 4.7, 4.73], rows, head_fill=P["ink"],
                     head_fills=[P["ink"], THEME["aca"]["accent"], THEME["aks"]["accent"]], size=18, min_row_h=0.56,
                     max_h=BODY_BOTTOM - BODY_TOP - 0.7, name="Container Apps vs AKS",
                     alt="Container Apps vs AKS: operational load, control, scaling, networking, cost model and best-fit workloads")
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
            alt="Local az login, Actions OIDC, ACA Managed Identity, AKS Workload Identity: all keyless identity paths")
    add_text(slide, MX + 0.25, ty, 2.4, 0.9, [{"t": d["trust_label"]}], size=18, bold=True, color=P["warn"],
             name="Keyless label", anchor="m", spacing=1.0)
    px = MX + 2.8
    for label in d["trust"]:
        px += pill(slide, px, ty + 0.27, label, fill="FFFFFF", color=P["warn"], line=P["identity"], size=14,
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
    for x, w, t in ((xn, wn, "Service"), (xb, wb, "Key benefit"), (xp, wp, "Evidence from the demo")):
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
    rows = [["Problem", "Fix"]]
    for name, symptom, fix in s["data"]["rows"]:
        rows.append([[{"t": name, "bold": True}, {"t": symptom, "size": 16, "bold": False, "color": P["muted"]}], fix])
    add_table(slide, MX, BODY_TOP, [3.7, 8.43], rows, head_fill=P["ink"], size=18, min_row_h=0.8,
              max_h=BODY_BOTTOM - BODY_TOP, name="Troubleshooting top 5", alt="Five common problems and how to fix them",
              code_color=THEME["aca"]["text"], first_col_bold=False)


def render_links(slide, s, th):
    d = s["data"]
    rows = [["Topic", "Start page"]]
    for label, display, url in d["rows"]:
        rows.append([label, {"t": display, "runs": [(display, {"link": url, "color": THEME["aca"]["text"]})]}])
    _, h = add_table(slide, MX, BODY_TOP, [4.0, 8.13], rows, head_fill=P["ink"], size=18, min_row_h=0.46, head_h=0.46,
                     max_h=BODY_BOTTOM - BODY_TOP - 0.5, name="Reference links", alt="Links to the official documentation start pages")
    add_text(slide, MX, BODY_TOP + h + 0.15, CW, 0.34, [{"t": d["foot"]}], size=16, color=P["muted"],
             name="Links note", spacing=1.0)


# ===========================================================================
# TIMING, MARKDOWN OUTLINE, BUILD
# ===========================================================================
APPENDIX_KINDS = ("prep", "trouble", "links")
KIND_LABEL = {
    "title": "Cover", "agenda": "Overview", "arch": "Diagram", "matrix": "Table", "app": "Diagram",
    "value": "Value", "flow": "Demo flow", "video": "Demo video", "code": "Key code", "compare": "Comparison table", "pipeline": "Diagram",
    "governance": "Checklist", "summary": "Summary", "closing": "Closing", "prep": "Appendix", "trouble": "Appendix",
    "links": "Appendix",
}
TIMING: dict = {}


def fmt_min(x: float) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.1f}"


def minutes_of(notes: dict) -> float:
    m = re.search(r"about\s*([0-9]+(?:\.[0-9]+)?)\s*min", notes["time"], re.IGNORECASE)
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
        o += [f"- Title: {d['title']}", f"- Subtitle: {d['subtitle']}", f"- Tagline: {d['tagline']}",
              "- Service chips: " + " · ".join(n for n, _ in d["chips"]), f"- Footer: {fill_timing(d['foot'])}"]
    elif k == "agenda":
        rows = [[str(x["no"]), x["short"], AGENDA_WHAT[x["key"]], f"{x['minutes']} min",
                 f"{x['lite_min']} min" if x["key"] in LITE_ORDER else "–"] for x in DEMOS]
        o += md_table(["#", "Demo", "What it shows", "Time", "Lite"], rows)
        o += ["", f"- Full: demos total about {fmt_min(TIMING['full'])} min · Lite: about {fmt_min(TIMING['lite'])} min",
              f"- Opening and wrap-up add about {fmt_min(TIMING['extra'])} min"]
    elif k == "arch":
        o += ["- Flow: developer → GitHub (Copilot · repository · Actions) → Azure (ACR → Container Apps / AKS → Microsoft Foundry)",
              "- Identity flows (orange, no stored keys): developer `az login` → Foundry · Actions `OIDC` → Azure · "
              "Container Apps `Managed Identity` → Foundry · AKS `Workload Identity` → Foundry",
              "- Code and image flows (gray): push · PR, Copilot PR, repository → Actions, ACR image pull"]
    elif k == "matrix":
        o += md_table(["Demo", "What you need", "Why it works alone"], [list(r) for r in d["rows"]])
        o += ["", "- " + plain(d["foot"])]
    elif k == "app":
        o += ["- Flow: browser UI → `POST /api/chat` → Python app (stdlib, `app/server.py`) → Entra ID token → "
              "Microsoft Foundry (gpt-6.1-sol, effort `xhigh`)",
              "- `GET /healthz`: no authentication, for platform probes",
              "- `GET /api/info`: authentication required; shows `backend` `auth` `model` `effort` `platform` `instance` `revision`",
              "- `POST /api/chat`: behind the demo authentication",
              "- Same image: local and Codespaces (`az login`) · Container Apps (Managed Identity) · AKS (Workload Identity)"]
    elif k == "value":
        x = d["demo"]
        lite = f" (Lite {x['lite_min']} min)" if x["lite_min"] else ""
        o += [f"- Demo {x['no']} · {x['product']} · about {x['minutes']} min{lite}", f"- What you need: {x['needs']}",
              f"- Standalone: {x['independent']}", "- Benefit cards:"]
        o += [f"  - **{h}** — {b} (demo: {p})" for h, b, p in x["cards"]]
    elif k == "flow":
        x = d["demo"]
        rows = [[f"{i}. {t}", tm, "<br>".join(f"`{ln.strip()}`" for ln in cmd), ok, "Lite" if lite else ""]
                for i, (t, tm, cmd, ok, lite) in enumerate(x["steps"], 1)]
        o += md_table(["Step", "Time", "Command · click", "Success criteria", "Lite"], rows)
        if x.get("opt"):
            _, ot, otime, otext = x["opt"]
            o += ["", f"- Optional · {ot} ({otime}): {otext}"]
        if x.get("flow_foot"):
            o += [f"- Note: {x['flow_foot']}"]
    elif k == "video":
        o += [f"- Video file: `en/slides/videos/{d['video_path'].name}`",
              "- If the file exists, it is embedded in the PPTX; if not, a note shows where to save the recording.",
              "- How to record the real screens: `en/slides/VIDEO_GUIDE.md`"]
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
        o += ["- Callouts:"] + [f"  - **{h}** — {b}" for h, b in c["callouts"]]
    elif k == "compare":
        o += md_table(["Criterion", "Container Apps", "AKS"], [list(r) for r in d["rows"]])
        o += ["", f"- {d['foot']}"]
    elif k == "pipeline":
        o += ["- Stages: " + " → ".join((l1 + (" " + l2 if l2 else "")).strip() + (f" ({b})" if b else "")
                                       for l1, l2, _, b in d["stages"])]
        o += [f"- {h}: {b}" for h, b, _ in d["groups"]]
        o += [f"- {d['trust_label']}: " + " · ".join(d["trust"])]
    elif k == "governance":
        o += [f"{i}. **{h}** — {b}" for i, (h, b) in enumerate(d["cards"], 1)]
    elif k == "summary":
        o += md_table(["Service", "Key benefit", "Evidence from the demo"], [[n, b, p] for _, n, b, p in d["rows"]])
    elif k == "closing":
        o += [f"- {d['repo_label']}: `{REPO}`"] + [f"- `{n}` — {t}" for n, t in d["items"]]
        o += [f"- {d['start_label']}:", "", "```", *d["start"], "```", "", f"- {d['foot']}"]
    elif k == "prep":
        for head, _, bullets in d["cols"]:
            o += [f"- **{head}**"] + [f"  - {b}" for b in bullets]
    elif k == "trouble":
        o += md_table(["Problem", "Symptom", "Fix"], [list(r) for r in d["rows"]])
    elif k == "links":
        o += md_table(["Topic", "Start page"], [[a, f"[{b}]({u})"] for a, b, u in d["rows"]])
        o += ["", f"- {d['foot']}"]
    return o


def render_markdown(S: list[dict]) -> str:
    T = TIMING
    L: list[str] = []
    a = L.append
    a("# GitHub Copilot in the Cloud — Presentation Outline and Speaker Script")
    a("")
    a("> This file is generated by `en/slides/build_deck.py` from the same data as `demo-presentation-en.pptx`. "
      "Do not edit it by hand: change the data in the script and run `python en/slides/build_deck.py`. "
      "The same script is also in each slide's speaker notes (the Notes pane in PowerPoint).")
    a("")
    a("## Timing")
    a("")
    rows = [["Opening", f"1–{T['first'] - 1}", f"about {fmt_min(T['opening'])} min", f"about {fmt_min(T['opening'])} min"]]
    for i, d in enumerate(DEMOS):
        base = T["first"] + 4 * i
        rows.append([f"Demo {d['no']} · {d['product']}", f"{base}–{base + 3}", f"{d['minutes']} min",
                     f"{d['lite_min']} min" if d["lite_min"] else "Skipped"])
    rows.append(["Wrap-up", f"{T['last'] + 1}–{T['closing']}", f"about {fmt_min(T['wrap'])} min + Q&A",
                 f"about {fmt_min(T['wrap'])} min + Q&A"])
    rows.append(["**Demo total**", "", f"**about {fmt_min(T['full'])} min**", f"**about {fmt_min(T['lite'])} min**"])
    rows.append(["Whole talk (reference)", "", f"about {fmt_min(T['full'] + T['extra'])} min + Q&A",
                 f"about {fmt_min(T['lite'] + T['extra'])} min + Q&A"])
    L += md_table(["Section", "Slides", "Full", "Lite"], rows)
    a("")
    a("- Each demo's time is the target from its demo README. Cover the value slide (about 1 min) within that time, and explain the key-code slide while waiting during the demo. If the step times add up to a little more, shorten your explanations to fit.")
    a("- The Lite path goes Copilot → Actions → Foundry → Container Apps and runs only the steps marked `Lite` on each flow slide. "
      "To fit a 15-minute slot, cut the opening (3–5) and wrap-up (30–33) slides to a sentence or two, or skip them.")
    a("- Skip the appendix slides (checklist, troubleshooting, links) during the talk and use them in Q&A.")
    a("")
    a("## Slide list")
    a("")
    rows = [[str(n), s["title"], KIND_LABEL[s["kind"]], ("about " + fmt_min(minutes_of(s["notes"])) + " min")
             if minutes_of(s["notes"]) else "–"] for n, s in enumerate(S, 1)]
    L += md_table(["#", "Title", "Type", "Estimated time"], rows)
    a("")
    for n, s in enumerate(S, 1):
        a("---")
        a("")
        a(f"## {n}. {s['title']}")
        a("")
        a(f"*{KIND_LABEL[s['kind']]}" + (f" · {s['label']}" if s["label"] else "") + "*")
        a("")
        a("### On the slide")
        a("")
        L += outline_for(s)
        a("")
        a("### What to say")
        a("")
        L += [f"- {t}" for t in s["notes"]["say"]]
        if s["notes"].get("cue"):
            a("")
            a("### Demo cues")
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


_A_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def drop_hangul_font(root) -> None:
    """The stock python-pptx themes map the Hangul script to a Korean face; this English deck has no use for it."""
    for el in root.findall(".//a:font[@script='Hang']", _A_NS):
        el.getparent().remove(el)


def patch_theme_fonts(prs) -> None:
    """Make Segoe UI the theme font so new slides added in PowerPoint match the deck."""
    theme = prs.slide_master.part.part_related_by(RT.THEME)
    root = etree.fromstring(theme.blob)
    for tag in ("majorFont", "minorFont"):
        font = root.find(f".//a:fontScheme/a:{tag}", _A_NS)
        font.find("a:latin", _A_NS).set("typeface", LATIN)
        font.find("a:ea", _A_NS).set("typeface", EA)
    drop_hangul_font(root)
    theme._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def patch_notes_theme(prs) -> None:
    """The notes master is created on first use and ships its own stock theme; clean it the same way."""
    drop_hangul_font(prs.notes_master.part.part_related_by(RT.THEME)._element)


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


HANGUL = re.compile("[\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uAC00-\uD7A3\uD7B0-\uD7FF]")


def hangul_problems(path: Path, md_text: str) -> list[str]:
    """The English deck must contain no Hangul anywhere: slide text, notes, alt text, properties, themes, outline."""
    found: list[str] = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.filename.endswith((".xml", ".rels")) and HANGUL.search(z.read(info).decode("utf-8", "ignore")):
                found.append(f"Hangul text in {info.filename}")
    if HANGUL.search(md_text):
        found.append(f"Hangul text in {MD_PATH.name}")
    return found


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
        if len(notes.strip()) < 40 or not re.search("[A-Za-z]", notes):
            problems.append(f"slide {i}: speaker notes missing")
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
    patch_notes_theme(prs)
    cp = prs.core_properties
    cp.title = "GitHub Copilot in the Cloud — Demo Presentation"
    cp.subject = "Live demos of GitHub Copilot, Microsoft Foundry, Azure Container Apps and AKS"
    cp.author = "ghcp-in-the-cloud"
    cp.last_modified_by = "ghcp-in-the-cloud"
    cp.keywords = "GitHub Copilot, Foundry, Container Apps, AKS, OIDC"
    cp.language = "en-US"
    cp.created = cp.modified = datetime(2025, 1, 1, 0, 0, 0)
    cp.revision = 1
    prs.save(str(PPTX_PATH))
    normalize_zip(PPTX_PATH)
    markdown = render_markdown(slides)
    MD_PATH.write_text(markdown, encoding="utf-8")
    problems, sizes = verify(PPTX_PATH, len(slides))
    problems += hangul_problems(PPTX_PATH, markdown)
    print(f"wrote {PPTX_PATH.relative_to(ROOT)} ({len(slides)} slides) and {MD_PATH.relative_to(ROOT)}")
    print("font sizes (pt: runs): " + ", ".join(f"{k:g}: {v}" for k, v in sorted(sizes.items())))
    for w in WARNINGS:
        print("layout warning:", w)
    for p in problems:
        print("ERROR:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(build())
