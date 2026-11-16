"""Kaggle에서 생성한 1024px 프레임을 게임용 도트 프레임(96x80)으로 바꾼다.

- 배경(밝은 회색)을 가장자리에서부터 지움
- 같은 묶음(예: 걷기 8장) 전체에서 뽑은 공통 색 40개로 맞춤 → 프레임마다 색이 같아짐
- 11px 블록마다 가장 많은 색 하나로 줄임 (키 약 62px, 기존 시트와 같은 크기)
- 포즈 스켈레톤 좌표를 그대로 써서 위치를 맞춤: 엉덩이 x=43, 서 있을 때 발바닥 y=77
  (웅크림·착지는 발이 바닥에 그대로, 공중 프레임은 다리를 접은 만큼 발이 올라감)

사용:  python to_sprite.py <생성 PNG 폴더> <출력 폴더>   (파일 이름: <동작>_<번호>_s<시드>.png)
작은 주인공: python to_sprite.py <폴더> <출력> --height 44 --frame 80x60 --anchor 32,57 --hip-y 0.67 --by-seed
"""
import sys
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
# 기본값은 1판(키 62px, poses.py) 설정. 작은 주인공은 main()의 옵션으로 바꿈
FW, FH = 96, 80
BLOCK = 11
HIP_Y = 0.53                                        # poses의 서 있을 때 엉덩이 높이 (키 1.0 기준)
HIP_GEN = (512, 123 + HIP_Y * 0.78 * 1024)          # poses.draw 기준 서 있을 때 엉덩이 위치 (1024 그림)
SOLE_GEN = 123 + 1.0 * 0.78 * 1024                  # 서 있을 때 발바닥 y (1024 그림)
HIP_OUT = (43, 77 - (SOLE_GEN - HIP_GEN[1]) / BLOCK)   # 발바닥이 프레임 y=77에 오도록


def configure(height=None, frame=None, anchor=None, hip_y=None):
    """작은 주인공용: 키 height px, 프레임 크기, 발 기준점, 포즈의 엉덩이 높이."""
    global FW, FH, BLOCK, HIP_Y, HIP_GEN, HIP_OUT
    if hip_y is not None:
        HIP_Y = hip_y
        HIP_GEN = (512, 123 + HIP_Y * 0.78 * 1024)
    if height:
        BLOCK = 0.78 * 1024 / height
    if frame:
        FW, FH = frame
    ax, ay = anchor if anchor else (43, 77)
    HIP_OUT = (ax, ay - (SOLE_GEN - HIP_GEN[1]) / BLOCK)


def palette(paths):
    """여러 생성 그림의 캐릭터 픽셀을 모아 공통 팔레트 40색을 만든다."""
    px = []
    for p in paths:
        rgb = np.asarray(Image.open(p).convert('RGB'))
        m = ~background_mask(rgb)
        px.append(rgb[m][::7])
    px = np.concatenate(px)
    strip = Image.fromarray(px.reshape(1, -1, 3).astype('uint8'))
    return strip.quantize(NCOL, method=Image.Quantize.MEDIANCUT)


NCOL = 40


def background_mask(rgb):
    h, w = rgb.shape[:2]
    corners = np.array([rgb[2, 2], rgb[2, w - 3], rgb[h - 3, 2], rgb[h - 3, w - 3]]).astype(int)
    bg = np.median(corners, axis=0)
    c = rgb.astype(int)
    near = np.abs(c - bg).sum(2) < 38
    sat = c.max(2) - c.min(2)
    near |= (sat < 16) & (c.mean(2) > 55) & (np.abs(c - bg).sum(2) < 150)   # 바닥 그림자(채도 낮은 회색)
    mask = np.zeros((h, w), bool)
    q = deque([(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)])
    for p in q:
        mask[p] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            Y, X = y + dy, x + dx
            if 0 <= Y < h and 0 <= X < w and not mask[Y, X] and near[Y, X]:
                mask[Y, X] = True
                q.append((Y, X))
    return mask


def to_frame(path, pal):
    im = Image.open(path).convert('RGB')
    rgb = np.asarray(im)
    bgm = background_mask(rgb)
    idx = np.asarray(im.quantize(palette=pal, dither=Image.Dither.NONE))
    colors = np.array(pal.getpalette()[:NCOL * 3]).reshape(NCOL, 3)
    out = np.zeros((FH, FW, 4), np.uint8)
    for y in range(FH):
        Y0 = int(round(HIP_GEN[1] + (y - HIP_OUT[1]) * BLOCK))
        Y1 = int(round(HIP_GEN[1] + (y + 1 - HIP_OUT[1]) * BLOCK))
        for x in range(FW):
            X0 = int(round(HIP_GEN[0] + (x - HIP_OUT[0]) * BLOCK))
            X1 = int(round(HIP_GEN[0] + (x + 1 - HIP_OUT[0]) * BLOCK))
            if X0 < 0 or Y0 < 0 or X1 > 1024 or Y1 > 1024:
                continue
            m = bgm[Y0:Y1, X0:X1]
            if m.mean() > 0.5:
                continue
            c = Counter(idx[Y0:Y1, X0:X1][~m].ravel().tolist()).most_common(1)[0][0]
            out[y, x, :3] = colors[c]
            out[y, x, 3] = 255
    # 떨어진 점 하나짜리 지우기
    al = out[..., 3] > 0
    for y in range(FH):
        for x in range(FW):
            if al[y, x] and not any(0 <= y + dy < FH and 0 <= x + dx < FW and al[y + dy, x + dx]
                                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y, x, 3] = 0
    return Image.fromarray(out, 'RGBA')


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--height', type=float, help='도트 키(px). 예: 44')
    ap.add_argument('--frame', help='프레임 크기 WxH. 예: 80x60')
    ap.add_argument('--anchor', help='발 기준점 x,y. 예: 32,57')
    ap.add_argument('--hip-y', type=float, help='포즈 파일의 HIP_Y (poses_small.py는 0.67)')
    ap.add_argument('--by-seed', action='store_true', help='시드마다 모든 동작에 공통 팔레트 (동작 사이 색 일치)')
    a = ap.parse_args()
    configure(a.height, tuple(map(int, a.frame.split('x'))) if a.frame else None,
              tuple(map(int, a.anchor.split(','))) if a.anchor else None, a.hip_y)
    src, dst = Path(a.src), Path(a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    groups = {}
    for p in sorted(src.glob('*_s*.png')):
        kind, _, seed = p.stem.split('_')
        groups.setdefault(seed if a.by_seed else (kind, seed), []).append(p)
    for paths in groups.values():
        pal = palette(paths)
        for p in paths:
            to_frame(p, pal).save(dst / p.name)
            print('ok', p.name)


if __name__ == '__main__':
    main()
