"""Build docs/SmartWaste_AI_Presentation.pptx: light, elegant design with real screenshots and real metrics.

Metrics come from ml/model/evaluation*.txt and docs/TESTING.md; screenshots from docs/guide/ (clean sample data).
Re-run after retraining or re-testing:
    python scripts/make_presentation.py
"""
import io
import re
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "guide"
MODEL = ROOT / "ml" / "model"

TEAM = [("Madhuri", "2300032809"), ("Keerthi", "2300033635"), ("Sana", "2300033102"), ("Sandhyana", "2300033182")]

# ---- palette: ivory, forest green, sage, a touch of antique gold
IVORY, WHITE, INK, MUTED = "FAF8F3", "FFFFFF", "1F2A24", "6B7280"
GREEN, GREEN2, SAGE, SAGE2, GOLD, LINE = "1B6B3A", "2E8B57", "E6F0E8", "CFE3D3", "B08D3C", "E5E1D6"
SERIF, SANS = "Georgia", "Segoe UI"
CAT = {"plastic": "3B82F6", "paper": "D97706", "metal": "64748B", "glass": "14B8A6", "organic": "84CC16"}


def rgb(h):
    return RGBColor.from_string(h)


# ------------------------------------------------------------------ real metrics
def read_acc(path):
    m = re.search(r"Test accuracy: ([0-9.]+) \((\d+) images\)", path.read_text(encoding="utf-8"))
    return float(m.group(1)) * 100, int(m.group(2))


def read_report(path):
    txt = path.read_text(encoding="utf-8")
    rows = {}
    for line in txt.splitlines():
        m = re.match(r"\s+(glass|metal|organic|paper|plastic)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+(\d+)", line)
        if m:
            rows[m.group(1)] = m.groups()[1:]
    return rows, float(re.search(r"macro avg\s+[0-9.]+\s+[0-9.]+\s+([0-9.]+)", txt).group(1))


ACC, N_TEST = read_acc(MODEL / "evaluation.txt")
BASE_ACC, _ = read_acc(MODEL / "evaluation_baseline.txt")
ROWS, MACRO = read_report(MODEL / "evaluation.txt")
_, BASE_MACRO = read_report(MODEL / "evaluation_baseline.txt")
T = (ROOT / "docs" / "TESTING.md").read_text(encoding="utf-8")
UNIT = re.search(r"\*\*Result: (\d+) passed", T).group(1)
E2E = re.search(r"\*\*Result: (\d+)/(\d+) checks passed", T)
AUD = re.search(r"Last run: \*\*(\d+)/(\d+) checks passed", T)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
n_slide = {"n": 0}


# ------------------------------------------------------------------ drawing helpers
def shape(s, l, t, w, h, fill=None, line=None, kind=MSO_SHAPE.RECTANGLE, radius=None, name=None, lw=0.75):
    sh = s.shapes.add_shape(kind, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill:
        sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
    else:
        sh.fill.background()
    if line:
        sh.line.color.rgb = rgb(line); sh.line.width = Pt(lw)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radius
    if name:
        sh.name = name
    return sh


def text(s, content, l, t, w, h, size=16, bold=False, color=INK, font=SANS, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=None, italic=False, tracking=None):
    tb = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04); tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, line in enumerate(content if isinstance(content, list) else [content]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.line_spacing = spacing
        r = p.add_run(); r.text = line
        r.font.size, r.font.bold, r.font.italic, r.font.name = Pt(size), bold, italic, font
        r.font.color.rgb = rgb(color)
        if tracking:
            r._r.get_or_add_rPr().set("spc", str(tracking))
    return tb


def bullets(s, items, l, t, w, h, size=16, gap=9, color=INK):
    tb = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap); p.line_spacing = 1.08
        head, _, rest = it.partition("::")
        dot = p.add_run(); dot.text = "\u25CF  "; dot.font.size = Pt(size - 6); dot.font.color.rgb = rgb(GREEN2); dot.font.name = SANS
        runs = []
        if rest:
            a = p.add_run(); a.text = head.strip() + ": "; a.font.bold = True; runs.append(a)
            b = p.add_run(); b.text = rest.strip(); runs.append(b)
        else:
            a = p.add_run(); a.text = head.strip(); runs.append(a)
        for r in runs:
            r.font.size = Pt(size); r.font.color.rgb = rgb(color); r.font.name = SANS
    return tb


