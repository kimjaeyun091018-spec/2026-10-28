"""세계 도트(타일·탄환·체크포인트·목표)와 1구역 배경을 주인공과 같은 해상도(게임 1px = 도트 2px)로 만든다.

실행:  python tools/art/make_world.py
결과:  assets/world/tiles.png   구역(줄)마다 32x32 칸 8개:
                                 0~2 드러난 돌 블록(변형 3개), 3 안쪽 블록, 4 이끼 윗면(32x16, 칸 위쪽),
                                 5~6 늘어진 덩굴(변형 2개), 7 가시덤불
       assets/world/fx.png      적 씨앗탄 4프레임(16x16) · 주인공 씨앗(날아감·싹·깜빡) · 체크포인트(꺼짐·켜짐 24x32) ·
                                 세계수 씨앗 2프레임(32x32)  — 좌표는 assets/world/world.json
       assets/ch{1,2,3}-bg-2x.png  구역 배경 원본(ch*-bg-original.png)을 852x480(2배)으로 줄이고 주인공 색감(탁한 올리브)에 맞춰 채도·밝기 조정
"""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets' / 'world'
ZONES = [  # index.html의 ZONES와 같은 색 (기본, 안쪽, 이끼)
    ('#4b5049', '#1d2431', '#6aa13c'),
    ('#303c3f', '#192124', '#5d9a4a'),
    ('#3f3236', '#21191c', '#6f8f3e'),
    ('#2e3a47', '#171e26', '#4f9a6a'),
]
OUTLINE = (20, 22, 20, 255)


def hx(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def tone(rgb, dl=0.0, ds=0.0):
    h, l, s = colorsys.rgb_to_hls(*[v / 255 for v in rgb])
    l = min(1, max(0, l + dl))
    s = min(1, max(0, s + ds))
    return tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, l, s)) + (255,)


def rnd(x, y, k=0):
    n = (x * 374761393 + y * 668265263 + k * 2147483647) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return ((n ^ (n >> 16)) & 0xffffffff) / 4294967296


def blank(w, h):
    return np.zeros((h, w, 4), np.uint8)


def stone(base, var, inner=False):
    """두 줄 벽돌 돌 블록 32x32. 줄눈은 어둡게, 벽돌마다 밝기 조금씩 다르게, 윗/왼쪽 밝고 아래/오른쪽 어둡게."""
    t = blank(32, 32)
    b = hx(base)
    for y in range(32):
        row = y // 16
        off = (8 + var * 5) % 16 if row else (var * 3) % 16
        for x in range(32):
            bx = (x + off) % 16
            brick = (x + off) // 16 + row * 7 + var * 13
            if y % 16 == 15 or bx == 15:
                t[y, x] = tone(b, -0.10)                     # 줄눈
                continue
            sh = (rnd(brick, row, var) - 0.5) * 0.06
            c = tone(b, sh)
            if y % 16 == 0 or bx == 0:
                c = tone(b, sh + 0.06)                       # 밝은 모서리
            elif y % 16 == 14 or bx == 14:
                c = tone(b, sh - 0.05)                       # 그림자 모서리
            elif rnd(x, y, var + 5) < 0.06:
                c = tone(b, sh - 0.07)                       # 점 무늬
            t[y, x] = c
    if not inner and var == 1:                               # 금 간 블록
        x = 9
        for y in range(3, 14):
            t[y, x] = tone(b, -0.16)
            x += 1 if rnd(x, y, 9) < 0.35 else 0
    if inner:
        t[..., :3] = (t[..., :3].astype(int) * 0.55).astype(np.uint8)
    return t


