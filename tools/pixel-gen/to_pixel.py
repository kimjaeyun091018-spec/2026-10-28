"""Kaggle에서 받은 그림을 도트 격자에 맞춰 줄이고 색 수를 제한해 assets/pixel/에 저장한다.
사용: python tools/pixel-gen/to_pixel.py <받은 폴더>
- 배경: 1344×768 → 224×128 (원본 6px = 도트 1칸), 48색
- 질감: 1024 → 128 → 가로·세로 끝을 섞어 이음새 없게 → 112×112, 24색 (게임이 3배로 반복해 깖)
"""
import sys
import numpy as np
from pathlib import Path
from PIL import Image

src = Path(sys.argv[1]); out = Path(__file__).resolve().parents[2] / 'assets' / 'pixel'
out.mkdir(parents=True, exist_ok=True)
PICK = {'bg-forest': ('bg_forest_s33.png', 'bg'), 'bg-river': ('bg_river_s11.png', 'bg'),
        'moss': ('tex_moss_s11.png', 'tex'), 'soil': ('tex_soil_s22.png', 'tex'), 'wood': ('tex_wood_s11.png', 'tex')}

def quant(im, n):
    return im.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')

def seamless(im, o):
    a = np.asarray(im).astype(np.float32); h, w, _ = a.shape
    t = np.linspace(0, 1, o)[None, :, None]; a[:, :o] = a[:, w - o:] * (1 - t) + a[:, :o] * t; a = a[:, :w - o]
    t = np.linspace(0, 1, o)[:, None, None]; a[:o] = a[h - o:] * (1 - t) + a[:o] * t; a = a[:h - o]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

for name, (fn, kind) in PICK.items():
    im = Image.open(src / fn).convert('RGB')
    if kind == 'bg':
        im = quant(im.resize((224, 128), Image.BOX), 48)
    else:
        im = quant(seamless(im.resize((128, 128), Image.BOX), 16), 24)
    im.save(out / f'{name}.png', optimize=True)
    print(name, im.size)