def new_slide(eyebrow, title, notes=None):
    s = prs.slides.add_slide(BLANK)
    n_slide["n"] += 1
    shape(s, 0, 0, 13.333, 7.5, fill=IVORY, name="bg")
    shape(s, 0, 0, 0.14, 7.5, fill=GREEN, name="deco")
    text(s, eyebrow.upper(), 0.8, 0.42, 9, 0.3, size=11, bold=True, color=GREEN2, tracking=250)
    text(s, title, 0.8, 0.72, 11.8, 0.85, size=30, color=INK, font=SERIF)
    text(s, "SmartWaste AI", 0.8, 7.04, 4, 0.3, size=10, color=MUTED)
    text(s, f"{n_slide['n']:02d}", 11.9, 7.04, 0.65, 0.3, size=10, color=MUTED, align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def card(s, l, t, w, h, fill=WHITE, accent=None):
    shape(s, l + 0.04, t + 0.06, w, h, fill="EFEBE0", kind=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06, name="deco")  # soft shadow
    c = shape(s, l, t, w, h, fill=fill, line=LINE, kind=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    if accent:
        shape(s, l + 0.25, t, 0.7, 0.05, fill=accent, name="deco")
    return c


def stat(s, l, t, w, number, label, color=GREEN, h=1.35):
    card(s, l, t, w, h, accent=color)
    text(s, number, l, t + 0.17, w, 0.7, size=34, color=color, font=SERIF, align=PP_ALIGN.CENTER)
    text(s, label, l + 0.1, t + 0.85, w - 0.2, 0.42, size=12, color=MUTED, align=PP_ALIGN.CENTER)


def frame(s, path, l, t, max_w, max_h, crop_h=None, align="center"):
    """Browser-style window card around a screenshot, scaled to fit max_w x max_h."""
    img = Image.open(path).convert("RGB")
    if crop_h:
        img = img.crop((0, 0, img.width, min(img.height, crop_h)))
    bar, pad = 0.42, 0.14
    r = min((max_w - 2 * pad) / img.width, (max_h - bar - pad) / img.height)
    iw, ih = img.width * r, img.height * r
    fw, fh = iw + 2 * pad, ih + bar + pad
    fl = l + (max_w - fw) / 2 if align == "center" else l
    shape(s, fl + 0.07, t + 0.09, fw, fh, fill="EAE6DA", kind=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.025, name="deco")
    shape(s, fl, t, fw, fh, fill=WHITE, line=LINE, kind=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.025)
    for i, c in enumerate(("E8A09A", "EFD28B", "9ACB9F")):
        shape(s, fl + 0.2 + i * 0.19, t + 0.15, 0.11, 0.11, fill=c, kind=MSO_SHAPE.OVAL, name="deco")
    buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
    s.shapes.add_picture(buf, Inches(fl + pad), Inches(t + bar), Inches(iw), Inches(ih))
    return fl, t, fw, fh


def table(s, data, l, t, w, col_w, row_h=0.4, size=13):
    rows, cols = len(data), len(data[0])
    gt = s.shapes.add_table(rows, cols, Inches(l), Inches(t), Inches(w), Inches(row_h * rows))
    tbl = gt.table
    for c in range(cols):
        tbl.columns[c].width = Inches(col_w[c])
    for r in range(rows):
        tbl.rows[r].height = Inches(row_h)
        for c in range(cols):
            cell = tbl.cell(r, c); cell.text = str(data[r][c])
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.1); cell.margin_top = cell.margin_bottom = Inches(0.03)
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
            for run in para.runs:
                run.font.size, run.font.name = Pt(size), SANS
                run.font.bold = r == 0 or c == 0
                run.font.color.rgb = rgb(GREEN if r == 0 else INK)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(SAGE2 if r == 0 else (WHITE if r % 2 else "F4F1E8"))
    return gt


def step(s, l, t, w, num, head, body):
    shape(s, l + 0.5, t + 0.3, w - 1.0, 0.03, fill=SAGE2, name="deco")
    c = shape(s, l, t, 0.62, 0.62, fill=GREEN, kind=MSO_SHAPE.OVAL, name="num")
    text(s, str(num), l, t + 0.07, 0.62, 0.5, size=20, color=WHITE, font=SERIF, align=PP_ALIGN.CENTER)
    text(s, head, l, t + 0.8, w - 0.15, 0.4, size=18, bold=True, color=INK, font=SERIF)
    text(s, body, l, t + 1.25, w - 0.2, 1.4, size=14, color=MUTED, spacing=1.1)


# =================================================================== 1. title
s = prs.slides.add_slide(BLANK); n_slide["n"] += 1
shape(s, 0, 0, 13.333, 7.5, fill=IVORY, name="bg")
shape(s, 9.3, -1.6, 6.0, 6.0, fill=SAGE, kind=MSO_SHAPE.OVAL, name="deco")
shape(s, 11.2, 4.7, 3.6, 3.6, fill="F1EBD9", kind=MSO_SHAPE.OVAL, name="deco")
shape(s, 0, 0, 0.14, 7.5, fill=GREEN, name="deco")
text(s, "FINAL PROJECT PRESENTATION", 0.8, 0.85, 7, 0.3, size=11, bold=True, color=GREEN2, tracking=300)
text(s, ["AI-Powered Smart Waste", "Management and Monitoring", "System"], 0.8, 1.35, 7.4, 2.3, size=38, color=INK, font=SERIF, spacing=1.0)
shape(s, 0.84, 3.85, 1.1, 0.05, fill=GOLD, name="deco")
text(s, "CNN waste classification  \u00B7  virtual smart bins  \u00B7  live monitoring", 0.8, 4.05, 7.2, 0.4, size=15, color=MUTED)
frame(s, GUIDE / "12_admin_dashboard.png", 8.0, 1.25, 4.9, 3.6, crop_h=700)
text(s, "PRESENTED BY", 0.8, 5.35, 4, 0.3, size=10, bold=True, color=GREEN2, tracking=250)
for i, (nm, roll) in enumerate(TEAM):
    x = 0.8 + i * 3.05
    shape(s, x, 5.78, 0.03, 0.62, fill=SAGE2, name="deco")
    text(s, nm, x + 0.12, 5.74, 2.8, 0.4, size=17, bold=True, color=INK, font=SERIF)
    text(s, roll, x + 0.12, 6.12, 2.8, 0.3, size=12, color=MUTED)
s.notes_slide.notes_text_frame.text = "Introduce the four team members and the one-line pitch: a photo of waste goes in, a routed and monitored bin comes out."

# =================================================================== 2. team
s = new_slide("Our team", "The people behind SmartWaste AI",
              "Each member should understand the whole workflow, even if the work was split across modules.")
for i, (nm, roll) in enumerate(TEAM):
    x = 0.8 + i * 3.0
    card(s, x, 2.2, 2.75, 2.7, accent=GREEN2)
    shape(s, x + 0.9, 2.65, 0.95, 0.95, fill=SAGE, line=SAGE2, kind=MSO_SHAPE.OVAL, name="ini")
    text(s, nm[0], x + 0.9, 2.82, 0.95, 0.6, size=30, color=GREEN, font=SERIF, align=PP_ALIGN.CENTER)
    text(s, nm, x + 0.1, 3.8, 2.55, 0.45, size=21, bold=True, color=INK, font=SERIF, align=PP_ALIGN.CENTER)
    text(s, roll, x + 0.1, 4.3, 2.55, 0.35, size=14, color=MUTED, align=PP_ALIGN.CENTER)
text(s, "Everyone understands the whole workflow: classification, bin assignment, alerts, collection and analytics.", 0.8, 5.5, 11.7, 0.5, size=16, color=MUTED, italic=True)

# =================================================================== 3. problem / solution
s = new_slide("The challenge", "From mixed waste to managed waste",
              "Explain the problem briefly, then the four verbs of the solution: classify, route, monitor, analyse.")
card(s, 0.8, 1.9, 5.6, 4.6)
text(s, "The problem", 1.1, 2.1, 5, 0.45, size=22, color=GREEN, font=SERIF)
bullets(s, ["Mixed waste::lowers recycling rates", "Fixed collection rounds::empty bins are visited while full bins overflow",
            "No data::managers cannot see what is thrown away, or where"], 1.1, 2.75, 5.0, 3.5, size=17, gap=12)
card(s, 6.9, 1.9, 5.65, 4.6, fill="F3F8F4")
text(s, "Our solution", 7.2, 2.1, 5, 0.45, size=22, color=GREEN, font=SERIF)
bullets(s, ["Classify::a CNN recognises plastic, paper, metal, glass or organic from a photo",
            "Route::the item goes to the matching compartment of a virtual smart bin",
            "Monitor::admins watch fill levels and alerts on a live dashboard",
            "Analyse::daily, weekly and monthly trends by location and category"], 7.2, 2.75, 5.1, 3.6, size=16, gap=10)
text(s, "No hardware needed: bin fullness is simulated from configured capacity and estimated item volume.", 0.8, 6.62, 11.7, 0.35, size=13, color=MUTED, italic=True)

# =================================================================== 4. how it works
s = new_slide("Workflow", "How it works, in four steps", "Walk left to right. Each step maps to a module in the project brief.")
steps = [("Capture", "Upload a photo or use the webcam, and choose the disposal location."),
         ("Classify", "The CNN predicts the category with a confidence percentage and a disposal tip."),
         ("Route", "The item enters the matching bin compartment and its simulated fill level rises."),
         ("Collect", "At 90 % an alert is raised. The admin collects the bin and capacity resets to zero.")]
for i, (h, b) in enumerate(steps):
    step(s, 0.8 + i * 3.05, 2.2, 2.85, i + 1, h, b)
text(s, "Every classification is stored, so history, analytics and reports always come from real records.", 0.8, 5.8, 11.7, 0.5, size=16, color=MUTED, italic=True)

# =================================================================== 5. features
s = new_slide("Capabilities", "Everything in one connected platform", "Eight capabilities, one line each.")
feats = [("AI classification", "Five categories with confidence and disposal advice"), ("Virtual smart bins", "Compartments per category across five locations"),
         ("Live dashboard", "Refreshes every few seconds, no reload needed"), ("Automatic alerts", "Raised when a compartment reaches 90 % of capacity"),
         ("Collections", "Pending and completed collections with date and time"), ("Analytics, reports", "Daily, weekly, monthly, plus CSV export"),
         ("Role-based access", "Separate user and administrator areas"), ("Real records only", "Every figure is calculated from the database")]
for i, (h, b) in enumerate(feats):
    x, y = 0.8 + (i % 4) * 3.05, 1.95 + (i // 4) * 2.4
    card(s, x, y, 2.85, 2.1, accent=GREEN2)
    shape(s, x + 0.25, y + 0.3, 0.42, 0.42, fill=SAGE, kind=MSO_SHAPE.OVAL, name="deco")
    text(s, f"{i + 1}", x + 0.25, y + 0.33, 0.42, 0.36, size=15, color=GREEN, font=SERIF, align=PP_ALIGN.CENTER)
    text(s, h, x + 0.2, y + 0.82, 2.5, 0.4, size=15, bold=True, color=INK, font=SERIF)
    text(s, b, x + 0.2, y + 1.22, 2.5, 0.8, size=13, color=MUTED, spacing=1.05)

# =================================================================== 6. architecture
s = new_slide("Design", "System architecture", "Browser talks to Flask; Flask uses the CNN and MySQL. The dashboard polls every five seconds.")
cols = [("Browser", "HTML, CSS, JavaScript and Chart.js"), ("Flask application", "Authentication, upload and live APIs, admin tools"), ("MySQL database", "Seven tables: users, locations, bins, compartments, records, collections, alerts")]
for i, (h, b) in enumerate(cols):
    x = 0.8 + i * 4.1
    card(s, x, 1.95, 3.5, 1.9, accent=GREEN2)
    text(s, h, x + 0.15, 2.2, 3.2, 0.45, size=20, color=GREEN, font=SERIF, align=PP_ALIGN.CENTER)
    text(s, b, x + 0.2, 2.75, 3.1, 1.0, size=14, color=MUTED, align=PP_ALIGN.CENTER, spacing=1.05)
    if i < 2:
        shape(s, x + 3.58, 2.65, 0.44, 0.3, fill=GOLD, kind=MSO_SHAPE.LEFT_RIGHT_ARROW, name="deco")
card(s, 4.9, 4.45, 3.5, 1.3, fill=GREEN)
text(s, "CNN model (Keras)", 4.95, 4.62, 3.4, 0.45, size=19, color=WHITE, font=SERIF, align=PP_ALIGN.CENTER)
text(s, "OpenCV preprocessing, MobileNetV2", 4.95, 5.12, 3.4, 0.4, size=13, color="DDEFE2", align=PP_ALIGN.CENTER)
shape(s, 6.5, 3.9, 0.3, 0.44, fill=GOLD, kind=MSO_SHAPE.UP_DOWN_ARROW, name="deco")
text(s, "Served with Waitress  \u00B7  health endpoint  \u00B7  rotating logs  \u00B7  Docker and CI ready", 0.8, 6.15, 11.7, 0.4, size=14, color=MUTED, align=PP_ALIGN.CENTER)

# =================================================================== 7. dataset / method
s = new_slide("Artificial intelligence", "Data and method", "6,576 images after mapping the original 12 classes to our 5 categories.")
table(s, [["Category", "Source folders", "Images"], ["Paper", "paper, cardboard", "1,941"], ["Glass", "brown, green, white glass", "2,016"],
          ["Organic", "biological", "985"], ["Plastic", "plastic", "865"], ["Metal", "metal", "769"]], 0.8, 1.9, 6.2, [1.6, 3.4, 1.2], row_h=0.5, size=14)
text(s, "Split 70 / 15 / 15:  4,608 train  \u00B7  984 validation  \u00B7  984 test", 0.8, 5.1, 6.4, 0.4, size=15, bold=True, color=INK)
text(s, "Images resized to 128 \u00D7 128 with OpenCV. Trash, battery, clothes and shoes were left out.", 0.8, 5.55, 6.3, 0.7, size=13, color=MUTED, spacing=1.1)
card(s, 7.5, 1.9, 5.05, 4.5, fill="F3F8F4")
text(s, "Method", 7.8, 2.1, 4, 0.45, size=22, color=GREEN, font=SERIF)
bullets(s, ["Transfer learning::MobileNetV2 with ImageNet weights", "Two phases::train a new head, then fine-tune the top layers",
            "Augmentation::flip, rotation, zoom and contrast", "Class weights::balance the uneven classes",
            "Honest testing::the test set was never used for training"], 7.8, 2.75, 4.5, 3.6, size=15, gap=9)

# =================================================================== 8. results
s = new_slide("Artificial intelligence", f"Results: {ACC:.1f}% accuracy on unseen images",
              f"Deployed model {ACC:.1f}% on {N_TEST} held-out images, up from {BASE_ACC:.1f}% for the from-scratch CNN. Weakest classes are metal and plastic.")
stat(s, 0.8, 1.8, 2.55, f"{ACC:.1f}%", "accuracy, deployed model", h=1.25)
stat(s, 3.55, 1.8, 2.55, f"{BASE_ACC:.1f}%", "accuracy, baseline CNN", color=GOLD, h=1.25)
stat(s, 0.8, 3.25, 2.55, f"{MACRO:.2f}", "macro F1, deployed", h=1.25)
stat(s, 3.55, 3.25, 2.55, f"{BASE_MACRO:.2f}", "macro F1, baseline", color=GOLD, h=1.25)
data = [["Class", "Precision", "Recall", "F1"]] + [[c.capitalize(), *ROWS[c][:3]] for c in ("paper", "organic", "glass", "metal", "plastic")]
table(s, data, 0.8, 4.75, 5.3, [1.5, 1.3, 1.2, 1.3], row_h=0.33, size=12)
frame(s, MODEL / "confusion_matrix.png", 6.6, 1.85, 6.0, 4.55)
text(s, "Confusion matrix on the test set. Weakest: metal and plastic, which look alike when shiny.", 6.6, 6.5, 6.0, 0.45, size=12, color=MUTED, align=PP_ALIGN.CENTER, italic=True)

# =================================================================== 9. bins
s = new_slide("Smart bins", "Virtual bins and capacity rules", "Explain simulated fullness clearly: configured capacity and estimated volume.")
bullets(s, ["Locations::College Block A and B, Hostel, Canteen, Library", "Bins::six virtual bins; every bin has five compartments, one per category",
            "Assignment::the emptiest matching compartment with room at the chosen location",
            "Estimated volume::plastic 0.5 L, paper 0.3 L, metal 0.25 L, glass 0.6 L, organic 0.8 L",
            "Fill percentage::current load divided by configured capacity"], 0.8, 1.9, 6.5, 4.6, size=16, gap=12)
table(s, [["Highest fill", "Status", "What happens"], ["Below 70 %", "Normal", "Nothing"], ["70 % to 90 %", "Almost full", "Listed for collection"],
          ["90 % or more", "Collection required", "Alert and collection"]], 7.6, 2.0, 4.95, [1.45, 1.6, 1.9], row_h=0.62, size=12)
text(s, "If a compartment has no room, the item is still recorded but flagged as unassigned.", 7.6, 4.8, 4.95, 0.7, size=13, color=MUTED, italic=True, spacing=1.1)

# =================================================================== 10. classify demo
s = new_slide("Product", "Classification experience", "Live demo moment: classify an image and point at confidence, tip and bin.")
frame(s, GUIDE / "08_classify_result.png", 0.8, 1.7, 8.0, 5.1, align="left")
bullets(s, ["Drag and drop, or webcam", "Result without a page reload", "Confidence ring and category", "Disposal recommendation", "Shows the assigned bin and compartment"],
        9.3, 2.1, 3.4, 4.4, size=16, gap=14)

# =================================================================== 11. dashboard
s = new_slide("Product", "Live operations dashboard", "Show one window updating while another user classifies.")
frame(s, GUIDE / "12_admin_dashboard.png", 0.8, 1.7, 8.0, 5.2, align="left")
bullets(s, ["Refreshes every 5 seconds", "Totals, recyclable share, category counts", "Normal, almost-full and collection-required bins",
            "Fill bars per compartment", "Live activity feed and alert pop-ups"], 9.3, 2.1, 3.4, 4.4, size=16, gap=14)

# =================================================================== 12. bins view
s = new_slide("Product", "Every bin at a glance", "Green edge = normal, amber = almost full, red = collection required.")
frame(s, GUIDE / "13_dashboard_bins.png", 0.8, 1.75, 11.7, 4.0)
text(s, "Hostel Bin 1 needs collection (red).  Library Bin 1 is almost full (amber).  The rest are normal (green).", 0.8, 6.0, 11.7, 0.5, size=15, color=MUTED, align=PP_ALIGN.CENTER, italic=True)

# =================================================================== 13. collections
s = new_slide("Product", "Alerts and collection management", "At 90 % an alert and a pending collection appear automatically.")
frame(s, GUIDE / "17_collections.png", 0.8, 1.7, 8.0, 5.2, align="left")
bullets(s, ["Alert at 90 % of capacity", "Pending and completed collections", "Mark collected resets capacity", "Date, time and admin are recorded",
            "Alerts resolve on collection"], 9.3, 2.1, 3.4, 4.4, size=16, gap=14)

# =================================================================== 14. analytics
s = new_slide("Product", "Analytics and reports", "Daily, weekly and monthly; location and category breakdowns; CSV export.")
frame(s, GUIDE / "19_analytics.png", 0.8, 1.7, 8.0, 5.2, align="left")
bullets(s, ["Daily, weekly and monthly trends", "Category-wise and location-wise charts", "Full classification history with filters", "CSV export for reports"],
        9.3, 2.1, 3.4, 4.4, size=16, gap=14)

# =================================================================== 15. database & security
s = new_slide("Foundation", "Database and security", "Seven tables exactly as required; security basics are in place.")
table(s, [["Table", "Purpose"], ["users", "accounts, hashed passwords, role"], ["locations", "blocks, hostel, canteen, library"], ["smart_bins", "virtual bins at a location"],
          ["bin_compartments", "capacity and load per category"], ["waste_records", "image, category, confidence, bin"], ["collection_records", "pending and completed collections"],
          ["alerts", "capacity alerts and their status"]], 0.8, 1.9, 6.6, [2.3, 4.3], row_h=0.5, size=13)
card(s, 7.9, 1.9, 4.65, 4.0, fill="F3F8F4")
text(s, "Security", 8.2, 2.1, 4, 0.45, size=22, color=GREEN, font=SERIF)
bullets(s, ["Hashed passwords", "CSRF protection on every form", "Role-based access control", "Validated uploads, private images", "Escaped output against XSS"],
        8.2, 2.75, 4.1, 3.0, size=15, gap=8)

# =================================================================== 16. testing
s = new_slide("Quality", "Tested end to end", "Quote the numbers: they come from real test runs, documented in docs/TESTING.md.")
stat(s, 0.8, 1.9, 2.8, UNIT, "automated tests passed")
stat(s, 3.85, 1.9, 2.8, f"{AUD.group(1)}/{AUD.group(2)}", "requirement checks over HTTP")
stat(s, 6.9, 1.9, 2.8, f"{E2E.group(1)}/{E2E.group(2)}", "browser end-to-end checks")
stat(s, 9.95, 1.9, 2.6, f"{ACC:.0f}%", "model accuracy, unseen data")
bullets(s, ["Covered::sign-up and login, roles, classification, bin assignment, 90 % alert, collection reset, dashboard counts, analytics, CSV, live updates",
            "Reliability::a concurrency test found and fixed a lost-update bug under 32 simultaneous uploads",
            "Responsive::all pages checked at phone width"], 0.8, 3.75, 11.7, 3.0, size=16, gap=12)

# =================================================================== 17. future
s = new_slide("Looking ahead", "Limitations and future scope", "Say the limits before someone asks.")
card(s, 0.8, 1.9, 5.6, 4.4)
text(s, "Current limitations", 1.1, 2.1, 5, 0.45, size=22, color=GREEN, font=SERIF)
bullets(s, ["Bin fullness is simulated, not measured", "Training photos are mostly single items on plain backgrounds", "Metal and plastic are the hardest classes",
            "No \u201Cunknown\u201D class and no login throttling yet"], 1.1, 2.75, 5.0, 3.4, size=15, gap=10)
card(s, 6.9, 1.9, 5.65, 4.4, fill="F3F8F4")
text(s, "Future scope", 7.2, 2.1, 5, 0.45, size=22, color=GREEN, font=SERIF)
bullets(s, ["Collect photos from the real campus bins", "Add an unknown class and a confidence threshold", "Real sensors in place of the simulation",
            "Email or SMS alerts for administrators", "HTTPS, rate limiting and a least-privilege database user"], 7.2, 2.75, 5.1, 3.5, size=15, gap=10)

# =================================================================== 18. thanks
s = prs.slides.add_slide(BLANK); n_slide["n"] += 1
shape(s, 0, 0, 13.333, 7.5, fill=IVORY, name="bg")
shape(s, 8.6, -2.0, 7.0, 7.0, fill=SAGE, kind=MSO_SHAPE.OVAL, name="deco")
shape(s, -1.5, 5.2, 4.5, 4.5, fill="F1EBD9", kind=MSO_SHAPE.OVAL, name="deco")
shape(s, 0, 0, 0.14, 7.5, fill=GREEN, name="deco")
text(s, "Thank you", 0.8, 2.0, 9, 1.2, size=60, color=INK, font=SERIF)
shape(s, 0.84, 3.35, 1.1, 0.05, fill=GOLD, name="deco")
text(s, "Questions?", 0.8, 3.6, 8, 0.7, size=26, color=GREEN2, font=SERIF, italic=True)
for i, (nm, roll) in enumerate(TEAM):
    x = 0.8 + i * 3.05
    shape(s, x, 5.55, 0.03, 0.62, fill=SAGE2, name="deco")
    text(s, nm, x + 0.12, 5.51, 2.8, 0.4, size=17, bold=True, color=INK, font=SERIF)
    text(s, roll, x + 0.12, 5.89, 2.8, 0.3, size=12, color=MUTED)

out = ROOT / "docs" / "SmartWaste_AI_Presentation.pptx"
prs.save(out)
print(f"Wrote {out} with {len(prs.slides)} slides")
