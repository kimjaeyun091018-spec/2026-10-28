"""원통 탑 주인공(잠수부 헬멧) 애니메이션 시트.

Kaggle(tools/hero-pose/gen_diver_kaggle.py)에서 프레임별 관절 포즈로 생성한 그림을
to_sprite.py로 도트화(키 52px = 게임 26px, 프레임 80x60, 발 기준점 32,57)한 뒤 시트로 묶는다.
웅크리기 두 줄은 crouch.py와 같은 방식(허벅지 부분을 빼고 윗몸을 내림)으로 서기·걷기에서 만듦.
시트 줄: idle 1(숨쉬기로 4프레임) · walk 8 · jump 6 · grapple 1 · whip 4 · crouch 4 · cwalk 8  (지금 주인공 시트와 같은 배치)

사용:  python tools/hero-anim/anim_diver.py <to_sprite 출력 폴더> <시드>
결과:  assets/tower/diver_sheet.png
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FW, FH = 80, 60


def frame(src, name, seed):
    p = src / f'{name}_s{seed}.png'
    return Image.open(p).convert('RGBA') if p.exists() else Image.new('RGBA', (FW, FH))


def breathe(im, k):
    """대기 숨쉬기: k번째 프레임에서 윗몸(발 위쪽)을 1px 내림"""
    if k % 2 == 0:
        return im
    a = np.asarray(im).copy(); out = np.zeros_like(a)
    cut = 44
    out[cut:] = a[cut:]; out[1:cut + 1] = np.where(a[0:cut, ..., 3:4] > 0, a[0:cut], out[1:cut + 1])
    return Image.fromarray(out)


def crouch(im, cut0, cut1, lean=2):
    o = Image.new('RGBA', (FW, FH))
    o.paste(im.crop((0, cut1, FW, FH)), (0, cut1))
    o.alpha_composite(im.crop((0, 0, FW, cut0)), (lean, cut1 - cut0))
    return o


def main(src, seed):
    src = Path(src)
    rows = [
        [breathe(frame(src, 'idle_0', seed), k) for k in range(4)],
        [frame(src, f'walk_{i}', seed) for i in range(8)],
        [frame(src, f'jump_{i}', seed) for i in range(6)],
        [frame(src, 'grapple_0', seed)],
        [frame(src, f'whip_{i}', seed) for i in range(4)],
    ]
    # 웅크리기: 엉덩이~무릎(키 52px 기준 대략 38~46줄)을 빼고 윗몸을 내림
    rows.append([crouch(f, 38, 47) for f in rows[0]])
    rows.append([crouch(f, 38, 44) for f in rows[1]])
    sheet = Image.new('RGBA', (FW * 8, FH * len(rows)))
    for r, fs in enumerate(rows):
        for c, f in enumerate(fs):
            sheet.paste(f, (c * FW, r * FH))
    out = ROOT / 'assets' / 'tower' / 'diver_sheet.png'
    sheet.save(out)
    print('ok', out, sheet.size)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
