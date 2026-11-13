"""생성한 적 그림(1024px, 밝은 회색 배경)에서 적만 잘라 원하는 키의 도트로 줄인다.

- 가장자리에서부터 배경과 바닥 그림자를 지움 (tools/hero-pose/to_sprite.py와 같은 방식)
- 적이 차지한 영역을 잘라, 키가 height px이 되도록 블록마다 가장 많은 색 하나로 줄임
- 색은 그 그림에서 뽑은 ncol색으로 맞춤
사용:  python extract.py <생성 PNG> <출력 PNG> <키px> [색 수]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hero-pose'))
from to_sprite import background_mask  # noqa: E402


def extract(src, height, ncol=28):
    im = Image.open(src).convert('RGB')
    rgb = np.asarray(im)
    bg = background_mask(rgb)
    # 다리 사이처럼 테두리와 이어지지 않은 배경·그림자 (채도가 낮은 회색)도 지움
    c = rgb.astype(int)
    corner = np.median(np.array([c[2, 2], c[2, -3], c[-3, 2], c[-3, -3]]), axis=0)
    sat = c.max(2) - c.min(2)
    bg |= (sat < 14) & (np.abs(c - corner).sum(2) < 120)
    ys, xs = np.where(~bg)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    block = (y1 - y0) / height
    w = int(round((x1 - x0) / block))
    px = rgb[~bg][::5]
    pal = Image.fromarray(px.reshape(1, -1, 3).astype('uint8')).quantize(ncol, method=Image.Quantize.MEDIANCUT)
    idx = np.asarray(im.quantize(palette=pal, dither=Image.Dither.NONE))
    colors = np.array(pal.getpalette()[:ncol * 3]).reshape(ncol, 3)
    out = np.zeros((height, w, 4), np.uint8)
    for y in range(height):
        for x in range(w):
            Y0, Y1 = int(y0 + y * block), int(y0 + (y + 1) * block)
            X0, X1 = int(x0 + x * block), int(x0 + (x + 1) * block)
            m = bg[Y0:Y1, X0:X1]
            if m.size == 0 or m.mean() > 0.5:
                continue
            c = Counter(idx[Y0:Y1, X0:X1][~m].ravel().tolist()).most_common(1)[0][0]
            out[y, x] = (*colors[c], 255)
    return Image.fromarray(out, 'RGBA')


if __name__ == '__main__':
    extract(sys.argv[1], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 28).save(sys.argv[2])
    print('ok', sys.argv[2])
