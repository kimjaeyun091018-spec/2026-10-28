"""Kaggle에서 만든 얼음 바다 그림을 받아 게임용 도트로 바꾼다.

python tools/ice-art/process.py <받은 원본 폴더> [이름=시드 ...]
- 하늘 ice_sky·얼음 단면 ice_ground: 4×4칸마다 가장 많은 색 하나(32색) → 1px = 게임 1px
- 중간 거리 ice_mid: 같은 방법으로 줄인 뒤, 위쪽 가장자리에서 이어진 하늘색을 투명하게 뺌
- 소품: 배경을 빼고 정한 키의 도트로 (연은 주인공과 같은 2배 해상도)
- 시드마다 assets/ice/gen/에 만들고, 고른 시드(이름=시드, 없으면 첫 시드)를 assets/ice/<이름>.png로 복사
"""
import shutil, sys
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'tower-art'))
sys.path.insert(0, str(ROOT / 'tools' / 'enemy-gen'))
from process import blockify  # noqa: E402
from extract import extract   # noqa: E402

OUT = ROOT / 'assets' / 'ice'
HEIGHT = {'kite': 30, 'ship': 80, 'barrel': 16, 'hut': 34, 'buoy': 28, 'berg': 30, 'flag': 40}


def key_sky(im, tol=40):
    """위쪽 가장자리에서 이어진, 하늘색과 비슷한 칸을 투명하게"""
    a = np.asarray(im.convert('RGB')).astype(int)
    h, w, _ = a.shape
    sky = np.median(a[0], axis=0)
    near = np.abs(a - sky).sum(2) < tol
    out = np.zeros((h, w), bool)
    q = deque((0, x) for x in range(w) if near[0, x])
    for y, x in q: out[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, (x + dx) % w
            if 0 <= ny < h and near[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True; q.append((ny, nx))
    rgba = np.dstack([a.astype(np.uint8), np.where(out, 0, 255).astype(np.uint8)])
    return Image.fromarray(rgba, 'RGBA')


def main(src, picks):
    src = Path(src)
    (OUT / 'gen').mkdir(parents=True, exist_ok=True)
    done = {}
    for p in sorted(src.glob('*.png')):
        name, seed = p.stem.rsplit('_s', 1)
        if name in ('ice_sky', 'ice_ground'):
            im = blockify(Image.open(p))
        elif name == 'ice_mid':
            im = key_sky(blockify(Image.open(p)))
        elif name in HEIGHT:
            im = extract(p, HEIGHT[name], 24)
        else:
            continue
        im.save(OUT / 'gen' / f'{p.stem}.png')
        done.setdefault(name, []).append(seed)
        print('ok', p.name, im.size)
    for name, seeds in done.items():
        seed = picks.get(name, seeds[0])
        shutil.copy(OUT / 'gen' / f'{name}_s{seed}.png', OUT / f'{name}.png')
    if (src / 'prompts.json').exists():
        shutil.copy(src / 'prompts.json', OUT / 'gen' / 'prompts_art.json')


if __name__ == '__main__':
    main(sys.argv[1], dict(a.split('=') for a in sys.argv[2:]))