def moss_top(top):
    """윗면 이끼 32x16 (칸 위 6px 위로 풀잎이 솟고, 아래는 고르지 않게 덮임)."""
    t = blank(32, 16)
    m = hx(top)
    for x in range(32):
        depth = 4 + int(rnd(x // 3, 1) * 4)
        for y in range(6, 6 + depth):
            c = tone(m, 0.06 if y == 6 else (-0.10 if y == 5 + depth else 0) - 0.02 * (y - 6), -0.15)
            t[y, x] = c
        if rnd(x, 7) < 0.45:                                 # 풀잎
            hgt = 1 + int(rnd(x, 8) * 5)
            for y in range(6 - hgt, 6):
                t[y, x] = tone(m, 0.10, -0.10)
        if rnd(x, 9) < 0.08:                                 # 작은 꽃
            t[5, x] = (226, 214, 150, 255)
    return t


def vines(top, var):
    """칸 아래로 늘어진 덩굴 32x32 (줄기 2~3개, 잎)."""
    t = blank(32, 32)
    m = hx(top)
    n = 2 + var
    for k in range(n):
        x = 4 + int(rnd(k, var, 3) * 24)
        ln = 10 + int(rnd(k, var, 4) * 20)
        for y in range(ln):
            xx = x + int(round(np.sin(y * 0.35 + k) * 1.2))
            t[y, xx] = tone(m, -0.12, -0.2)
            if y % 5 == 2:
                for dx in (-2, -1) if (y // 5) % 2 else (1, 2):
                    if 0 <= xx + dx < 32:
                        t[y, xx + dx] = tone(m, 0.0 if abs(dx) == 1 else -0.06, -0.15)
    return t


def thorns():
    """가시덤불 32x32: 아래에서 솟는 갈색·검붉은 가시."""
    t = blank(32, 32)
    for k in range(7):
        x0 = 2 + k * 4 + int(rnd(k, 1) * 3)
        h = 12 + int(rnd(k, 2) * 14)
        for i in range(h):
            y = 31 - i
            w = max(0, int((1 - i / h) * 3))
            for dx in range(-w, w + 1):
                x = x0 + dx + (i // 6) * (1 if k % 2 else -1)
                if 0 <= x < 32:
                    c = (110, 52, 40, 255) if i > h * 0.6 else (78, 40, 32, 255)
                    if dx == -w:
                        c = (150, 82, 58, 255)
                    t[y, x] = c
        tip = (x0 + (h // 6) * (1 if k % 2 else -1), 31 - h)
        if 0 <= tip[0] < 32:
            t[max(0, tip[1]), tip[0]] = (226, 200, 160, 255)
    for x in range(32):                                      # 덤불 밑동
        for y in range(28, 32):
            if rnd(x, y, 3) < 0.7:
                t[y, x] = (52, 40, 30, 255) if rnd(x, y) < 0.5 else (70, 52, 36, 255)
    return t


def outline(t):
    """불투명 영역 바깥 1px에 진한 테두리."""
    a = t[..., 3] > 0
    out = t.copy()
    h, w = a.shape
    for y in range(h):
        for x in range(w):
            if not a[y, x] and any(0 <= y + dy < h and 0 <= x + dx < w and a[y + dy, x + dx]
                                   for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y, x] = OUTLINE
    return out


def disk(t, cx, cy, r, c):
    h, w = t.shape[:2]
    for y in range(h):
        for x in range(w):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                t[y, x] = c


def seed_bullet(f):
    """적 씨앗탄 16x16: 둥근 씨앗이 돌며 검붉은 빛."""
    t = blank(16, 16)
    glow = (200, 70, 60, 120 if f % 2 else 80)
    disk(t, 7.5, 7.5, 6.5, glow)
    ang = f * np.pi / 4
    for y in range(16):
        for x in range(16):
            u = (x - 7.5) * np.cos(ang) + (y - 7.5) * np.sin(ang)
            v = -(x - 7.5) * np.sin(ang) + (y - 7.5) * np.cos(ang)
            if (u / 4.2) ** 2 + (v / 3) ** 2 <= 1:
                t[y, x] = (226, 196, 120, 255) if u < -1 and v < 0 else (176, 128, 70, 255)
                if (u / 4.2) ** 2 + (v / 3) ** 2 > 0.6:
                    t[y, x] = (110, 70, 40, 255)
    t[7:9, 7:9] = (90, 30, 30, 255)
    return t


def hero_seed(kind):
    """주인공 씨앗 12x12: 0 날아감, 1 박혀서 싹 틈, 2 사라지기 전 깜빡."""
    t = blank(12, 12)
    for y in range(12):
        for x in range(12):
            if ((x - 6) / 3.2) ** 2 + ((y - 7) / 3.6) ** 2 <= 1:
                t[y, x] = (168, 124, 72, 255) if x < 6 else (130, 92, 54, 255)
    t[4, 5:7] = (90, 64, 40, 255)
    if kind >= 1:
        t[1:4, 6] = (110, 170, 70, 255)
        t[1, 7:9] = (160, 220, 100, 255)
        t[2, 4:6] = (130, 200, 90, 255)
    if kind == 2:
        a = t[..., 3] > 0
        t[a] = (233, 215, 138, 255)
    return outline(t)


def checkpoint(on):
    """새싹 체크포인트 24x32."""
    t = blank(24, 32)
    stem = (121, 184, 93, 255) if on else (63, 107, 64, 255)
    leaf = (159, 210, 122, 255) if on else (70, 110, 70, 255)
    for y in range(12, 31):
        t[y, 11:13] = stem
    for i in range(6):
        t[12 - i // 2, 5 + i] = leaf
        t[13 - i // 2, 5 + i] = leaf
        t[10 - i // 2, 13 + i] = leaf
        t[11 - i // 2, 13 + i] = leaf
    t[29:32, 6:18] = (70, 56, 40, 255)
    if on:
        t[6:9, 10:14] = (233, 215, 138, 255)
    return outline(t)


def goal(f):
    """세계수 씨앗 32x32: 금빛 씨앗과 새싹, 빛이 맥박처럼."""
    t = blank(32, 32)
    r = 13 if f else 11
    for y in range(32):
        for x in range(32):
            d = ((x - 16) ** 2 + (y - 17) ** 2) ** 0.5
            if d <= r and (x + y) % 2 == 0:
                t[y, x] = (233, 215, 138, 70)
    for y in range(32):
        for x in range(32):
            if ((x - 16) / 6) ** 2 + ((y - 19) / 7.5) ** 2 <= 1:
                t[y, x] = (196, 150, 80, 255) if x < 16 else (160, 116, 60, 255)
                if x < 13 and y < 18:
                    t[y, x] = (233, 200, 130, 255)
    for y in range(5, 12):
        t[y, 16] = (121, 184, 93, 255)
    t[5, 17:21] = (159, 210, 122, 255)
    t[6, 17:20] = (159, 210, 122, 255)
    t[7, 12:16] = (140, 200, 110, 255)
    return t


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tiles = Image.new('RGBA', (32 * 8, 32 * len(ZONES)))
    for z, (base, deep, top) in enumerate(ZONES):
        cells = [stone(base, 0), stone(base, 1), stone(base, 2), stone(base, 0, inner=True)]
        mt = moss_top(top)
        mt_cell = blank(32, 32)
        mt_cell[:16] = mt
        cells += [mt_cell, vines(top, 0), vines(top, 1), outline(thorns())]
        for i, c in enumerate(cells):
            tiles.paste(Image.fromarray(c, 'RGBA'), (i * 32, z * 32))
    tiles.save(OUT / 'tiles.png')

    fx = Image.new('RGBA', (128, 64))
    layout = {}
    for f in range(4):
        fx.paste(Image.fromarray(seed_bullet(f), 'RGBA'), (f * 16, 0))
    layout['enemySeed'] = {'x': 0, 'y': 0, 'w': 16, 'h': 16, 'frames': 4}
    for k in range(3):
        fx.paste(Image.fromarray(hero_seed(k), 'RGBA'), (64 + k * 12, 0))
    layout['heroSeed'] = {'x': 64, 'y': 0, 'w': 12, 'h': 12, 'frames': 3}
    for k in range(2):
        fx.paste(Image.fromarray(checkpoint(k), 'RGBA'), (k * 24, 16))
    layout['checkpoint'] = {'x': 0, 'y': 16, 'w': 24, 'h': 32, 'frames': 2}
    for k in range(2):
        fx.paste(Image.fromarray(goal(k), 'RGBA'), (48 + k * 32, 16))
    layout['goal'] = {'x': 48, 'y': 16, 'w': 32, 'h': 32, 'frames': 2}
    fx.save(OUT / 'fx.png')
    (OUT / 'world.json').write_text(json.dumps({'tiles': {'cell': 32, 'cols': ['stone0', 'stone1', 'stone2', 'inner', 'mossTop', 'vine0', 'vine1', 'thorns']},
                                                 'fx': layout}, indent=1))

    for ch in (1, 2, 3):                                     # 구역 배경 원본 → 2배 해상도 + 같은 색감 조정
        src = Image.open(ROOT / 'assets' / f'ch{ch}-bg-original.png').convert('RGB').resize((852, 480), Image.BOX)
        src = ImageEnhance.Color(src).enhance(0.72)
        src = Image.blend(src, Image.new('RGB', src.size, (70, 72, 52)), 0.12)
        src = ImageEnhance.Brightness(src).enhance(0.86)
        src.save(ROOT / 'assets' / f'ch{ch}-bg-2x.png')
    print('ok')


if __name__ == '__main__':
    main()
