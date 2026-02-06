import os
import math
import textwrap
import re
import random
import gradio as gr
from groq import Groq
from PIL import Image, ImageDraw, ImageFont

# ================= CONFIG =================

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

THEMES = {
    "Purple": {"bg": "white", "box": "#E1BEE7", "line": "#6A1B9A", "text": "black"},
    "Blue": {"bg": "white", "box": "#BBDEFB", "line": "#1E88E5", "text": "black"},
    "Dark": {"bg": "#1E1E1E", "box": "#2D2D2D", "line": "#B0B0B0", "text": "white"},
}

LEVEL_MAX_STEPS = {
    "Beginner": 6,
    "Intermediate": 10,
    "Advanced": 14,
}

FONT = ImageFont.load_default()

# ================= UTILS =================

def parse_months(duration):
    m = re.search(r"\d+", duration)
    return int(m.group()) if m else 3


def steps_from_months(months):
    return max(3, months * 2)


def compute_steps(months, level):
    return min(steps_from_months(months), LEVEL_MAX_STEPS[level])


def random_style():
    return random.choice([
        "hands-on focused",
        "project-driven",
        "theory-first",
        "tool-oriented",
        "problem-solving based",
        "real-world use cases"
    ])

# ================= DRAWING =================

def draw_arrow(draw, start, end, color):
    draw.line([start, end], fill=color, width=3)
    dx, dy = end[0] - start[0], end[1] - start[1]
    angle = math.atan2(dy, dx)
    hl, hw = 14, 7

    p1 = (
        end[0] - hl * math.cos(angle) + hw * math.sin(angle),
        end[1] - hl * math.sin(angle) - hw * math.cos(angle)
    )
    p2 = (
        end[0] - hl * math.cos(angle) - hw * math.sin(angle),
        end[1] - hl * math.sin(angle) + hw * math.cos(angle)
    )
    draw.polygon([end, p1, p2], fill=color)


def draw_box(draw, cx, y, w, text, theme):
    wrapped = textwrap.wrap(text, width=38)
    h = 34 + len(wrapped) * 18
    x = cx - w // 2

    draw.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=20,
        fill=theme["box"],
        outline=theme["line"],
        width=3,
    )

    ty = y + 12
    for line in wrapped:
        tw = draw.textlength(line, font=FONT)
        draw.text((cx - tw // 2, ty), line, fill=theme["text"], font=FONT)
        ty += 18

    return (x, y, x + w, y + h)

# ================= AI =================

def generate_roadmap(domain, level, duration):
    months = parse_months(duration)
    steps_count = compute_steps(months, level)

    prompt = f"""
You are an expert curriculum designer.

Create a RANDOM learning roadmap.
Domain: {domain}
Level: {level}
Duration: {months} months

Style: {random_style()}

Rules:
- Steps must vary on every generation
- No generic repeated templates
- Each step is a clear learning milestone
- Return EXACTLY {steps_count} steps
- One step per line
- No numbering
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    return [
        s.strip()
        for s in response.choices[0].message.content.split("\n")
        if s.strip()
    ][:steps_count]

# ================= ROADMAP IMAGE =================

def draw_roadmap(steps, theme_name):
    theme = THEMES[theme_name]
    cx, top, gap, bw = 500, 60, 35, 620

    height = top + 60
    for s in steps:
        height += 34 + len(textwrap.wrap(s, 38)) * 18 + gap

    img = Image.new("RGB", (1000, height), theme["bg"])
    draw = ImageDraw.Draw(img)

    y, boxes = top, []
    for s in steps:
        box = draw_box(draw, cx, y, bw, s, theme)
        boxes.append(box)
        y = box[3] + gap

    for i in range(len(boxes) - 1):
        start = ((boxes[i][0] + boxes[i][2]) // 2, boxes[i][3] + 6)
        end = ((boxes[i + 1][0] + boxes[i + 1][2]) // 2, boxes[i + 1][1] - 6)
        draw_arrow(draw, start, end, theme["line"])

    path = "/tmp/roadmap.png"
    img.save(path)
    return path

# ================= MAIN =================

def run(domain, level, duration, theme):
    steps = generate_roadmap(domain, level, duration)
    img_path = draw_roadmap(steps, theme)

    txt_path = "/tmp/roadmap.txt"
    with open(txt_path, "w") as f:
        f.write("\n".join(steps))

    return "\n".join(steps), img_path, txt_path

# ================= UI =================

css = """
body {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
}

label {
    color: #d0d0ff !important;
    font-weight: 600;
}

input, textarea, select {
    background-color: #1e1e2f !important;
    color: white !important;
    border-radius: 10px !important;
    border: 1px solid #6c63ff !important;
}

button {
    background: linear-gradient(90deg, #7f00ff, #e100ff) !important;
    color: white !important;
    font-weight: bold !important;
    border-radius: 14px !important;
    padding: 12px !important;
}

button:hover {
    box-shadow: 0 0 16px rgba(225, 0, 255, 0.6);
}
"""

with gr.Blocks(css=css) as demo:
    gr.Markdown("""
    <h1 style="text-align:center;color:white;">
    🗺️ AI Learning Roadmap Generator
    </h1>
    <p style="text-align:center;color:#c7c7ff;">
    Dynamic roadmaps based on duration & level
    </p>
    """)

    with gr.Group():
        domain = gr.Textbox(value="Machine Learning", label="Domain")
        level = gr.Dropdown(["Beginner", "Intermediate", "Advanced"], value="Beginner", label="Level")
        duration = gr.Textbox(value="3 months", label="Duration")
        theme = gr.Dropdown(list(THEMES.keys()), value="Purple", label="Diagram Theme")

    btn = gr.Button("🚀 Generate Roadmap")

    with gr.Group():
        txt = gr.Textbox(lines=15, label="Roadmap Steps")
        img = gr.Image(label="Roadmap Diagram")
        file = gr.File(label="Download Steps")

    btn.click(run, [domain, level, duration, theme], [txt, img, file])

demo.launch()
