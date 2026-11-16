"""작은 주인공(게임 키 약 22px = 도트 44px) 애니메이션 시트.

- 대기·걷기 8·채찍 4·갈고리: Kaggle에서 게임 속 주인공을 참고로 포즈 지정 생성(tools/hero-pose/poses_small.py,
  gen_small_kaggle.py)한 그림을 도트화한 것(assets/hero/gen_small/)을 그대로 씀. 땅에 닿는 프레임은 발을 y=57에 맞춤
- 점프 6: AI가 다리를 접은 자세를 그리지 못해서, 대기 프레임의 몸통(코트 아래 단까지)에
  poses_small.py의 점프 관절 좌표(엉덩이·무릎·발목)로 다리를 새로 그림 → 무릎이 실제로 꺾이며 오므렸다 펴짐
프레임 80x60, 발 기준점 (32, 57). 시트 줄: idle 4, walk 8, jump 6, grapple 1, whip 4
실행:  python tools/hero-anim/anim3.py   →  assets/hero/hero_sheet.png, hero_<동작>.png, frames.json, preview/
"""
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / 'assets' / 'hero'
GEN = HERO / 'gen_small'
FW, FH, AX, AY = 80, 60, 32, 57
HEIGHT = 44                                    # 도트 키 (to_sprite --height)

