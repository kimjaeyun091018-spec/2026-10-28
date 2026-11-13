"""적 애니메이션 시트 만들기. AI로 생성해 도트화한 적(assets/enemies/gen/*.png)을 부위별로 잘라 움직인다.

시트는 오른쪽을 보는 기준 (게임이 방향에 맞춰 좌우를 뒤집음). 한 줄에 한 동작.
- 덩굴 뭉치 blob  프레임 48x40, 발 기준점 (24, 38): walk 4 · attack 4 (웅크림→덤벼듦→핵이 번쩍이며 물기→회복) · hurt 1
- 꽃 포탑 flower  프레임 64x64, 뿌리 기준점 (32, 62): idle 4 (흔들림) · attack 4 (꽃잎이 부풀며 꽃심이 번쩍→씨앗 발사 반동→가라앉음) · hurt 1
실행:  python tools/enemy-gen/anim_enemies.py   →  assets/enemies/<적>.png, enemies.json, preview/*.gif
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'assets' / 'enemies' / 'gen'
OUT = ROOT / 'assets' / 'enemies'


def load(p):
    return np.asarray(Image.open(p).convert('RGBA')).copy()


def clean_bottom_shadow(a, rows=3):
    """맨 아래 몇 줄의 채도 낮은 회색(바닥 그림자 흔적)을 지움."""
    h = a.shape[0]
    c = a[..., :3].astype(int)
    sat = c.max(2) - c.min(2)
    m = np.zeros(a.shape[:2], bool)
    m[h - rows:] = True
    a[m & (sat < 16)] = 0
    return a


def place(frame, spr, x, y):
    """spr의 왼쪽 위를 (x, y)에 겹쳐 그림."""
    h, w = spr.shape[:2]
    FH, FW = frame.shape[:2]
    for yy in range(h):
        for xx in range(w):
            if spr[yy, xx, 3] and 0 <= y + yy < FH and 0 <= x + xx < FW:
                frame[y + yy, x + xx] = spr[yy, xx]
    return frame


def split(a, y_cut=None, x_cut=None):
    """a를 y_cut 위/아래 (또는 x_cut 왼/오른쪽) 두 장으로 나눔 (크기 그대로, 나머지는 투명)."""
    top, bot = a.copy(), a.copy()
    if y_cut is not None:
        top[y_cut:] = 0
        bot[:y_cut] = 0
    else:
        top[:, x_cut:] = 0
        bot[:, :x_cut] = 0
    return top, bot


def glow_red(a, k):
    """붉은 핵·입 안 픽셀을 밝게 (k 0~1)."""
    c = a[..., :3].astype(int)
    m = (a[..., 3] > 0) & (c[..., 0] > c[..., 1] + 25) & (c[..., 0] > c[..., 2] + 15)
    tgt = np.array([255, 120, 70])
    a[..., :3][m] = np.clip(c[m] + (tgt - c[m]) * k, 0, 255).astype(np.uint8)
    return a


def flash(a, k=0.75):
    m = a[..., 3] > 0
    a[..., :3][m] = (a[..., :3][m] * (1 - k) + np.array([240, 245, 225]) * k).astype(np.uint8)
    return a


def shift(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    ys, xs = np.nonzero(a[..., 3])
    X, Y = xs + dx, ys + dy
    ok = (X >= 0) & (X < w) & (Y >= 0) & (Y < h)
    out[Y[ok], X[ok]] = a[ys[ok], xs[ok]]
    return out


# ---------- 덩굴 뭉치 ----------
def blob_frames():
    spr = clean_bottom_shadow(load(SRC / 'blob.png'))
    h, w = spr.shape[:2]
    FW, FH, AX, AY = 48, 40, 24, 38
    ox, oy = AX - w // 2, AY + 1 - h            # 발이 AY에 오도록
    leg_y = int(h * 0.72)                        # 이 줄 아래가 다리
    body, legs = split(spr, y_cut=leg_y)
    leg_l, leg_r = split(legs, x_cut=w // 2)

    def fr(body_dx=0, body_dy=0, l=(0, 0), r=(0, 0), glow=0.0, hurt=False, squash=0):
        f = np.zeros((FH, FW, 4), np.uint8)
        place(f, shift(leg_l, *l), ox + body_dx, oy)
        place(f, shift(leg_r, *r), ox + body_dx, oy)
        b = shift(body, 0, body_dy + squash)
        if glow:
            b = glow_red(b, glow)
        place(f, b, ox + body_dx, oy)
        if hurt:
            f = flash(f)
        return f

    walk = [fr(body_dy=0, l=(0, -1), r=(0, 0)), fr(body_dy=-1, l=(0, 0), r=(0, 0)),
            fr(body_dy=0, l=(0, 0), r=(0, -1)), fr(body_dy=-1, l=(0, 0), r=(0, 0))]
    attack = [fr(squash=2, l=(-1, 0), r=(1, 0), glow=0.3),           # 웅크림
              fr(body_dx=4, body_dy=-3, l=(-1, -2), r=(1, -2), glow=0.6),   # 덤벼듦
              fr(body_dx=6, body_dy=-1, glow=1.0),                    # 핵이 번쩍이며 물기
              fr(body_dx=2, glow=0.4)]                                # 회복
    hurt = [fr(body_dx=-2, hurt=True)]
    return {'w': FW, 'h': FH, 'anchor': [AX, AY], 'anims': {'walk': (walk, 150, True), 'attack': (attack, 90, False), 'hurt': (hurt, 120, False)}}


# ---------- 꽃 포탑 ----------
def flower_frames():
    p = SRC / 'flower.png'
    if not p.exists():
        return None
    spr = clean_bottom_shadow(load(p))
    h, w = spr.shape[:2]
    FW, FH, AX, AY = 64, 64, 32, 62
    ox, oy = AX - w // 2, AY + 1 - h
    head_y = int(h * 0.62)                       # 이 줄 위가 꽃 머리, 아래가 줄기·뿌리혹
    head, base = split(spr, y_cut=head_y)

    def fr(sway=0, open_=0, recoil=0, glow=0.0, hurt=False):
        """open_: 꽃잎을 부풀림(가로로 open_px 넓히고 위로 들어 올림), recoil: 발사 반동으로 뒤로."""
        f = np.zeros((FH, FW, 4), np.uint8)
        place(f, base, ox, oy)
        hd = head
        if open_:
            ys, xs = np.nonzero(head[..., 3])
            x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
            crop = Image.fromarray(head[y0:y1, x0:x1], 'RGBA')
            big = np.asarray(crop.resize((crop.width + open_ * 2, crop.height + open_), Image.NEAREST)).copy()
            hd = np.zeros((h + open_, w + open_ * 2, 4), np.uint8)
            hd[y0:y0 + big.shape[0], x0:x0 + big.shape[1]] = big
            hd = shift(hd, 0, -open_)
            hd_x = ox - open_
        else:
            hd_x = ox
        hd = shift(hd, sway - recoil, 0)
        if glow:
            hd = glow_red(hd, glow)
        place(f, hd, hd_x, oy)
        if hurt:
            f = flash(f)
        return f

    idle = [fr(0), fr(1), fr(1), fr(0)]
    attack = [fr(-1, open_=1, glow=0.3), fr(-1, open_=2, glow=0.8), fr(1, open_=1, recoil=2, glow=1.0), fr(0, open_=0, glow=0.3)]
    hurt = [fr(-2, hurt=True)]
    return {'w': FW, 'h': FH, 'anchor': [AX, AY], 'anims': {'idle': (idle, 220, True), 'attack': (attack, 90, False), 'hurt': (hurt, 120, False)}}


def main():
    (OUT / 'preview').mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, fn in (('blob', blob_frames), ('flower', flower_frames)):
        d = fn()
        if d is None:
            print('skip', name)
            continue
        FW, FH = d['w'], d['h']
        rows = list(d['anims'].items())
        n = max(len(fr) for _, (fr, _, _) in rows)
        sheet = Image.new('RGBA', (FW * n, FH * len(rows)))
        info = {'frame_w': FW, 'frame_h': FH, 'anchor': d['anchor'], 'anims': {}}
        for r, (an, (frames, ms, loop)) in enumerate(rows):
            for i, f in enumerate(frames):
                sheet.paste(Image.fromarray(f, 'RGBA'), (i * FW, r * FH))
            info['anims'][an] = {'row': r, 'frames': len(frames), 'ms': ms, 'loop': loop}
            gif = []
            for f in frames:
                b = Image.new('RGBA', (FW, FH), (86, 80, 50, 255))
                b.alpha_composite(Image.fromarray(f, 'RGBA'))
                gif.append(b.resize((FW * 5, FH * 5), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
            gif[0].save(OUT / 'preview' / f'{name}_{an}.gif', save_all=True, append_images=gif[1:], duration=ms, loop=0)
        sheet.save(OUT / f'{name}.png')
        meta[name] = info
        pv = Image.new('RGBA', sheet.size, (86, 80, 50, 255))
        pv.alpha_composite(sheet)
        pv.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(OUT / 'preview' / f'{name}_sheet_x4.png')
        print('ok', name)
    (OUT / 'enemies.json').write_text(json.dumps(meta, indent=1))


if __name__ == '__main__':
    main()
