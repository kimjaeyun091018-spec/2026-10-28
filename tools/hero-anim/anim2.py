"""주인공 애니메이션 2판: AI로 생성한 옆모습 걷기 8프레임을 바탕으로 모든 동작을 만든다.

- 걷기: assets/hero/gen/walk_0~7.png (Kaggle, 포즈 지정 생성 → tools/hero-pose/to_sprite.py로 도트화)
        를 발바닥이 y=77에 오도록 맞춰 그대로 씀
- 대기·점프·갈고리·채찍: 걷기 2번(통과 자세)을 몸통으로 삼아 장화·코트 자락·화분 팔을 잘라 움직임
  점프는 장화를 코트 밑으로 접어 올리고 자락을 펄럭여 다리를 오므리는 모습으로 표현
프레임 96x80, 발 기준점 (43, 77). 시트 줄 순서: idle, walk, jump, grapple, whip
실행:  python tools/hero-anim/anim2.py
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import anim as v1   # 덩굴·파리지옥 그리기 함수 재사용

ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / 'assets' / 'hero'
FW, FH = 96, 80
GROUND = 77
TIP = (62, 14)          # 화분 식물 끝 (덩굴이 나오는 곳)


def load(p):
    return np.asarray(Image.open(p).convert('RGBA')).copy()


def ground(a):
    """가장 낮은 불투명 픽셀이 GROUND에 오도록 위아래로 옮김."""
    ys = np.where(a[..., 3].any(1))[0]
    return shift(a, 0, GROUND - ys.max())


def shift(a, dx, dy):
    out = np.zeros_like(a)
    ys, xs = np.nonzero(a[..., 3])
    X, Y = xs + dx, ys + dy
    ok = (X >= 0) & (X < FW) & (Y >= 0) & (Y < FH)
    out[Y[ok], X[ok]] = a[ys[ok], xs[ok]]
    return out


def cut(a, x0, y0, x1, y1):
    part = np.zeros_like(a)
    part[y0:y1 + 1, x0:x1 + 1] = a[y0:y1 + 1, x0:x1 + 1]
    rest = a.copy()
    rest[y0:y1 + 1, x0:x1 + 1][part[y0:y1 + 1, x0:x1 + 1, 3] > 0] = 0
    return part, rest


def over(dst, src):
    m = src[..., 3] > 0
    dst[m] = src[m]
    return dst


def glow(a, k):
    px = a[..., :3].astype(int)
    m = (a[..., 3] > 0) & (px[..., 1] > 150) & (px[..., 1] > px[..., 0] + 50)
    a[..., :3][m] = np.clip(px[m] + k, 0, 255).astype(np.uint8)
    return a


WALK = [ground(load(HERO / 'gen' / f'walk_{i}.png')) for i in range(8)]
BASE = WALK[2]
BOOT_B, rest = cut(BASE, 27, 63, 37, 79)        # 뒷발 장화
BOOT_F, rest = cut(rest, 38, 65, 52, 79)        # 앞발 장화
HEM, rest = cut(rest, 29, 55, 53, 66)           # 코트 자락
ARM, BODY = cut(rest, 48, 8, 71, 37)            # 화분을 든 팔과 식물
STAND_B = (3, 2)                                # 대기: 들린 뒷발을 바닥에 내려 앞발 옆에 둠


def figure(body_dy=0, b=(0, 0), f=(0, 0), hem=(0, 0), arm=(0, 0), glow_k=15, tuck=False):
    """부위를 옮겨 한 프레임 조립. 평소엔 장화를 코트 뒤에, 다리를 접은 공중 프레임(tuck)은
    접힌 다리가 보이도록 장화를 코트 자락 앞에 그림."""
    cv = np.zeros((FH, FW, 4), np.uint8)
    boots = [shift(BOOT_B, STAND_B[0] + b[0], STAND_B[1] + b[1]), shift(BOOT_F, f[0], f[1])]
    if not tuck:
        for x in boots:
            over(cv, x)
    over(cv, shift(BODY, 0, body_dy))
    over(cv, shift(HEM, hem[0], body_dy + hem[1]))
    if tuck:
        for x in boots:
            over(cv, x)
    over(cv, shift(ARM, arm[0], body_dy + arm[1]))
    return glow(cv, glow_k)


def idle(t):
    bob = [0, 0, 1, 1][t]
    return figure(bob, hem=(0, 0), arm=(0, 1 if t == 3 else 0), glow_k=[0, 20, 40, 20][t])


JUMP = [  # 몸 dy, 뒷발, 앞발, 코트 자락, 화분 팔
    (3, (-2, 0), (1, 0), (0, 0), (0, 1)),          # 0 준비: 웅크림 (몸이 내려와 장화 위로 겹침)
    (-2, (-3, 1), (0, 0), (0, 0), (0, -2)),        # 1 도약: 몸을 펴고 뒷발로 박참
    (0, (4, -7), (3, -6), (-2, 0), (0, -2)),       # 2 상승: 무릎을 앞으로 끌어올리며 장화를 접어 올림, 자락은 뒤로
    (0, (6, -11), (4, -10), (-3, 0), (0, -1)),     # 3 정점: 가장 많이 오므림 (장화가 엉덩이 쪽까지)
    (0, (0, -4), (3, -2), (-2, -3), (0, -2)),      # 4 하강: 다리를 아래로 펴며 자락이 위로 날림
    (4, (-3, 0), (2, 0), (0, 0), (0, 2)),          # 5 착지: 깊게 웅크림
]


def jump(t):
    dy, b, f, hem, arm = JUMP[t]
    return figure(dy, b, f, hem, arm, glow_k=30 if t in (2, 3) else 10, tuck=t in (2, 3, 4))


def vine_layer(cv, pts, jaw):
    """v1.vine은 v1 프레임(96x80) 위에 그림. 같은 크기라 그대로 씀."""
    v1.vine(cv, pts, jaw_open=jaw)
    return cv


GRAPPLE = [(0.00, None, -1), (0.35, 0.8, -3), (0.75, 1.0, -3), (1.00, 0.9, -3), (1.00, 0.0, -3), (0.45, 0.0, -2)]
GRAPPLE_END = (FW - 6, 2)


def grapple(t):
    k, op, up = GRAPPLE[t]
    cv = figure(0, b=(-1, 0), f=(1, 0), arm=(0, up), glow_k=40 if t in (2, 3) else 15)
    sx, sy = TIP[0], TIP[1] + up
    if k > 0:
        ex, ey = sx + (GRAPPLE_END[0] - sx) * k, sy + (GRAPPLE_END[1] - sy) * k
        sag = 3 if t in (1, 5) else 1
        vine_layer(cv, v1.bezier((sx, sy), ((sx + ex) / 2, (sy + ey) / 2 + sag), (ex, ey), 30), op)
        over(cv, shift(ARM, 0, up))                      # 화분이 덩굴 시작점을 덮도록
    else:
        vine_layer(cv, [(sx, sy), (sx + 1, sy - 3), (sx - 1, sy - 6)], 0.2)
    return cv


WHIP = [(-120, 10), (-75, 16), (-20, 30), (25, 30), (60, 16)]


def whip(t):
    ang, ln = WHIP[t]
    lean = [-1, 0, 1, 1, 0][t]
    cv = figure(0, b=(-1 + lean, 0), f=(1 + lean, 0), arm=(lean, -2 if t < 3 else 0), glow_k=35 if t in (2, 3) else 10)
    sx, sy = TIP[0] + lean, TIP[1] + (-2 if t < 3 else 0)
    a = math.radians(ang)
    prev = math.radians(WHIP[t - 1][0]) if t else a
    ex, ey = sx + ln * math.cos(a), sy + ln * math.sin(a)
    cx, cy = sx + ln * 0.6 * math.cos((a + prev) / 2), sy + ln * 0.6 * math.sin((a + prev) / 2)
    if t in (2, 3):
        for s in range(6):
            bb = prev + (a - prev) * s / 6
            v1.dot(cv, sx + ln * 0.95 * math.cos(bb), sy + ln * 0.95 * math.sin(bb), (200, 240, 150, 255))
    vine_layer(cv, v1.bezier((sx, sy), (cx, cy), (ex, ey), 30), 0.5 if t in (2, 3) else 0.1)
    return cv


ANIMS = {
    'idle': (4, idle, 280, True),
    'walk': (8, lambda t: glow(WALK[t].copy(), 15), 95, True),
    'jump': (6, jump, 100, False),
    'grapple': (6, grapple, 80, False),
    'whip': (5, whip, 70, False),
}


def main():
    prev_dir = HERO / 'preview'
    prev_dir.mkdir(exist_ok=True)
    meta = {'frame_w': FW, 'frame_h': FH, 'anchor': [43, GROUND], 'plant_tip': list(TIP), 'anims': {}}
    rows = []
    for name, (n, fn, ms, loop) in ANIMS.items():
        frames = [Image.fromarray(fn(t), 'RGBA') for t in range(n)]
        sheet = Image.new('RGBA', (FW * n, FH))
        for i, f in enumerate(frames):
            sheet.paste(f, (i * FW, 0))
        sheet.save(HERO / f'hero_{name}.png')
        rows.append(sheet)
        meta['anims'][name] = {'row': len(rows) - 1, 'frames': n, 'ms': ms, 'loop': loop}
        gif = []
        for f in frames:
            b = Image.new('RGBA', (FW, FH), (86, 80, 50, 255))
            b.alpha_composite(f)
            gif.append(b.resize((FW * 4, FH * 4), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
        gif[0].save(prev_dir / f'hero_{name}.gif', save_all=True, append_images=gif[1:], duration=ms, loop=0)
    full = Image.new('RGBA', (max(r.width for r in rows), FH * len(rows)))
    for i, r in enumerate(rows):
        full.paste(r, (0, i * FH))
    full.save(HERO / 'hero_sheet.png')
    (HERO / 'frames.json').write_text(json.dumps(meta, indent=2))
    pv = Image.new('RGBA', full.size, (86, 80, 50, 255))
    pv.alpha_composite(full)
    pv.resize((full.width * 3, full.height * 3), Image.NEAREST).save(prev_dir / 'hero_sheet_x3.png')


if __name__ == '__main__':
    main()
