"""얼음 바다 스케이트 주인공(털 파카) 시트.

Kaggle(tools/hero-pose/gen_ice_kaggle.py, 포즈 poses_ice.py)에서 생성한 그림을
to_sprite.py로 도트화한 뒤 시트로 묶는다.
시트 줄(80×60): 0줄 skate 0~7 · 1줄 tuck, jump 0~2, grind, glide 0~1, boost

사용:  python tools/hero-anim/anim_ice.py <to_sprite 출력 폴더> <시드>
결과:  assets/ice/skater_sheet.png
"""
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FW, FH = 80, 60
ROWS = [[f'skate_{i}' for i in range(8)],
        ['tuck_0', 'jump_0', 'jump_1', 'jump_2', 'grind_0', 'glide_0', 'glide_1', 'boost_0']]


def main(src, seed):
    src = Path(src)
    sheet = Image.new('RGBA', (FW * 8, FH * len(ROWS)))
    for r, names in enumerate(ROWS):
        for c, n in enumerate(names):
            p = src / f'{n}_s{seed}.png'
            if p.exists():
                sheet.paste(Image.open(p).convert('RGBA'), (c * FW, r * FH))
    out = ROOT / 'assets' / 'ice' / 'skater_sheet.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print('ok', out, sheet.size)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
