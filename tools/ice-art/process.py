"""Kaggle에서 만든 얼음 바다 그림을 받아 게임용 도트로 바꾼다.

python tools/ice-art/process.py <받은 원본 폴더> [이름=시드 ...]
- 하늘 ice_sky·얼음 단면 ice_ground: 4×4칸마다 가장 많은 색 하나(32색) → 1px = 게임 1px
- 중간 거리 ice_mid: 같은 방법으로 줄인 뒤, 위쪽(하늘·먼 산)을 4×4 바이어 무늬로 점점 투명하게 (70~105줄) → 먼 하늘 그림이 비쳐 보임
  (단색 하늘을 부탁했지만 구름 낀 하늘이 그려져서 색으로 빼지 않고 높이로 뺌)
- 얼음 단면 ice_ground·연 kite는 생성 결과가 맞지 않아(단면 대신 풍경, 연 대신 새·곡괭이) 쓰지 않음 → 게임 코드가 직접 그림
- 깃발 flag 시드 5: 깃발 옆에 등불이 따로 그려져서 왼쪽 깃발만 잘라 씀
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
HEIGHT = {'ship': 80, 'barrel': 16, 'hut': 34, 'buoy': 28, 'berg': 30, 'flag': 40}


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


BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16


def fade_top(im, y0=70, y1=105):
    """y0줄 위는 투명, y1줄 아래는 그대로, 사이는 바이어 무늬로 점점 보이게"""
    a = np.asarray(im.convert('RGBA')).copy()
    h, w, _ = a.shape
    for y in range(h):
        t = min(1, max(0, (y - y0) / (y1 - y0)))
        a[y, :, 3] = np.where(t > BAYER[y % 4][np.arange(w) % 4], 255, 0)
    return Image.fromarray(a, 'RGBA')


def main(src, picks):
    src = Path(src)
    (OUT / 'gen').mkdir(parents=True, exist_ok=True)
    done = {}
    for p in sorted(src.glob('*.png')):
        name, seed = p.stem.rsplit('_s', 1)
        if name == 'ice_sky':
            im = blockify(Image.open(p))
        elif name == 'ice_mid':
            im = fade_top(blockify(Image.open(p)))
        elif name == 'flag' and seed == '5':
            crop = Image.open(p).convert('RGB').crop((0, 0, 700, 1024)); tmp = OUT / 'gen' / '_flag_crop.png'
            Image.new('RGB', (1024, 1024), crop.getpixel((5, 5))).save(tmp); c = Image.open(tmp); c.paste(crop, (0, 0)); c.save(tmp)
            im = extract(tmp, HEIGHT[name], 24); tmp.unlink()
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


# 고른 시드: python tools/ice-art/process.py <폴더> ice_sky=11 ice_mid=22 ship=4 hut=4 barrel=4 buoy=4 berg=4 flag=5
if __name__ == '__main__':
    main(sys.argv[1], dict(a.split('=') for a in sys.argv[2:]))
