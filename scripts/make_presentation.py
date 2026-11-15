"""Build docs/SmartWaste_AI_Presentation.pptx from real project artefacts.

Metrics are read from ml/model/evaluation*.txt and docs/TESTING.md; screenshots come from docs/screenshots
(produced by tests/e2e/run_e2e.py). Re-run this after retraining or re-testing:
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
SHOTS = ROOT / "docs" / "screenshots"
MODEL = ROOT / "ml" / "model"

GREEN, DARK, INK, MUTED, LIGHT = RGBColor(0x16, 0xA3, 0x4A), RGBColor(0x0B, 0x1F, 0x17), RGBColor(0x0F, 0x17, 0x2A), RGBColor(0x64, 0x74, 0x8B), RGBColor(0xF0, 0xFD, 0xF4)
WHITE, AMBER, RED = RGBColor(255, 255, 255), RGBColor(0xF5, 0x9E, 0x0B), RGBColor(0xDC, 0x26, 0x26)


def read_acc(path):
    m = re.search(r"Test accuracy: ([0-9.]+) \((\d+) images\)", path.read_text(encoding="utf-8"))
    return float(m.group(1)) * 100, int(m.group(2))


def read_report(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s+(glass|metal|organic|paper|plastic)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+(\d+)", line)
        if m:
            rows[m.group(1)] = tuple(m.groups()[1:])
    macro = re.search(r"macro avg\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", path.read_text(encoding="utf-8"))
    return rows, float(macro.group(3))


ACC, N_TEST = read_acc(MODEL / "evaluation.txt")
BASE_ACC, _ = read_acc(MODEL / "evaluation_baseline.txt")
ROWS, MACRO = read_report(MODEL / "evaluation.txt")
_, BASE_MACRO = read_report(MODEL / "evaluation_baseline.txt")
testing = (ROOT / "docs" / "TESTING.md").read_text(encoding="utf-8")
UNIT = re.search(r"\*\*Result: (\d+) passed", testing).group(1)
E2E = re.search(r"\*\*Result: (\d+)/(\d+) checks passed", testing)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
counter = {"n": 0}


def box(slide, l, t, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def text(slide, s, l, t, w, h, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    lines = s if isinstance(s, list) else [s]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = line
        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bold, color
        r.font.name = "Calibri"
    return tb


def bullets(slide, items, l, t, w, h, size=18, color=INK, gap=8):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        head, _, rest = it.partition("::")
        r0 = p.add_run(); r0.text = "•  "; r0.font.size = Pt(size); r0.font.color.rgb = GREEN; r0.font.bold = True
        if rest:
            r1 = p.add_run(); r1.text = head.strip() + " "; r1.font.bold = True
            r2 = p.add_run(); r2.text = rest.strip()
            runs = (r1, r2)
        else:
            r1 = p.add_run(); r1.text = head.strip(); runs = (r1,)
        for r in runs:
            r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = "Calibri"
    return tb


def slide(title, notes=None, subtitle=None):
    s = prs.slides.add_slide(BLANK)
    counter["n"] += 1
    box(s, 0, 0, 13.333, 7.5, fill=WHITE)
    box(s, 0, 0, 0.25, 7.5, fill=GREEN)
    text(s, title, 0.7, 0.4, 12, 0.8, size=32, bold=True, color=DARK)
    if subtitle:
        text(s, subtitle, 0.7, 1.15, 12, 0.5, size=16, color=MUTED)
    text(s, f"SmartWaste AI  ·  {counter['n']}", 11.3, 7.05, 1.8, 0.3, size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def picture(s, path, l, t, max_w, max_h, crop_h=None, border=True):
    img = Image.open(path).convert("RGB")
    if crop_h:
        img = img.crop((0, 0, img.width, min(img.height, crop_h)))
    buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
    ratio = min(max_w / img.width, max_h / img.height)
    w, h = img.width * ratio, img.height * ratio
    left = l + (max_w - w) / 2
    if border:
        box(s, left - 0.04, t - 0.04, w + 0.08, h + 0.08, fill=RGBColor(0xE2, 0xE8, 0xF0))
    s.shapes.add_picture(buf, Inches(left), Inches(t), Inches(w), Inches(h))


def table(s, data, l, t, w, h, col_w=None, size=14, header_fill=DARK):
    rows, cols = len(data), len(data[0])
    gt = s.shapes.add_table(rows, cols, Inches(l), Inches(t), Inches(w), Inches(h)).table
    for c in range(cols):
        if col_w:
            gt.columns[c].width = Inches(col_w[c])
    for r in range(rows):
        for c in range(cols):
            cell = gt.cell(r, c); cell.text = str(data[r][c])
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
            for run in para.runs:
                run.font.size = Pt(size); run.font.name = "Calibri"
                run.font.bold = r == 0 or (c == 0)
                run.font.color.rgb = WHITE if r == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if r == 0 else (LIGHT if r % 2 == 0 else WHITE)
    return gt


def stat(s, l, t, w, number, label, color=GREEN):
    box(s, l, t, w, 1.5, fill=LIGHT, line=RGBColor(0xBB, 0xF7, 0xD0), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, number, l, t + 0.15, w, 0.8, size=38, bold=True, color=color, align=PP_ALIGN.CENTER)
    text(s, label, l + 0.1, t + 0.95, w - 0.2, 0.5, size=14, color=MUTED, align=PP_ALIGN.CENTER)


# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK); counter["n"] += 1
box(s, 0, 0, 13.333, 7.5, fill=DARK)
box(s, 0, 5.4, 13.333, 0.06, fill=GREEN)
text(s, "AI-Powered Smart Waste Management", 0.8, 1.9, 11.5, 1.2, size=46, bold=True, color=WHITE)
text(s, "and Monitoring System", 0.8, 2.9, 11.5, 1, size=46, bold=True, color=RGBColor(0x4A, 0xDE, 0x80))
text(s, "CNN waste classification  ·  virtual smart bins  ·  real-time monitoring", 0.8, 4.2, 11.5, 0.6, size=22, color=RGBColor(0xCB, 0xD5, 0xE1))
text(s, "Python · Flask · TensorFlow/Keras · OpenCV · MySQL · Chart.js", 0.8, 5.7, 11.5, 0.5, size=18, color=RGBColor(0x94, 0xA3, 0xB8))
text(s, "Team presentation and demonstration", 0.8, 6.2, 11.5, 0.5, size=16, color=RGBColor(0x94, 0xA3, 0xB8))
s.notes_slide.notes_text_frame.text = "Introduce the team and the one-line pitch: a photo of waste goes in, a routed, monitored bin comes out."

# ---------------------------------------------------------------- 2 problem
s = slide("The problem and our goal", "Bins are emptied on fixed schedules and waste is mixed. We want sorting at the source and collection when needed.")
text(s, "Problem", 0.7, 1.4, 5.8, 0.5, size=22, bold=True, color=GREEN)
bullets(s, ["Mixed waste::lowers recycling rates", "Fixed collection rounds::empty bins get visited, full bins overflow", "No data::managers cannot see what is thrown away or where"], 0.7, 2.0, 5.8, 3.5, size=20)
text(s, "Our solution", 6.9, 1.4, 5.8, 0.5, size=22, bold=True, color=GREEN)
bullets(s, ["Classify::a CNN identifies plastic, paper, metal, glass or organic from a photo", "Route::the item goes to the matching compartment of a virtual smart bin", "Monitor::admins see fill levels, alerts and collections live", "Analyse::trends by day, week, month, location and category"], 6.9, 2.0, 5.9, 4, size=20)
box(s, 0.7, 6.0, 12, 0.8, fill=LIGHT, line=RGBColor(0xBB, 0xF7, 0xD0), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, "No hardware needed: bin fullness is simulated from configured capacity and estimated item volume, not sensors.", 0.9, 6.1, 11.6, 0.6, size=16, color=DARK, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 3 workflow
s = slide("How it works", "Walk left to right through the four steps.")
steps = [("1  Capture", "Upload a photo or use the webcam; pick the disposal location"), ("2  Classify", "CNN predicts the category and a confidence %"), ("3  Route", "Item goes to the matching compartment; simulated fill rises"), ("4  Collect", "Alert at 90%; admin collects and resets capacity")]
for i, (h, d) in enumerate(steps):
    x = 0.7 + i * 3.1
    box(s, x, 2.0, 2.8, 2.9, fill=LIGHT, line=RGBColor(0xBB, 0xF7, 0xD0), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, h, x + 0.15, 2.2, 2.5, 0.6, size=22, bold=True, color=GREEN)
    text(s, d, x + 0.15, 2.9, 2.5, 1.8, size=16, color=INK)
    if i < 3:
        text(s, "›", x + 2.8, 3.0, 0.3, 0.6, size=34, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
text(s, "Disposal advice is shown with every result, and every classification is stored for history and analytics.", 0.7, 5.4, 12, 0.6, size=18, color=MUTED)

# ---------------------------------------------------------------- 4 architecture
s = slide("System architecture", "Browser talks to Flask; Flask uses the CNN and MySQL. The dashboard polls every five seconds.")
layers = [("Browser", "HTML · CSS · JavaScript · Chart.js", 0.7, 2.0), ("Flask web app", "Auth · upload API · live API · admin", 4.7, 2.0), ("MySQL", "7 tables: users, locations, bins, compartments, waste records, collections, alerts", 8.9, 2.0)]
for h, d, x, y in layers:
    box(s, x, y, 3.8, 1.7, fill=LIGHT, line=GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, h, x + 0.1, y + 0.1, 3.6, 0.5, size=20, bold=True, color=DARK, align=PP_ALIGN.CENTER)
    text(s, d, x + 0.15, y + 0.65, 3.5, 1.0, size=14, color=MUTED, align=PP_ALIGN.CENTER)
text(s, "⇄", 4.5, 2.5, 0.4, 0.6, size=28, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
text(s, "⇄", 8.7, 2.5, 0.4, 0.6, size=28, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
box(s, 4.7, 4.3, 3.8, 1.3, fill=DARK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, "CNN model (Keras)", 4.8, 4.4, 3.6, 0.5, size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
text(s, "OpenCV preprocessing → MobileNetV2", 4.8, 4.95, 3.6, 0.5, size=14, color=RGBColor(0xBB, 0xF7, 0xD0), align=PP_ALIGN.CENTER)
text(s, "▲▼", 6.35, 3.75, 0.8, 0.5, size=18, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
bullets(s, ["Waitress server, /health check, rotating logs", "Docker Compose: web app + MySQL; CI builds and tests on every push"], 0.7, 5.9, 12, 1.2, size=16, color=MUTED, gap=4)

# ---------------------------------------------------------------- 5 dataset / method
s = slide("AI model: data and method", "6,576 images after mapping 12 original classes to our 5 categories.")
table(s, [["Category", "Source folders", "Images"], ["Paper", "paper, cardboard", "1,941"], ["Glass", "brown, green, white glass", "2,016"], ["Organic", "biological", "985"], ["Plastic", "plastic", "865"], ["Metal", "metal", "769"]], 0.7, 1.6, 6.3, 3.2, col_w=[1.6, 3.4, 1.3], size=15)
text(s, "Split 70 / 15 / 15:  4,608 train · 984 validation · 984 test", 0.7, 5.0, 6.5, 0.5, size=16, bold=True, color=DARK)
text(s, "Skipped: trash, battery, clothes, shoes. Images resized to 128×128 with OpenCV.", 0.7, 5.45, 6.5, 0.8, size=14, color=MUTED)
text(s, "Method", 7.6, 1.5, 5, 0.5, size=22, bold=True, color=GREEN)
bullets(s, ["Transfer learning::MobileNetV2 with ImageNet weights", "Two phases::train the new head, then fine-tune the top 40 layers", "Augmentation::flip, rotation, zoom, contrast", "Class weights::counter the imbalance (glass is 2.6× metal)", "Honest evaluation::test set untouched until the end"], 7.6, 2.1, 5.3, 4.5, size=17)

# ---------------------------------------------------------------- 6 results
s = slide("AI model: results", f"Deployed model {ACC:.1f}% on {N_TEST} held-out images, up from {BASE_ACC:.1f}% for the from-scratch CNN.")
stat(s, 0.7, 1.5, 2.6, f"{ACC:.1f}%", "test accuracy (deployed)")
stat(s, 3.5, 1.5, 2.6, f"{BASE_ACC:.1f}%", "baseline CNN", color=AMBER)
stat(s, 0.7, 3.2, 2.6, f"{MACRO:.2f}", "macro F1 (deployed)")
stat(s, 3.5, 3.2, 2.6, f"{BASE_MACRO:.2f}", "macro F1 (baseline)", color=AMBER)
data = [["Class", "Precision", "Recall", "F1"]] + [[c.capitalize(), *ROWS[c][:3]] for c in ("paper", "organic", "glass", "metal", "plastic")]
table(s, data, 0.7, 4.95, 5.4, 2.0, col_w=[1.5, 1.3, 1.3, 1.3], size=13)
picture(s, MODEL / "confusion_matrix.png", 6.6, 1.5, 6.2, 4.6)
text(s, "Weakest classes: metal and plastic (reflective surfaces look alike).", 6.6, 6.25, 6.2, 0.7, size=15, color=MUTED)

# ---------------------------------------------------------------- 7 bins
s = slide("Virtual smart bins and capacity rules", "Explain simulated fullness clearly: configured capacity and estimated volume.")
bullets(s, ["Locations::College Block A and B, Hostel, Canteen, Library (admins can add more)", "Bins::6 virtual bins; each has one compartment per category", "Assignment::item goes to the emptiest matching compartment with room at the chosen location", "Estimated volume::litres per item (plastic 0.5, paper 0.3, metal 0.25, glass 0.6, organic 0.8)", "Fill %::load ÷ configured capacity"], 0.7, 1.6, 7.0, 5, size=18)
table(s, [["Highest fill", "Status", "Action"], ["below 70%", "Normal", "none"], ["70% to under 90%", "Almost full", "listed for collection"], ["90% or more", "Collection required", "alert + pending collection"]], 8.0, 1.8, 4.9, 2.4, col_w=[1.6, 1.7, 1.6], size=13)
text(s, "If a compartment has no room, the item is still recorded but flagged as unassigned.", 8.0, 4.5, 4.9, 1.0, size=15, color=MUTED)

# ---------------------------------------------------------------- 8 classify UI
s = slide("Classification experience", "Live demo moment: classify an image and point at confidence, tip and bin.")
picture(s, SHOTS / "classify_result.png", 0.7, 1.4, 8.0, 5.4)
bullets(s, ["Drag and drop or webcam", "Result without page reload", "Confidence ring and category", "Disposal recommendation", "Shows the assigned bin and compartment"], 9.0, 1.7, 4.0, 4.5, size=18)

# ---------------------------------------------------------------- 9 dashboard
s = slide("Real-time admin dashboard", "Show Window A updating while Window B classifies.")
picture(s, SHOTS / "admin_dashboard.png", 0.7, 1.4, 8.0, 5.5, crop_h=1180)
bullets(s, ["Refreshes every 5 s", "Totals, recyclable share, category counts", "Normal / almost-full / collection-required bins", "Fill bars per compartment", "Live activity feed and alert toasts", "All figures from stored records"], 9.0, 1.6, 4.0, 5, size=17)

# ---------------------------------------------------------------- 10 collections
s = slide("Alerts and collection management", "At 90% an alert and a pending collection appear automatically.")
picture(s, SHOTS / "collections.png", 0.7, 1.4, 7.4, 5.5)
bullets(s, ["Alert at 90% of capacity", "Pending vs completed collections", "Mark collected: resets capacity", "Date, time and admin recorded", "Alerts resolved on collection"], 8.5, 1.8, 4.4, 4.5, size=18)

# ---------------------------------------------------------------- 11 analytics
s = slide("Analytics and reports", "Daily, weekly and monthly; location and category breakdowns; CSV export.")
picture(s, SHOTS / "analytics.png", 0.7, 1.4, 8.0, 5.5)
bullets(s, ["Daily, weekly, monthly trends", "Category-wise and location-wise", "Full classification history with filters", "CSV export (spreadsheet-safe)"], 9.0, 1.8, 4.0, 4.5, size=18)

# ---------------------------------------------------------------- 12 database
s = slide("Database design (MySQL)", "Seven tables as required.")
table(s, [["Table", "Purpose"], ["users", "users and admins, hashed passwords, role"], ["locations", "college blocks, hostel, canteen, library"], ["smart_bins", "virtual bins, each at one location"], ["bin_compartments", "per-category capacity and current load"], ["waste_records", "image, category, confidence, bin assignment"], ["collection_records", "pending/completed collections with timestamps"], ["alerts", "capacity alerts with resolved state"]], 0.7, 1.6, 8.0, 4.6, col_w=[2.6, 5.4], size=15)
bullets(s, ["Foreign keys and unique (bin, category)", "SQLAlchemy ORM; SQL aggregates for stats", "No fabricated rows: seed creates no waste records"], 9.1, 1.8, 3.9, 4, size=16)

# ---------------------------------------------------------------- 13 quality
s = slide("Security and testing", "Quote the numbers: they come from real test runs in docs/TESTING.md.")
stat(s, 0.7, 1.5, 3.7, UNIT, "automated tests passing (pytest)")
stat(s, 4.6, 1.5, 3.7, f"{E2E.group(1)}/{E2E.group(2)}", "browser end-to-end checks (Edge)")
stat(s, 8.5, 1.5, 3.7, f"{ACC:.1f}%", "model accuracy on held-out data")
bullets(s, ["Security::hashed passwords, CSRF protection, role-based access, validated uploads, private images, security headers", "Tested flows::auth, classification, bin assignment, 90% alert, collection reset, dashboard counts, analytics, CSV, live updates", "Not covered::real webcam capture, load testing, photos outside the dataset"], 0.7, 3.5, 12, 3.2, size=17)

# ---------------------------------------------------------------- 14 devops
s = slide("Production readiness", "Industrial touches beyond the minimum brief.")
bullets(s, ["Docker Compose::web app and MySQL start with one command", "GitHub Actions CI::runs tests and builds the image on every push", "Waitress server::production WSGI server, /health endpoint", "Logging::rotating log file; warnings for insecure configuration", "Configuration::all secrets in environment variables, none in code", "Demo tooling::scripted traffic and cleanup for presentations"], 0.7, 1.6, 12, 5, size=20)

# ---------------------------------------------------------------- 15 limits
s = slide("Limitations and next steps", "Say the limits before someone asks.")
text(s, "Limitations", 0.7, 1.5, 5.8, 0.5, size=22, bold=True, color=RED)
bullets(s, ["Fullness is simulated, not measured", "Dataset photos are mostly single objects on plain backgrounds", "Metal and plastic are the weakest classes", "No 'not waste / unknown' class yet"], 0.7, 2.1, 5.8, 4, size=18)
text(s, "Next steps", 6.9, 1.5, 5.8, 0.5, size=22, bold=True, color=GREEN)
bullets(s, ["Collect photos from the real campus bins", "Add an unknown class and a confidence threshold", "Higher resolution and EfficientNet", "Email/SMS notification for alerts", "Optional real sensors replacing the simulation"], 6.9, 2.1, 5.9, 4.5, size=18)

# ---------------------------------------------------------------- 16 team
s = slide("Team work distribution", "Replace 'Member N' with names.")
table(s, [["Member", "Responsibility"], ["Member 1", "Dataset collection and CNN model"], ["Member 2", "Frontend development"], ["Member 3", "Flask backend and AI integration"], ["Member 4", "MySQL database and virtual bin management"], ["Member 5", "Admin dashboard, analytics, testing and integration"]], 0.7, 1.7, 12, 3.6, col_w=[2.5, 9.5], size=18)
text(s, "Everyone understands the full workflow, even when each person owns a module.", 0.7, 5.7, 12, 0.6, size=18, color=MUTED)

# ---------------------------------------------------------------- 17 thanks
s = prs.slides.add_slide(BLANK); counter["n"] += 1
box(s, 0, 0, 13.333, 7.5, fill=DARK)
text(s, "Thank you", 0.8, 2.4, 11.5, 1.2, size=54, bold=True, color=WHITE)
text(s, "Questions?", 0.8, 3.6, 11.5, 0.8, size=30, color=RGBColor(0x4A, 0xDE, 0x80))
text(s, "Source code, documentation and test results are in the project repository.", 0.8, 5.2, 11.5, 0.6, size=18, color=RGBColor(0x94, 0xA3, 0xB8))

out = ROOT / "docs" / "SmartWaste_AI_Presentation.pptx"
prs.save(out)
print(f"Wrote {out} with {len(prs.slides)} slides")
