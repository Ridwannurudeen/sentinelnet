#!/usr/bin/env python3
"""Generate OG image for SentinelNet (1200x630)."""
import os
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
BG = (10, 10, 26)
CYAN = (0, 212, 255)
WHITE = (255, 255, 255)
GRAY = (160, 160, 180)
DARK_ACCENT = (20, 20, 45)

def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # Background grid pattern
    for x in range(0, WIDTH, 40):
        draw.line([(x, 0), (x, HEIGHT)], fill=(15, 15, 35), width=1)
    for y in range(0, HEIGHT, 40):
        draw.line([(0, y), (WIDTH, y)], fill=(15, 15, 35), width=1)

    # Shield icon (geometric)
    cx, cy = 160, 280
    shield_points = [
        (cx, cy - 100), (cx + 70, cy - 70), (cx + 70, cy + 20),
        (cx, cy + 80), (cx - 70, cy + 20), (cx - 70, cy - 70),
    ]
    draw.polygon(shield_points, fill=DARK_ACCENT, outline=CYAN)
    # Inner shield
    inner = [
        (cx, cy - 65), (cx + 45, cy - 45), (cx + 45, cy + 10),
        (cx, cy + 50), (cx - 45, cy + 10), (cx - 45, cy - 45),
    ]
    draw.polygon(inner, outline=CYAN, width=2)
    # Checkmark inside
    draw.line([(cx - 20, cy - 5), (cx - 5, cy + 15), (cx + 25, cy - 25)], fill=CYAN, width=4)

    # Try to use a nice font, fall back to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        badge_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except (OSError, IOError):
        try:
            title_font = ImageFont.truetype("arial.ttf", 72)
            sub_font = ImageFont.truetype("arial.ttf", 32)
            badge_font = ImageFont.truetype("arialbd.ttf", 22)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()
            badge_font = ImageFont.load_default()

    # Title
    draw.text((300, 200), "SentinelNet", fill=WHITE, font=title_font)

    # Subtitle
    draw.text((300, 290), "Trust Layer for ERC-8004 Agents", fill=GRAY, font=sub_font)

    # Stats line
    draw.text((300, 350), "Autonomous reputation scoring on Base", fill=(100, 100, 120), font=sub_font)

    # Cyan accent line
    draw.rectangle([(300, 280), (700, 284)], fill=CYAN)

    # Base Network badge
    badge_x, badge_y = 950, 530
    draw.rounded_rectangle([(badge_x, badge_y), (badge_x + 180, badge_y + 40)], radius=8, fill=(0, 82, 255), outline=(0, 112, 255))
    draw.text((badge_x + 20, badge_y + 8), "Base Network", fill=WHITE, font=badge_font)

    # Gradient overlay at bottom
    for y in range(HEIGHT - 80, HEIGHT):
        alpha = int((y - (HEIGHT - 80)) / 80 * 100)
        draw.line([(0, y), (WIDTH, y)], fill=(5, 5, 15))

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "og-image.png")
    img.save(out_path, "PNG", optimize=True)
    print(f"Generated: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    main()
