"""선택된 주인공(화분을 든 방독면 사냥꾼) 컷아웃 애니메이션.

assets/hero/hero-base.png(원본 픽셀 격자 41x62)를 부위별로 잘라 움직인다. 디자인은 원본 그대로 유지.
동작: idle 4, walk 6, jump 6, grapple 6 (화분 식물이 덩굴 갈고리 발사), whip 5 (덩굴 채찍)
프레임: 96x80, 발 기준점 (FX, FY)
실행:  python tools/hero-anim/anim.py  →  assets/hero/ 에 동작별 시트 PNG, 미리보기 GIF, frames.json
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = Path(__file__).resolve().parent.parent.parent / 'assets' / 'hero'
ROOT = HERE.parent.parent
SRC = np.asarray(Image.open(ROOT / 'assets' / 'hero' / 'hero-base.png').convert('RGBA')).copy()
SH, SW = SRC.shape[:2]          # 62, 41
FW, FH = 96, 80
OX, OY = 20, 16                 # 프레임 안에서 원본 좌상단 위치
FX, FY = OX + 23, OY + 61       # 발 기준점 (두 발 사이 바닥)


def region(x0, y0, x1, y1, cond=None):
    """원본에서 사각형 부위만 남긴 레이어."""
    lay = np.zeros_like(SRC)
    ys, xs = np.mgrid[0:SH, 0:SW]
    m = (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)
    if cond is not None:
        m &= cond(xs, ys)
    lay[m] = SRC[m]
    return lay


# 부위 나누기 (좌표는 원본 41x62 기준)
LEG_L = region(13, 47, 21, 61)
LEG_R = region(22, 47, 34, 61)
BASKET = region(0, 31, 13, 55)
POT_ARM = region(27, 4, 40, 31, lambda x, y: ~((x <= 30) & (y >= 22)))
taken = (LEG_L[..., 3] > 0) | (LEG_R[..., 3] > 0) | (BASKET[..., 3] > 0) | (POT_ARM[..., 3] > 0)
BODY = SRC.copy()
BODY[taken] = 0
HEAD = region(13, 0, 30, 16)
HEAD = np.where((POT_ARM[..., 3] > 0)[..., None], 0, HEAD)
BODY_NOHEAD = BODY.copy()
BODY_NOHEAD[HEAD[..., 3] > 0] = 0

PLANT_TIP = (35, 8)             # 덩굴이 나오는 화분 식물 위치 (원본 좌표)

# 덩굴 색 (원본 그림의 녹색에서 뽑음)
V_OUT = (22, 30, 20, 255)
V_DARK = (40, 70, 34, 255)
V_MID = (74, 118, 44, 255)
V_GLOW = (128, 236, 70, 255)
J_IN = (150, 44, 52, 255)
J_DARK = (96, 28, 36, 255)
TOOTH = (226, 214, 168, 255)


def canvas():
    return np.zeros((FH, FW, 4), np.uint8)


def paste(cv, lay, dx=0, dy=0):
    ys, xs = np.nonzero(lay[..., 3])
    X, Y = xs + OX + dx, ys + OY + dy
    ok = (X >= 0) & (X < FW) & (Y >= 0) & (Y < FH)
    cv[Y[ok], X[ok]] = lay[ys[ok], xs[ok]]


def glow_pulse(cv, k):
    """방독면 렌즈·가슴 무늬 같은 밝은 연두/청록 픽셀을 k만큼 밝게."""
    px = cv[..., :3].astype(int)
    m = (cv[..., 3] > 0) & (px[..., 1] > 150) & (px[..., 1] > px[..., 0] + 60)
    cv[..., :3][m] = np.clip(px[m] + k, 0, 255).astype(np.uint8)


def dot(cv, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < FW and 0 <= y < FH:
        cv[y, x] = c


def disk(cv, x, y, r, c):
    for yy in range(int(y - r - 1), int(y + r + 2)):
        for xx in range(int(x - r - 1), int(x + r + 2)):
            if (xx - x) ** 2 + (yy - y) ** 2 <= r * r:
                dot(cv, xx, yy, c)


def curve(pts, step=0.4):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    return out + [pts[-1]]


def bezier(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


def vine(cv, pts, jaw_open=None, thick=1.3):
    path = curve(pts)
    for x, y in path:
        disk(cv, x, y, thick + 1, V_OUT)
    for i, (x, y) in enumerate(path):
        disk(cv, x, y, thick, V_DARK if i % 7 < 3 else V_MID)
    for i, (x, y) in enumerate(path):
        if (i // 3) % 3 != 2:
            dot(cv, x, y - 0.5, V_GLOW)
    if jaw_open is None:
        return
    ex, ey = path[-1]
    px, py = path[max(0, len(path) - 6)]
    ang = math.atan2(ey - py, ex - px)
    ca, sa = math.cos(ang), math.sin(ang)
    o = 1 + jaw_open * 3

    def P(u, v):                              # 덩굴 방향 기준 좌표 → 화면
        return ex + u * ca - v * sa, ey + u * sa + v * ca
    for u in range(0, 7):
        for v in range(-int(o) - 2, int(o) + 3):
            lobe = abs(abs(v) - o) <= 1.2 and u <= 6 - (abs(v) > o) * 1
            inner = abs(v) < o - 0.5 and u <= 4
            if lobe:
                dot(cv, *P(u, v), V_OUT if abs(v) > o + 0.4 else V_MID)
            elif inner:
                dot(cv, *P(u, v), J_IN if u > 1 else J_DARK)
    for u in (1, 3, 5):                       # 이빨
        dot(cv, *P(u, -o + 0.6), TOOTH)
        dot(cv, *P(u, o - 0.6), TOOTH)
    dot(cv, *P(7, -o - 0.5), TOOTH)
    dot(cv, *P(7, o + 0.5), TOOTH)


def speed_lines(cv, pts, c=(200, 230, 150, 140)):
    for x, y in curve(pts, 1.6):
        dot(cv, x, y, c)


def tip():
    return PLANT_TIP[0] + OX, PLANT_TIP[1] + OY


# ---------- 동작 ----------
def f_idle(t):
    cv = canvas()
    bob = [0, 0, 1, 1][t]
    paste(cv, LEG_L); paste(cv, LEG_R)
    paste(cv, BODY_NOHEAD, 0, bob)
    paste(cv, HEAD, 0, bob)
    paste(cv, BASKET, 0, bob)
    paste(cv, POT_ARM, 0, bob + (1 if t == 3 else 0))
    glow_pulse(cv, [0, 20, 40, 20][t])
    return cv


def f_walk(t, n=6):
    cv = canvas()
    p = t / n * 2 * math.pi
    bob = 1 if t in (1, 4) else 0
    lx, rx = round(2 * math.cos(p)), round(-2 * math.cos(p))
    ll, rl = (1 if math.sin(p) > 0.3 else 0), (1 if math.sin(p) < -0.3 else 0)
    paste(cv, LEG_L, lx, -ll)
    paste(cv, LEG_R, rx, -rl)
    paste(cv, BODY_NOHEAD, 0, bob)
    paste(cv, HEAD, 1 if t in (2, 5) else 0, bob)
    paste(cv, BASKET, round(-1.5 * math.cos(p)), bob)
    paste(cv, POT_ARM, round(1 * math.cos(p)), bob)
    glow_pulse(cv, 20)
    return cv


JUMP = [  # (몸 dy, 다리 dy, 다리 벌림, 바구니 dy, 화분 dy)
    (2, 0, 1, 2, 2),      # 웅크림
    (-2, 0, 0, -1, -3),   # 도약
    (-3, -4, -1, 1, -3),  # 상승 (다리 접음)
    (-3, -3, -1, 0, -2),  # 정점
    (-2, -1, 1, -2, -1),  # 하강 (다리 뻗음, 바구니 들림)
    (2, 0, 1, 2, 2),      # 착지
]


def f_jump(t):
    cv = canvas()
    by, ly, sp, bk, pt = JUMP[t]
    paste(cv, LEG_L, -sp, ly)
    paste(cv, LEG_R, sp, ly)
    paste(cv, BODY_NOHEAD, 0, by)
    paste(cv, HEAD, 0, by)
    paste(cv, BASKET, -1 if t == 4 else 0, by + bk)
    paste(cv, POT_ARM, 0, by + pt)
    glow_pulse(cv, 30 if t in (2, 3) else 10)
    return cv


GRAPPLE = [  # (덩굴 끝 위치 비율 0~1, 입 벌림, 몸 dx, 화분 들기)
    (0.00, None, -1, -1),
    (0.35, 0.8, 0, -3),
    (0.75, 1.0, 1, -3),
    (1.00, 0.9, 1, -3),
    (1.00, 0.0, 1, -3),
    (0.45, 0.0, 0, -2),
]
GRAPPLE_END = (FW - 6, 4)


def f_grapple(t):
    cv = canvas()
    k, op, bx, up = GRAPPLE[t]
    paste(cv, LEG_L, -1); paste(cv, LEG_R, 1)
    paste(cv, BODY_NOHEAD, bx, 0)
    paste(cv, HEAD, bx, 0)
    paste(cv, BASKET, bx - 1, 0)
    sx, sy = tip()
    sx, sy = sx + bx, sy + up
    if k > 0:
        ex = sx + (GRAPPLE_END[0] - sx) * k
        ey = sy + (GRAPPLE_END[1] - sy) * k
        sag = 3 if t in (1, 5) else 1
        pts = bezier((sx, sy), ((sx + ex) / 2, (sy + ey) / 2 + sag), (ex, ey), 30)
        if t in (1, 2):
            speed_lines(cv, [(sx - 4, sy + 6), (ex - 6, ey + 6)])
        vine(cv, pts, jaw_open=op)
    paste(cv, POT_ARM, bx, up)
    if k == 0:
        vine(cv, [(sx, sy), (sx + 1, sy - 3), (sx - 1, sy - 6)], jaw_open=0.2, thick=1.0)
    glow_pulse(cv, 40 if t in (2, 3) else 15)
    return cv


WHIP = [  # 덩굴 끝 각도(도, 0=오른쪽, -90=위), 길이
    (-120, 10), (-75, 18), (-20, 40), (25, 38), (60, 18),
]


def f_whip(t):
    cv = canvas()
    ang, ln = WHIP[t]
    lean = [-1, 0, 1, 1, 0][t]
    paste(cv, LEG_L, -1); paste(cv, LEG_R, 1)
    paste(cv, BODY_NOHEAD, lean, 0)
    paste(cv, HEAD, lean + (1 if t in (2, 3) else 0), 0)
    paste(cv, BASKET, lean - 1, 0)
    sx, sy = tip()
    sx += lean
    a = math.radians(ang)
    ex, ey = sx + ln * math.cos(a), sy + ln * math.sin(a)
    prev = math.radians(WHIP[t - 1][0]) if t else a
    # 채찍은 끝이 늦게 따라오도록 휘게
    cx = sx + ln * 0.6 * math.cos((a + prev) / 2)
    cy = sy + ln * 0.6 * math.sin((a + prev) / 2)
    if t in (2, 3):                           # 휘두른 궤적
        for s in range(6):
            b = prev + (a - prev) * s / 6
            dot(cv, sx + ln * 0.95 * math.cos(b), sy + ln * 0.95 * math.sin(b), (200, 240, 150, 255))
    vine(cv, bezier((sx, sy), (cx, cy), (ex, ey), 30), jaw_open=0.5 if t in (2, 3) else 0.1)
    paste(cv, POT_ARM, lean, -2 if t < 3 else 0)
    glow_pulse(cv, 35 if t in (2, 3) else 10)
    return cv


ANIMS = {
    'idle': (4, f_idle, 280, True),
    'walk': (6, f_walk, 110, True),
    'jump': (6, f_jump, 100, False),
    'grapple': (6, f_grapple, 80, False),
    'whip': (5, f_whip, 70, False),
}


def main():
    (OUT / 'preview').mkdir(parents=True, exist_ok=True)
    meta, rows = {'frame_w': FW, 'frame_h': FH, 'anchor': [FX, FY], 'anims': {}}, []
    for name, (n, fn, ms, loop) in ANIMS.items():
        frames = [Image.fromarray(fn(t), 'RGBA') for t in range(n)]
        sheet = Image.new('RGBA', (FW * n, FH))
        for i, f in enumerate(frames):
            sheet.paste(f, (i * FW, 0))
        sheet.save(OUT / f'hero_{name}.png')
        rows.append((name, sheet))
        meta['anims'][name] = {'row': len(rows) - 1, 'frames': n, 'ms': ms, 'loop': loop}
        prev = []
        for f in frames:
            b = Image.new('RGBA', (FW, FH), (86, 80, 50, 255))
            b.alpha_composite(f)
            prev.append(b.resize((FW * 4, FH * 4), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
        prev[0].save(OUT / 'preview' / f'hero_{name}.gif', save_all=True, append_images=prev[1:], duration=ms, loop=0)
    full = Image.new('RGBA', (max(s.width for _, s in rows), FH * len(rows)))
    for i, (_, s) in enumerate(rows):
        full.paste(s, (0, i * FH))
    full.save(OUT / 'hero_sheet.png')
    (OUT / 'frames.json').write_text(json.dumps(meta, indent=2))
    pv = Image.new('RGBA', full.size, (86, 80, 50, 255))
    pv.alpha_composite(full)
    pv.resize((full.width * 3, full.height * 3), Image.NEAREST).save(OUT / 'preview' / 'hero_sheet_x3.png')


if __name__ == '__main__':
    main()