spec = importlib.util.spec_from_file_location('poses_small', ROOT / 'tools' / 'hero-pose' / 'poses_small.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
HIP_PX = AY - (1.0 - P.HIP_Y) * HEIGHT        # 서 있을 때 엉덩이 y (도트)


def load(name):
    return np.asarray(Image.open(GEN / f'{name}.png').convert('RGBA')).copy()


def shift(a, dx, dy):
    out = np.zeros_like(a)
    ys, xs = np.nonzero(a[..., 3])
    X, Y = xs + dx, ys + dy
    ok = (X >= 0) & (X < FW) & (Y >= 0) & (Y < FH)
    out[Y[ok], X[ok]] = a[ys[ok], xs[ok]]
    return out


def ground(a):
    ys = np.where(a[..., 3].any(1))[0]
    return shift(a, 0, AY - ys.max())


def over(dst, src):
    m = src[..., 3] > 0
    dst[m] = src[m]
    return dst


def glow(a, k):
    c = a[..., :3].astype(int)
    m = (a[..., 3] > 0) & (c[..., 1] > 150) & (c[..., 1] > c[..., 0] + 50)
    a[..., :3][m] = np.clip(c[m] + k, 0, 255).astype(np.uint8)
    return a


def common(a, y0, y1, pick):
    """a의 y0~y1 줄에서 pick 조건을 만족하는 가장 흔한 색."""
    px = [tuple(int(v) for v in a[y, x, :3]) for y in range(y0, y1) for x in range(FW) if a[y, x, 3] and pick(a[y, x])]
    return Counter(px).most_common(1)[0][0] if px else (60, 60, 50)


IDLE = ground(load('idle_0'))
# 코트 아래 단: 엉덩이 아래로 바지·장화만 남는 첫 줄 (넉넉하게 엉덩이+3)
HEM = int(round(HIP_PX)) + 3
BODY = IDLE.copy()
BODY[HEM:] = 0
PANTS = common(IDLE, HEM, AY - 3, lambda p: int(p[1]) >= int(p[0]))          # 초록 바지
BOOT = common(IDLE, AY - 3, AY + 1, lambda p: int(p[0]) > int(p[2]) + 20)     # 갈색 장화
OUT = (22, 24, 20, 255)


def draw_leg(cv, hip, thigh, bend, shade):
    """허벅지·정강이를 3px 굵기로, 끝에 장화. shade<1이면 먼 다리(어둡게)."""
    S = HEIGHT
    knee, ankle = P.leg_points((0, 0), thigh, bend)
    pts = [hip, (hip[0] + knee[0] * S, hip[1] + knee[1] * S), (hip[0] + ankle[0] * S, hip[1] + ankle[1] * S)]
    col = tuple(int(v * shade) for v in PANTS) + (255,)
    bcol = tuple(int(v * shade) for v in BOOT) + (255,)
    lay = np.zeros((FH, FW, 4), np.uint8)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(n + 1):
            x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    X, Y = int(round(x + dx)), int(round(y + dy))
                    if 0 <= X < FW and 0 <= Y < FH:
                        lay[Y, X] = col
    ax, ay = pts[2]
    for dx in range(-1, 4):                               # 장화: 발목에서 앞으로
        for dy in range(-1, 2):
            X, Y = int(round(ax + dx)), int(round(ay + dy))
            if 0 <= X < FW and 0 <= Y < FH:
                lay[Y, X] = bcol
    # 바깥 테두리
    a = lay[..., 3] > 0
    out = lay.copy()
    for y in range(FH):
        for x in range(FW):
            if not a[y, x] and any(0 <= y + v < FH and 0 <= x + u < FW and a[y + v, x + u]
                                   for u, v in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y, x] = OUT
    return over(cv, out)


def jump(t):
    near, far, drop, lean, _, _ = P.JUMP[t]
    dy = int(round(drop * HEIGHT))
    hip = (AX + 0.5, HIP_PX + dy)
    cv = np.zeros((FH, FW, 4), np.uint8)
    draw_leg(cv, (hip[0] - 0.5, hip[1]), *far, 0.75)       # 먼 다리 먼저
    draw_leg(cv, (hip[0] + 0.5, hip[1]), *near, 1.0)
    over(cv, shift(BODY, 0, dy))                           # 몸통(코트)이 허벅지 윗부분을 덮음
    return glow(cv, 30 if t in (2, 3) else 10)


def idle(t):
    up = IDLE.copy()
    lower = up.copy()
    up[HEM - 2:] = 0                                       # 숨쉬기: 허리 위만 1px 내려감
    lower[:HEM - 2] = 0
    cv = over(np.zeros_like(IDLE), lower)
    over(cv, shift(up, 0, 1 if t in (2, 3) else 0))
    return glow(cv, [0, 20, 40, 20][t])


def plant_tip(a):
    """화분 식물 끝: 초록이 강한 픽셀 중 가장 오른쪽 위."""
    c = a[..., :3].astype(int)
    m = (a[..., 3] > 0) & (c[..., 1] > c[..., 0] + 25) & (c[..., 1] > c[..., 2])
    ys, xs = np.nonzero(m)
    i = np.argmax(xs * 4 - ys)
    return int(xs[i]), int(ys[i])


GRAPPLE = ground(load('grapple_0'))
ANIMS = {
    'idle': (4, idle, 280, True),
    'walk': (8, lambda t: glow(ground(load(f'walk_{t}')), 15), 95, True),
    'jump': (6, jump, 100, False),
    'grapple': (1, lambda t: glow(GRAPPLE.copy(), 30), 160, False),
    'whip': (4, lambda t: glow(ground(load(f'whip_{t}')), 25), 75, False),
}


def main():
    prev_dir = HERO / 'preview'
    prev_dir.mkdir(exist_ok=True)
    tip = plant_tip(GRAPPLE)
    meta = {'frame_w': FW, 'frame_h': FH, 'anchor': [AX, AY], 'plant_tip_grapple': list(tip), 'anims': {}}
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
            gif.append(b.resize((FW * 5, FH * 5), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
        gif[0].save(prev_dir / f'hero_{name}.gif', save_all=True, append_images=gif[1:], duration=ms, loop=0)
    full = Image.new('RGBA', (max(r.width for r in rows), FH * len(rows)))
    for i, r in enumerate(rows):
        full.paste(r, (0, i * FH))
    full.save(HERO / 'hero_sheet.png')
    (HERO / 'frames.json').write_text(json.dumps(meta, indent=2))
    pv = Image.new('RGBA', full.size, (86, 80, 50, 255))
    pv.alpha_composite(full)
    pv.resize((full.width * 4, full.height * 4), Image.NEAREST).save(prev_dir / 'hero_sheet_x3.png')
    print('ok', 'tip', tip)


if __name__ == '__main__':
    main()
