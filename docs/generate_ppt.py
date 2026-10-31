"""
GrowthPilot — Razorpay Buildathon 2026
Premium Dark-Themed PowerPoint Generator
Sections:
  1. WHAT I BUILT
  2. THE PROBLEM IT SOLVES
  3. HOW IT WORKS (DEMO)
  4. AI IMPLEMENTATION
  5. RAZORPAY INTEGRATION & KEY FEATURES
  6. CLOSING
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── Palette ─────────────────────────────────────────────────────────────────
BG          = RGBColor(0x0F, 0x17, 0x2A)
PANEL       = RGBColor(0x1E, 0x29, 0x3B)
BORDER_BLUE = RGBColor(0x38, 0xBD, 0xF8)
BORDER_GRN  = RGBColor(0x34, 0xD3, 0x99)
BORDER_PURP = RGBColor(0x81, 0x8C, 0xF8)
BORDER_AMB  = RGBColor(0xFB, 0xBF, 0x24)
BORDER_RED  = RGBColor(0xF8, 0x71, 0x71)
BORDER_LBLU = RGBColor(0x60, 0xA5, 0xFA)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
SLATE_300   = RGBColor(0xCB, 0xD5, 0xE1)
SLATE_400   = RGBColor(0x94, 0xA3, 0xB8)
SLATE_200   = RGBColor(0xE2, 0xE8, 0xF0)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
OUT_PATH   = os.path.join(SCRIPT_DIR, "..", "GrowthPilot_Buildathon_Deck_Simple.pptx")
ARCH_IMG   = os.path.join(SCRIPT_DIR, "architecture_diagram.png")
RZP_IMG    = os.path.join(SCRIPT_DIR, "razorpay_event_flow.png")



# ── Low-level helpers ────────────────────────────────────────────────────────

def set_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height,
             fill_color=None, line_color=None, line_width_pt=2):
    shape = slide.shapes.add_shape(
        1, Inches(left), Inches(top), Inches(width), Inches(height))
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(line_width_pt)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def add_text(slide, text, left, top, width, height,
             font_size=18, bold=False, italic=False,
             color=WHITE, align=PP_ALIGN.LEFT, font_name="Calibri"):
    tb = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return tb


def add_bullets(slide, lines, left, top, width, height,
                font_size=13, line_color=SLATE_200,
                font_name="Calibri", spacing_pt=4):
    tb = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(spacing_pt)
        run = p.add_run()
        run.text = f"• {line}"
        run.font.name = font_name
        run.font.size = Pt(font_size)
        run.font.color.rgb = line_color
    return tb


# ── Composite helpers ────────────────────────────────────────────────────────

def pill(slide, text, accent, top=0.18):
    add_rect(slide, 0.35, top, 3.6, 0.34, fill_color=accent, line_color=None)
    add_text(slide, text, 0.38, top + 0.03, 3.52, 0.28,
             font_size=10, bold=True, color=BG, align=PP_ALIGN.CENTER)


def title_bar(slide, title, accent=BORDER_BLUE, subtitle=None):
    add_text(slide, title, 0.35, 0.58, 12.6, 0.72,
             font_size=32, bold=True, color=WHITE)
    add_rect(slide, 0.35, 1.28, 12.6, 0.05, fill_color=accent, line_color=None)
    if subtitle:
        add_text(slide, subtitle, 0.35, 1.38, 12.6, 0.38,
                 font_size=14, color=SLATE_400, italic=True)


def card(slide, left, top, w, h, heading, bullets,
         accent=BORDER_BLUE, fs=13):
    add_rect(slide, left, top, w, h, fill_color=PANEL,
             line_color=accent, line_width_pt=1.5)
    add_text(slide, heading, left + 0.15, top + 0.1, w - 0.3, 0.38,
             font_size=14, bold=True, color=accent)
    add_bullets(slide, bullets, left + 0.18, top + 0.52,
                w - 0.36, h - 0.64, font_size=fs,
                line_color=SLATE_200, spacing_pt=3)


# ════════════════════════════════════════════════════════════════════════════
prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H
BL = prs.slide_layouts[6]   # Blank


# ─── SLIDE 1: COVER ─────────────────────────────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)

# Left accent bars
for i, c in enumerate([BORDER_BLUE, BORDER_GRN, BORDER_PURP, BORDER_LBLU]):
    add_rect(sl, 0, i * 1.875, 0.09, 1.875, fill_color=c, line_color=None)

# Main title box
add_rect(sl, 0.35, 1.55, 8.9, 1.65, fill_color=PANEL,
         line_color=BORDER_BLUE, line_width_pt=2.5)
add_text(sl, "GROWTHPILOT", 0.52, 1.67, 8.6, 0.78,
         font_size=46, bold=True, color=WHITE)
add_text(sl, "Your AI-Powered Growth Team", 0.52, 2.46, 8.6, 0.6,
         font_size=22, color=BORDER_BLUE)

# Tagline
add_rect(sl, 0.35, 3.32, 8.9, 0.68, fill_color=RGBColor(0x09, 0x0E, 0x1C),
         line_color=None)
add_text(sl, '"GrowthPilot finds the problem, makes a plan, and runs the campaign for you."',
         0.52, 3.38, 8.6, 0.56, font_size=13, italic=True, color=SLATE_400)

# Tech pills
pills = [("FastAPI", BORDER_PURP), ("Supabase Database", BORDER_GRN),
         ("Redis", BORDER_RED), ("Razorpay Payments", BORDER_LBLU),
         ("5 Smart AI Agents", BORDER_BLUE)]
px = 0.35
for lbl, col in pills:
    add_rect(sl, px, 4.18, 2.32, 0.38, fill_color=col, line_color=None)
    add_text(sl, lbl, px + 0.06, 4.2, 2.2, 0.32,
             font_size=11, bold=True, color=BG, align=PP_ALIGN.CENTER)
    px += 2.45

# Event badge
add_rect(sl, 9.9, 1.55, 3.08, 1.36, fill_color=PANEL,
         line_color=BORDER_AMB, line_width_pt=2)
add_text(sl, "RAZORPAY BUILDATHON", 9.95, 1.63, 2.98, 0.38,
         font_size=11, bold=True, color=BORDER_AMB, align=PP_ALIGN.CENTER)
add_text(sl, "2026", 9.95, 2.02, 2.98, 0.6,
         font_size=34, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
add_text(sl, "Submission", 9.95, 2.6, 2.98, 0.28,
         font_size=11, color=SLATE_400, align=PP_ALIGN.CENTER)

# Footer
add_rect(sl, 0, 6.9, 13.33, 0.6, fill_color=PANEL, line_color=None)
add_text(sl, "Multi-Store Support  ·  Secure Database  ·  Razorpay Checkout  ·  5 AI Agents  ·  Fully Tested",
         0.3, 6.96, 12.8, 0.4, font_size=11, color=SLATE_400, align=PP_ALIGN.CENTER)


# ─── SLIDE 2: WHAT I BUILT ──────────────────────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "01  ·  WHAT I BUILT", BORDER_BLUE)
title_bar(sl, "GrowthPilot — What I Built", accent=BORDER_BLUE)

card(sl, 0.35, 1.85, 4.15, 5.35,
     "🤖  Smart AI Team", [
         "5 specialized AI assistants working together",
         "Finds issues → Makes a plan → Runs campaigns",
         "Safety checks built-in to track results",
         "Uses real math, not just AI guessing",
         "You approve everything before it runs",
     ], accent=BORDER_GRN)

card(sl, 4.62, 1.85, 4.15, 5.35,
     "🗄️  Strong Foundation", [
         "Fast and reliable API (FastAPI)",
         "Secure Database for user data (Supabase)",
         "Built to handle multiple stores at once",
         "Easy and safe database updates",
         "Works offline for easy development",
     ], accent=BORDER_PURP)

card(sl, 8.88, 1.85, 4.15, 5.35,
     "⚡  Real-Time Connections", [
         "Fast event tracking with Redis",
         "Quick data loading with smart caching",
         "Prevents the system from getting overloaded",
         "Creates Razorpay payment links automatically",
         "Secure communication with Razorpay",
     ], accent=BORDER_AMB)

add_rect(sl, 0.35, 7.22, 12.6, 0.2, fill_color=PANEL, line_color=None)
add_text(sl, "Built with Python · Clean Dashboard · Fully Automated Testing",
         0.4, 7.22, 12.5, 0.2, font_size=10, color=SLATE_400, align=PP_ALIGN.CENTER)


# ─── SLIDE 3: THE PROBLEM ────────────────────────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "02  ·  THE PROBLEM", BORDER_RED)
title_bar(sl, "The Problem: Lots of Data, No Action", accent=BORDER_RED)

add_rect(sl, 0.35, 1.85, 6.2, 5.42, fill_color=PANEL,
         line_color=BORDER_RED, line_width_pt=2)
add_text(sl, "❌  The Reality Today", 0.55, 1.98, 5.9, 0.4,
         font_size=16, bold=True, color=BORDER_RED)
add_bullets(sl, [
    "Dashboards show past problems, but don't tell you what to do next.",
    "Store owners have to guess the best marketing move.",
    "Calculating safe discounts takes hours and leads to mistakes.",
    "Giving everyone the same discount loses the store money.",
    "Creating payment links is a slow, manual process.",
    "It's hard to know if a campaign actually worked.",
    "Mistakes are repeated because there is no feedback loop.",
], 0.55, 2.48, 5.8, 4.5, font_size=13.5, spacing_pt=6)

add_rect(sl, 6.78, 1.85, 6.2, 5.42, fill_color=PANEL,
         line_color=BORDER_GRN, line_width_pt=2)
add_text(sl, "✅  GrowthPilot Solves This", 6.96, 1.98, 5.9, 0.4,
         font_size=16, bold=True, color=BORDER_GRN)
add_bullets(sl, [
    "Finds the best ways to grow your sales automatically.",
    "Uses strict math to calculate safe discounts that protect profits.",
    "Prioritizes the best campaigns to run right now.",
    "Writes the marketing emails for you to win customers back.",
    "Creates Razorpay checkout links with just one click.",
    "Tests the results to prove the campaign actually worked.",
    "Learns from mistakes and improves its suggestions over time.",
], 6.96, 2.48, 5.8, 4.5, font_size=13.5, spacing_pt=6)

# Arrow divider
add_rect(sl, 6.44, 3.9, 0.34, 0.7, fill_color=BORDER_AMB, line_color=None)
add_text(sl, "→", 6.4, 3.98, 0.44, 0.55,
         font_size=22, bold=True, color=BG, align=PP_ALIGN.CENTER)


# ─── SLIDE 4: HOW IT WORKS — Architecture diagram ───────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "03  ·  HOW IT WORKS", BORDER_GRN)
title_bar(sl, "System Overview", accent=BORDER_GRN)

if os.path.exists(ARCH_IMG):
    sl.shapes.add_picture(ARCH_IMG,
                          Inches(0.35), Inches(1.85),
                          Inches(12.6), Inches(5.45))
else:
    add_text(sl, "[docs/architecture_diagram.png]", 0.5, 3.5, 12.3, 1.0,
             font_size=16, color=SLATE_400, align=PP_ALIGN.CENTER)


# ─── SLIDE 5: HOW IT WORKS — Step-by-step demo flow ────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "03  ·  HOW IT WORKS (DEMO)", BORDER_GRN)
title_bar(sl, "End-to-End Demo: SoundWave Audio", accent=BORDER_GRN)

steps = [
    ("1", "Login to Dashboard",
     "The manager logs into the GrowthPilot dashboard to view their store's data.",
     BORDER_BLUE),
    ("2", "AI Finds a Problem",
     "The AI notices that 71% of customers are leaving a product in their cart without buying.",
     BORDER_PURP),
    ("3", "AI Ranks the Opportunity",
     "The AI calculates that fixing this is worth ₹81,600 and ranks it as the #1 priority.",
     BORDER_GRN),
    ("4", "AI Creates a Plan",
     "The AI suggests an 8% discount (which is safe for margins) and writes the campaign email.",
     BORDER_AMB),
    ("5", "You Approve It",
     "The manager reviews the plan, clicks 'Approve', and GrowthPilot instantly creates a Razorpay payment link.",
     BORDER_LBLU),
    ("6", "AI Learns from Results",
     "When customers pay via Razorpay, the AI tracks the success and learns that the campaign worked.",
     BORDER_GRN),
]

y = 1.88
for num, title, desc, col in steps:
    add_rect(sl, 0.35, y, 0.58, 0.72, fill_color=col, line_color=None)
    add_text(sl, num, 0.35, y + 0.1, 0.58, 0.52,
             font_size=18, bold=True, color=BG, align=PP_ALIGN.CENTER)
    add_rect(sl, 1.05, y, 12.0, 0.72, fill_color=PANEL,
             line_color=col, line_width_pt=1)
    add_text(sl, title, 1.22, y + 0.06, 3.0, 0.3,
             font_size=13, bold=True, color=col)
    add_text(sl, desc, 1.22, y + 0.38, 11.6, 0.28,
             font_size=11.5, color=SLATE_300)
    y += 0.83


# ─── SLIDE 6: AI IMPLEMENTATION ─────────────────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "04  ·  HOW THE AI WORKS", BORDER_PURP)
title_bar(sl, "5 Smart Agents Working Together", accent=BORDER_PURP)

agents = [
    ("1  Insight Agent",           BORDER_BLUE,
     "Scans your store data to find problems, like customers who are likely to stop buying."),
    ("2  Decision Agent",         BORDER_GRN,
     "Looks at all the problems and ranks them, showing you the most important ones first."),
    ("3  Pricing Agent",          BORDER_AMB,
     "Calculates safe discount amounts so you always maintain a healthy profit margin."),
    ("4  Guardrail Agent",        BORDER_RED,
     "Acts as a safety check. It makes sure no campaigns are sent without your final approval."),
    ("5  Experiment Agent",       BORDER_PURP,
     "Monitors the results of the campaigns and learns what works best for the future."),
]

y = 1.9
for name, col, desc in agents:
    add_rect(sl, 0.35, y, 12.6, 0.84, fill_color=PANEL,
             line_color=col, line_width_pt=1.5)
    add_text(sl, name, 0.55, y + 0.06, 4.0, 0.36,
             font_size=14, bold=True, color=col)
    add_text(sl, desc, 0.55, y + 0.44, 12.2, 0.34,
             font_size=13, color=SLATE_300, italic=False)
    y += 0.98

add_rect(sl, 0.35, 6.78, 12.6, 0.58, fill_color=RGBColor(0x07, 0x2B, 0x1A),
         line_color=BORDER_GRN, line_width_pt=1)
add_text(sl, "⚡  Why Math instead of just AI? — AI models can make mistakes with numbers. "
             "GrowthPilot uses strict math formulas for pricing to guarantee you never give a discount that destroys your profit.",
         0.55, 6.83, 12.2, 0.48, font_size=12, color=BORDER_GRN)


# ─── SLIDE 7: RAZORPAY — Event flow diagram ─────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "05  ·  RAZORPAY", BORDER_LBLU)
title_bar(sl, "Razorpay Payment Flow", accent=BORDER_LBLU)

if os.path.exists(RZP_IMG):
    sl.shapes.add_picture(RZP_IMG,
                          Inches(0.35), Inches(1.85),
                          Inches(12.6), Inches(4.9))
else:
    add_text(sl, "[docs/razorpay_event_flow.png]", 0.5, 3.5, 12.3, 1.0,
             font_size=16, color=SLATE_400, align=PP_ALIGN.CENTER)

add_rect(sl, 0.35, 6.9, 12.6, 0.48, fill_color=PANEL, line_color=None)
add_text(sl, "Payment Occurs → Verified Securely → Queued for Processing "
             "→ AI Learns from the Result → Secure Log Saved",
         0.5, 6.94, 12.4, 0.38, font_size=11, color=SLATE_400, align=PP_ALIGN.CENTER)


# ─── SLIDE 8: RAZORPAY KEY FEATURES ─────────────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "05  ·  KEY FEATURES", BORDER_LBLU)
title_bar(sl, "Razorpay Integration Features", accent=BORDER_LBLU)

features = [
    ("Instant Payment Links", BORDER_LBLU, [
        "Creates Razorpay orders automatically.",
        "Generates payment links as soon as you approve a campaign.",
        "Automatically retries if there are any network issues.",
    ]),
    ("Secure Communication", BORDER_GRN, [
        "Checks every message to ensure it's really from Razorpay.",
        "Uses strong security to prevent hacking.",
        "Saves a secure code for every event to prove it's real.",
    ]),
    ("Fast Event Processing", BORDER_RED, [
        "Handles messages from Razorpay instantly.",
        "Processes payments in the background so the dashboard stays fast.",
        "Tracks successful payments and failures easily.",
    ]),
    ("Smart Failure Tracking", BORDER_AMB, [
        "If a payment fails, the AI learns that the offer didn't work.",
        "Saves the reason why the payment failed.",
        "Stops the AI from repeating the same mistakes.",
    ]),
    ("System Protection", BORDER_PURP, [
        "Limits how many requests can happen at once.",
        "Keeps the system safe from being overloaded.",
        "Gracefully handles too much traffic.",
    ]),
    ("Secure Activity Log", BORDER_BLUE, [
        "Records everything the system does.",
        "Hides all sensitive customer and card information.",
        "Creates an unchangeable, secure history of events.",
    ]),
]

x, y = 0.35, 1.85
for i, (title, col, buls) in enumerate(features):
    card(sl, x, y, 4.15, 2.44, title, buls, accent=col, fs=13)
    x += 4.32
    if i == 2:
        x, y = 0.35, 4.44


# ─── SLIDE 9: TECH STACK TABLE ───────────────────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)
pill(sl, "05  ·  TECHNOLOGY", BORDER_LBLU)
title_bar(sl, "The Tools Behind GrowthPilot", accent=BORDER_LBLU)

rows = [
    ("FastAPI",            "Main Server",                       "Fast and reliable way to connect the dashboard and the AI.",          BORDER_PURP),
    ("Supabase Postgres",  "Database",                          "Safely stores data and keeps different stores separated.",    BORDER_GRN),
    ("SQLite",             "Backup Database",                   "Allows the system to run offline on a local computer easily.",BORDER_BLUE),
    ("Redis",              "Speed & Queues",                    "Makes the app fast and handles Razorpay messages smoothly.",    BORDER_RED),
    ("Razorpay",           "Payments",                          "Industry standard for creating checkouts and accepting money.",    BORDER_LBLU),
    ("Pandas / NumPy",     "Data Analysis",                     "Quickly crunches numbers and finds trends in the data.",   BORDER_GRN),
    ("JWT Authentication", "Security",                          "Ensures that only authorized users can access their store data.",BORDER_AMB),
    ("Alembic",            "Database Updates",                  "Safely manages updates to the database structure.",            BORDER_PURP),
]

col_w = [2.55, 2.8, 6.6]
col_x = [0.35, 2.9, 5.7]
hdrs  = ["Tool", "What it does", "Why we use it"]

y = 1.9
for ci, (h, cw, cx) in enumerate(zip(hdrs, col_w, col_x)):
    add_rect(sl, cx, y, cw, 0.4, fill_color=BORDER_BLUE, line_color=None)
    add_text(sl, h, cx + 0.08, y + 0.07, cw - 0.16, 0.28,
             font_size=12, bold=True, color=BG, align=PP_ALIGN.CENTER)
y += 0.44

for ri, (tech, role, why, col) in enumerate(rows):
    row_bg = PANEL if ri % 2 == 0 else RGBColor(0x16, 0x20, 0x32)
    for val, cw, cx, fc, lc in [
        (tech, col_w[0], col_x[0], col,       col),
        (role, col_w[1], col_x[1], SLATE_200, RGBColor(0x33, 0x41, 0x55)),
        (why,  col_w[2], col_x[2], SLATE_300, RGBColor(0x33, 0x41, 0x55)),
    ]:
        add_rect(sl, cx, y, cw, 0.5, fill_color=row_bg,
                 line_color=lc, line_width_pt=0.75)
        add_text(sl, val, cx + 0.1, y + 0.08, cw - 0.2, 0.36,
                 font_size=12, bold=(fc == col), color=fc)
    y += 0.54


# ─── SLIDE 10: CLOSING ──────────────────────────────────────────────────────
sl = prs.slides.add_slide(BL)
set_bg(sl, BG)

# Right accent bars
for i, c in enumerate([BORDER_LBLU, BORDER_GRN, BORDER_AMB, BORDER_PURP]):
    add_rect(sl, 13.24, i * 1.875, 0.09, 1.875, fill_color=c, line_color=None)

pill(sl, "06  ·  CLOSING", BORDER_AMB)

# Big headline box
add_rect(sl, 0.5, 1.52, 12.33, 2.06, fill_color=PANEL,
         line_color=BORDER_AMB, line_width_pt=2.5)
add_text(sl, "The Future of E-Commerce Growth", 0.65, 1.65, 12.0, 0.72,
         font_size=30, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
add_text(sl, "Smart AI  ·  Safe Decisions  ·  Fully Automated",
         0.65, 2.34, 12.0, 0.44, font_size=17, color=BORDER_AMB,
         align=PP_ALIGN.CENTER, italic=True)
add_rect(sl, 1.2, 2.86, 10.93, 0.06, fill_color=BORDER_AMB, line_color=None)
add_text(sl, "GrowthPilot doesn't just show you data — it acts on it, safely and easily.",
         0.65, 2.98, 12.0, 0.42, font_size=15, color=SLATE_300,
         align=PP_ALIGN.CENTER, italic=True)

# Three closing pillars
pillars = [
    ("🔍  Find",     "The AI scans your store\nand finds the best\nopportunities to make money.",       BORDER_BLUE),
    ("🎯  Decide",   "The AI calculates safe\ndiscounts and plans\nthe perfect campaign.",      BORDER_GRN),
    ("⚡  Execute",  "You approve it,\nGrowthPilot creates the link,\nand tracks the success.",BORDER_AMB),
]
px = 0.9
for label, desc, col in pillars:
    add_rect(sl, px, 3.66, 3.6, 2.78, fill_color=PANEL,
             line_color=col, line_width_pt=2)
    add_text(sl, label, px + 0.15, 3.78, 3.3, 0.52,
             font_size=20, bold=True, color=col, align=PP_ALIGN.CENTER)
    add_text(sl, desc, px + 0.15, 4.34, 3.3, 1.9,
             font_size=13, color=SLATE_300, align=PP_ALIGN.CENTER)
    px += 3.84

# Footer
add_rect(sl, 0, 6.82, 13.33, 0.68, fill_color=PANEL, line_color=None)
add_text(sl, "Thank you  ·  Built for Razorpay Buildathon 2026",
         0.3, 6.88, 12.8, 0.34, font_size=13, color=SLATE_400, align=PP_ALIGN.CENTER)
add_text(sl, "github.com/[your-handle]/GrowthPilot",
         0.3, 7.18, 12.8, 0.26, font_size=12, color=BORDER_BLUE, align=PP_ALIGN.CENTER)


# ─── Save ────────────────────────────────────────────────────────────────────
prs.save(OUT_PATH)
print(f"Saved: {os.path.abspath(OUT_PATH)}")
