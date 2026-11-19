"""Kaggle에서 만든 원통 탑 그림을 받아 게임용 도트로 바꾼다.

python tools/tower-art/process.py <받은 원본 폴더>
- 벽 그림(wall_*): 4×4칸마다 가장 많은 색 하나로 줄여 1px = 게임 1px (1536×640 → 384×160, 원통 한 층 높이),
  그림마다 32색. 가로로 이어지는 그림이라 줄여도 왼쪽·오른쪽 끝이 맞음 → assets/tower/
- 식물(vine_hang·grass·fern·roots): 배경을 빼고 정한 키의 도트로 (tools/enemy-gen/extract.py) → assets/tower/
- 주인공 시안(hero_*): 키 44px 도트(지금 주인공과 같은 2배 해상도) + 원본 축소판 모음 → assets/tower/hero_concepts/
"""
import shutil, sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'enemy-gen'))
from extract import extract  # noqa: E402

OUT = ROOT / 'assets' / 'tower'
HEIGHT = {'vine_hang': 112, 'roots': 112, 'grass': 44, 'fern': 40}


def blockify(im, block=4, ncol=32):
    """block×block칸마다 가장 많은 색 (팔레트 ncol색)"""
    im = im.convert('RGB')
    pal = im.quantize(ncol, method=Image.Quantize.MEDIANCUT)
    idx = np.asarray(im.quantize(palette=pal, dither=Image.Dither.NONE))
    colors = np.array(pal.getpalette()[:ncol * 3]).reshape(ncol, 3)
    h, w = idx.shape[0] // block, idx.shape[1] // block
    out = np.zeros((h, w, 3), np.uint8)
    for y in range(h):
        for x in range(w):
            c = Counter(idx[y * block:(y + 1) * block, x * block:(x + 1) * block].ravel().tolist()).most_common(1)[0][0]
            out[y, x] = colors[c]
    return Image.fromarray(out)


def main(src):
    src = Path(src)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'hero_concepts').mkdir(exist_ok=True)
    heroes = []
    for p in sorted(src.glob('*.png')):
        name = p.stem.rsplit('_s', 1)[0]
        if name.startswith('wall_'):
            blockify(Image.open(p)).save(OUT / f'{p.stem}.png')
        elif name in HEIGHT:
            extract(p, HEIGHT[name], 24).save(OUT / f'{p.stem}.png')
        elif name == 'hero':
            extract(p, 44, 28).save(OUT / 'hero_concepts' / f'{p.stem}.png')
            heroes.append(p)
        print('ok', p.name)
    if heroes:                                  # 원본 축소판 모음 (고르기용)
        th = [Image.open(p).convert('RGB').resize((320, 320), Image.NEAREST) for p in heroes]
        sheet = Image.new('RGB', (320 * len(th), 320), 'white')
        for i, t in enumerate(th): sheet.paste(t, (i * 320, 0))
        sheet.save(OUT / 'hero_concepts' / 'sheet.png')
    if (src / 'prompts.json').exists():
        shutil.copy(src / 'prompts.json', OUT / 'prompts.json')


if __name__ == '__main__':
    main(sys.argv[1])
