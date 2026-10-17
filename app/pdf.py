"""PDF generation for printable checklists (documents, steps, costs, warnings).

Uses fpdf2 with the system Noto fonts, so Hindi, Marathi and the other Indic
scripts render correctly. If no Indic font is found, Latin text still works.
"""
import os

from fpdf import FPDF

# Per-language fonts found on common Linux distributions (Noto family).
FONT_CANDIDATES = {
    "hi": ["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"],
    "mr": ["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"],
    "ta": ["/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf"],
    "te": ["/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf"],
    "bn": ["/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"],
    "gu": ["/usr/share/fonts/truetype/noto/NotoSansGujarati-Regular.ttf"],
    "kn": ["/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf"],
    "ml": ["/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf"],
    "pa": ["/usr/share/fonts/truetype/noto/NotoSansGurmukhi-Regular.ttf"],
}
LATIN_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]
LATIN_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]


def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def font_for(lang):
    return _first_existing(FONT_CANDIDATES.get(lang, [])) or _first_existing(LATIN_CANDIDATES)


def _s(text):
    """fpdf core fonts are latin-1; the Noto/DejaVu TTFs are unicode. Keep both happy."""
    if text is None:
        return ""
    return str(text).replace("\u20b9", "Rs.").replace("\t", "    ")


class ChecklistPDF(FPDF):
    def header(self):
        self.set_font(self._font, "B", 16)
        self.set_text_color(31, 31, 31)
        self.multi_cell(0, 9, _s(self.doc_title), new_x="LMARGIN", new_y="NEXT")
        if self.doc_subtitle:
            self.set_font(self._font, "", 10)
            self.set_text_color(110, 105, 95)
            self.multi_cell(0, 5.5, _s(self.doc_subtitle), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(184, 55, 31)
        self.set_line_width(0.6)
        y = self.get_y() + 1.5
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(5)

    def footer(self):
        self.set_y(-14)
        self.set_font(self._font, "", 8)
        self.set_text_color(130, 125, 115)
        self.cell(0, 5, _s("Samajh | Verify every detail on the official portal before you act."), align="L")
        self.cell(0, 5, f"{self.page_no()}", align="R")

    def section(self, heading):
        self.ln(2)
        self.set_font(self._font, "B", 12)
        self.set_text_color(184, 55, 31)
        self.multi_cell(0, 7, _s(heading), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(31, 31, 31)
        self.set_font(self._font, "", 11)

    def item(self, text, box=False):
        prefix = "" if box else "-  "
        x = self.get_x()
        self.set_font(self._font, "", 11)
        if box:
            self.draw_box_check(x + 1, self.get_y() + 1.2, 3.6, 3.6)
            self.set_x(x + 7)
        else:
            self.set_x(x + 2)
        self.multi_cell(0, 6.2, _s(prefix + str(text)), new_x="LMARGIN", new_y="NEXT")

    def draw_box_check(self, x, y, w, h):
        self.set_draw_color(90, 85, 78)
        self.set_line_width(0.3)
        self.rect(x, y, w, h)

    def note(self, text):
        self.ln(1)
        self.set_font(self._font, "", 9.5)
        self.set_text_color(110, 105, 95)
        self.multi_cell(0, 5.5, _s(text), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(31, 31, 31)

    def link_line(self, url):
        if not url:
            return
        self.ln(1)
        self.set_font(self._font, "", 10)
        self.set_text_color(40, 80, 180)
        self.multi_cell(0, 5.5, _s(url), link=url, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(31, 31, 31)


def build_checklist_pdf(title, subtitle, sections, lang="en", notes="", official_url=""):
    """Render a checklist PDF and return the bytes."""
    latin = _first_existing(LATIN_CANDIDATES)
    latin_bold = _first_existing(LATIN_BOLD_CANDIDATES)
    indic = _first_existing(FONT_CANDIDATES.get(lang, []))
    pdf = ChecklistPDF()
    pdf.doc_title = title or "Checklist"
    pdf.doc_subtitle = subtitle or ""
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(16, 16, 16)
    if latin:
        # Latin font as the base (it has the widest coverage of ASCII), with the
        # language's Noto font as glyph fallback so Hindi/Marathi/Tamil/... render.
        pdf.add_font("Body", "", latin)
        pdf.add_font("Body", "B", latin_bold if latin_bold else latin)
        if indic and indic != latin:
            pdf.add_font("Indic", "", indic)
            pdf.add_font("Indic", "B", indic)
            pdf.set_fallback_fonts(["Indic"])
        pdf._font = "Body"
        pdf.set_font("Body", "B", 16)
    else:
        pdf._font = "Helvetica"
        pdf.set_font("Helvetica", "B", 16)
    pdf.add_page()
    for section in sections:
        heading = section.get("heading") if isinstance(section, dict) else ""
        items = section.get("items") if isinstance(section, dict) else []
        if not heading and not items:
            continue
        if heading:
            pdf.section(heading)
        for item in items or []:
            pdf.item(item, box=True)
    if notes:
        pdf.note(notes)
    pdf.link_line(official_url or "")
    pdf.note("Generated by Samajh. This is a convenience copy, not an official document.")
    out = pdf.output()
    return bytes(out)
