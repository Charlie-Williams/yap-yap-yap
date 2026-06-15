"""Generate the YapYapYap bird logo (a cheerful, noisy yellow bird) at several
sizes plus a Windows .ico. Run:  python -m yapyapyap.tools.make_logo"""
import os
import math
from PIL import Image, ImageDraw

from yapyapyap import config

S = 4  # supersample factor
W = 256 * S

YELLOW = (255, 222, 33)
YELLOW_DK = (242, 194, 0)
YELLOW_LT = (255, 236, 130)
INK = (26, 26, 23)
ORANGE = (245, 150, 30)
ORANGE_DK = (224, 120, 12)
WHITE = (255, 255, 255)
BLUSH = (250, 170, 120)


def px(*v):
    return tuple(int(x * S) for x in v)


def ellipse(d, cx, cy, rx, ry, fill, outline=None, w=0):
    d.ellipse([px(cx - rx, cy - ry)[0], px(cx - rx, cy - ry)[1],
               px(cx + rx, cy + ry)[0], px(cx + rx, cy + ry)[1]],
              fill=fill, outline=outline, width=int(w * S))


def draw_bird(d):
    OL = INK
    ow = 5  # outline width (pre-scale)

    # ---- tail ----
    d.polygon([px(70, 150)[0], px(70, 150)[1], px(120, 120)[0], px(120, 120)[1],
               px(120, 175)[0], px(120, 175)[1]], fill=YELLOW_DK, outline=OL, width=int(ow * S))

    # ---- body ----
    ellipse(d, 150, 150, 78, 86, YELLOW, OL, ow)
    # belly highlight
    ellipse(d, 158, 168, 50, 56, YELLOW_LT)
    # re-stroke body edge so highlight doesn't cover it
    ellipse(d, 150, 150, 78, 86, None, OL, ow)

    # ---- wing (folded teardrop on the body side) ----
    wing = [px(150, 138), px(186, 168), px(168, 206), px(150, 196), px(146, 168)]
    d.polygon([c for p in wing for c in p], fill=YELLOW_DK, outline=OL,
              width=int(ow * S))
    d.line([px(164, 168)[0], px(164, 168)[1], px(158, 192)[0], px(158, 192)[1]],
           fill=OL, width=int(3 * S))

    # ---- crest (3 fanned feathers, no sticks) ----
    for ang, length in ((-30, 46), (0, 54), (30, 46)):
        rad = math.radians(ang)
        bx, by = 150, 76
        tx = bx + math.sin(rad) * length
        ty = by - math.cos(rad) * length
        d.line([px(bx, by)[0], px(bx, by)[1], px(tx, ty)[0], px(tx, ty)[1]],
               fill=OL, width=int(16 * S))
        d.line([px(bx, by)[0], px(bx, by)[1], px(tx, ty)[0], px(tx, ty)[1]],
               fill=YELLOW_DK, width=int(9 * S))

    # ---- cheek blush ----
    ellipse(d, 120, 165, 17, 12, BLUSH)

    # ---- eye ----
    ellipse(d, 138, 128, 27, 29, WHITE, OL, ow)
    ellipse(d, 144, 132, 12, 13, INK)
    ellipse(d, 148, 127, 4.5, 4.5, WHITE)

    # ---- beak (wide open, singing) ----
    # upper beak
    d.polygon([px(196, 128)[0], px(196, 128)[1], px(250, 112)[0], px(250, 112)[1],
               px(208, 150)[0], px(208, 150)[1]], fill=ORANGE, outline=OL,
              width=int(ow * S))
    # lower beak
    d.polygon([px(196, 150)[0], px(196, 150)[1], px(244, 168)[0], px(244, 168)[1],
               px(208, 150)[0], px(208, 150)[1]], fill=ORANGE_DK, outline=OL,
              width=int(ow * S))

    # ---- feet ----
    for fx in (134, 166):
        d.line([px(fx, 232)[0], px(fx, 232)[1], px(fx, 248)[0], px(fx, 248)[1]],
               fill=ORANGE_DK, width=int(7 * S))
        for a in (-12, 0, 12):
            d.line([px(fx, 248)[0], px(fx, 248)[1], px(fx + a, 256)[0],
                    px(fx + a, 256)[1]], fill=ORANGE_DK, width=int(6 * S))

    # ---- sound waves (it's making noise!) ----
    cx, cy = 250, 130
    for i, r in enumerate((28, 46, 64)):
        bb = [px(cx - r, cy - r)[0], px(cx - r, cy - r)[1],
              px(cx + r, cy + r)[0], px(cx + r, cy + r)[1]]
        d.arc(bb, start=-42, end=42, fill=INK, width=int((7 - i) * S))
    # a cheerful music note
    nx, ny = 232, 64
    d.ellipse([px(nx - 9, ny - 7)[0], px(nx - 9, ny - 7)[1],
               px(nx + 5, ny + 6)[0], px(nx + 5, ny + 6)[1]], fill=INK)
    d.line([px(nx + 4, ny + 1)[0], px(nx + 4, ny + 1)[1], px(nx + 4, ny - 30)[0],
            px(nx + 4, ny - 30)[1]], fill=INK, width=int(5 * S))
    d.line([px(nx + 4, ny - 30)[0], px(nx + 4, ny - 30)[1], px(nx + 18, ny - 24)[0],
            px(nx + 18, ny - 24)[1]], fill=INK, width=int(6 * S))


def main():
    assets = config.ASSETS_DIR
    os.makedirs(assets, exist_ok=True)

    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_bird(d)

    for size in (256, 128, 64, 48, 32):
        out = img.resize((size, size), Image.LANCZOS)
        out.save(os.path.join(assets, f"logo_{size}.png"))
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(assets, "logo.png"))
    # Windows icon (multi-size)
    img.resize((256, 256), Image.LANCZOS).save(
        os.path.join(assets, "logo.ico"),
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("logo written to", assets)


if __name__ == "__main__":
    main()
