"""웅크리기 줄 만들기: hero_sheet.png의 서기(0줄)·걷기(1줄) 프레임에서
허벅지 부분(44~52줄, 걷기는 44~49줄)을 빼고 윗몸을 아래로 내려 앞으로 살짝 숙인 프레임을 만들어 시트 아래에 붙임.
  5줄: 웅크려 서기 4프레임, 6줄: 웅크려 걷기 8프레임
python3 tools/hero-anim/crouch.py  (여러 번 돌려도 같은 결과: 0~4줄만 남기고 다시 붙임)"""
from PIL import Image
P = 'assets/hero/hero_sheet.png'
FW, FH = 80, 60
src = Image.open(P).convert('RGBA')
base = src.crop((0, 0, src.width, FH * 5))
out = Image.new('RGBA', (src.width, FH * 7), (0, 0, 0, 0))
out.paste(base, (0, 0))
CUT0, CUT1, LEAN = 44, 53, 2      # 44~52줄(허벅지)을 빼고, 윗몸은 9줄 내려가며 앞으로 2px

def crouch(fr, lean, cut1=CUT1):
    o = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
    o.paste(fr.crop((0, cut1, FW, FH)), (0, cut1))                       # 발(부츠)은 그대로
    up = fr.crop((0, 0, FW, CUT0))
    o.alpha_composite(up, (lean, cut1 - CUT0))                           # 윗몸
    return o

for row, n, dst, cut1 in [(0, 4, 5, CUT1), (1, 8, 6, 50)]:   # 걷기는 정강이를 조금 남겨 발이 떨어져 보이지 않게
    for f in range(n):
        fr = src.crop((f * FW, row * FH, f * FW + FW, row * FH + FH))
        out.paste(crouch(fr, LEAN, cut1), (f * FW, dst * FH))
out.save(P)
print(out.size)
