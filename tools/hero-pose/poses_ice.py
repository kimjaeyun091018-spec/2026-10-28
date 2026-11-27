"""얼음 바다 스케이트 주인공(털 파카, 2.5등신)용 프레임별 관절 포즈 → OpenPose 스켈레톤 그림.

poses_small.py의 체형·그리기를 그대로 쓰고 동작만 스케이트용으로 바꿈.
동작: skate 8(한쪽씩 뒤로 밀어 차기) · tuck 1(낮게 웅크려 속도 내기) · jump 3(준비·공중·착지)
      grind 1(레일 위 균형) · glide 2(머리 위 연 손잡이를 잡고 활공 · 몸을 숙여 다이브) · boost 1(두 손 얼음 송곳으로 얼음을 찍어 밀기)
Kaggle 생성 스크립트가 이 파일을 그대로 품어 씀.
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)) if '__file__' in globals() else None

from PIL import Image, ImageDraw

THIGH, SHIN = 0.165, 0.155
UPPER, FORE = 0.12, 0.11
HIP_Y = 0.67
NECK_DROP = 0.25

# 스케이트 밀어 차기: (가까운 다리, 먼 다리, 몸 높이 변화, 상체 기울기, 가까운 팔, 먼 팔)
SKATE = [
    ((22, 40), (18, 40), 0.06, 18, (-35, 20), (30, 20)),     # 두 발 모아 미끄러짐
    ((-20, 20), (24, 50), 0.07, 22, (35, 25), (-40, 15)),    # 가까운 발을 뒤로 밀기 시작
    ((-45, 8), (28, 58), 0.09, 26, (50, 25), (-55, 10)),     # 가까운 다리를 뒤로 쭉 뻗음
    ((-5, 70), (24, 50), 0.07, 22, (20, 25), (-25, 15)),     # 가까운 발을 끌어와 앞으로
]
SKATE = SKATE + [(b, a, h, l, af, an) for (a, b, h, l, an, af) in SKATE]
TUCK = ((62, 115), (55, 110), 0.15, 38, (40, 60), (30, 60))
JUMP = [
    ((55, 100), (48, 95), 0.13, 25, (-40, 30), (-55, 20)),   # 준비
    ((80, 120), (70, 120), 0.06, 12, (100, 40), (70, 40)),   # 공중: 무릎을 끌어올림
    ((40, 80), (34, 76), 0.10, 20, (70, 40), (-50, 30)),     # 착지
]
GRIND = ((35, 70), (28, 64), 0.08, 10, (95, 10), (-85, 10))
GLIDE = [
    ((-6, 20), (-14, 26), 0.0, 8, (172, 0), (165, 0)),       # 날개 손잡이를 머리 위로 잡고 활공
    ((-20, 10), (-26, 14), 0.0, 34, (150, 0), (145, 0)),     # 머리를 숙여 다이브
]
BOOST = ((30, 50), (-30, 10), 0.08, 40, (-40, 10), (-55, 10))

TEXT = {
    'skate': [
        'ice skating forward, gliding on both skates, knees bent, leaning forward',
        'ice skating, pushing one skate backward to gain speed, leaning forward',
        'ice skating, one leg fully stretched back after a powerful push stride, leaning forward',
        'ice skating, bringing the back skate forward again, leaning forward',
    ],
    'tuck': 'speed tuck on ice skates, crouching very low, leaning far forward',
    'jump': [
        'crouching low on ice skates before jumping off a ramp',
        'airborne jump on ice skates, knees pulled up to the chest',
        'landing on ice skates, knees bent absorbing the impact',
    ],
    'grind': 'grinding along a rail on ice skates, balancing with both arms stretched out to the sides, knees bent',
    'glide': [
        'flying with a traction kite, both arms raised straight up above the head gripping a handle bar, body hanging straight, legs together',
        'diving down with a traction kite, arms raised up above the head gripping a handle bar, body tilted forward, legs trailing back',
    ],
    'boost': 'speed skater pushing hard with two ice picks stabbed into the ice behind, body leaning far forward, both arms swept back',
}


def leg_points(hip, thigh_deg, knee_bend):
    t = math.radians(thigh_deg)
    knee = (hip[0] + THIGH * math.sin(t), hip[1] + THIGH * math.cos(t))
    s = t - math.radians(knee_bend)
    return knee, (knee[0] + SHIN * math.sin(s), knee[1] + SHIN * math.cos(s))


def arm_points(sho, upper_deg, elbow_bend):
    u = math.radians(upper_deg)
    elb = (sho[0] + UPPER * math.sin(u), sho[1] + UPPER * math.cos(u))
    f = u + math.radians(elbow_bend)
    return elb, (elb[0] + FORE * math.sin(f), elb[1] + FORE * math.cos(f))


def skeleton(near, far, drop, lean, arm_n, arm_f):
    hip = (0.0, HIP_Y + drop)
    ln = math.radians(lean)
    neck = (hip[0] + NECK_DROP * math.sin(ln), hip[1] - NECK_DROP * math.cos(ln))
    nose = (neck[0] + 0.11, neck[1] - 0.13)
    eye = (neck[0] + 0.085, neck[1] - 0.19)
    ear = (neck[0] + 0.0, neck[1] - 0.17)
    sho_n = (neck[0] + 0.01, neck[1] + 0.02)
    sho_f = (neck[0] - 0.01, neck[1] + 0.015)
    k_n, a_n = leg_points((hip[0] + 0.01, hip[1]), *near)
    k_f, a_f = leg_points((hip[0] - 0.01, hip[1]), *far)
    e_n, w_n = arm_points(sho_n, *arm_n)
    e_f, w_f = arm_points(sho_f, *arm_f)
    return [nose, neck, sho_n, e_n, w_n, sho_f, e_f, w_f,
            (hip[0] + 0.01, hip[1]), k_n, a_n, (hip[0] - 0.01, hip[1]), k_f, a_f,
            eye, None, ear, None]


LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13),
         (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]
COLORS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0),
          (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255),
          (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]


def draw(points, size=1024, height=0.78, top=0.12, cx=0.5):
    im = Image.new('RGB', (size, size), (0, 0, 0))
    d = ImageDraw.Draw(im)
    P = [None if p is None else (size * cx + p[0] * size * height, size * top + p[1] * size * height) for p in points]
    for i, (a, b) in enumerate(LIMBS):
        if P[a] is not None and P[b] is not None:
            d.line([P[a], P[b]], fill=tuple(int(v * 0.6) for v in COLORS[i]), width=max(4, size // 110))
    for i, p in enumerate(P):
        if p is not None:
            r = max(3, size // 160)
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=COLORS[i])
    return im


def all_poses():
    out = []
    for i, (n, f, h, l, an, af) in enumerate(SKATE):
        out.append((f'skate_{i}', skeleton(n, f, h, l, an, af), TEXT['skate'][i % 4]))
    out.append(('tuck_0', skeleton(*TUCK), TEXT['tuck']))
    for i, p in enumerate(JUMP):
        out.append((f'jump_{i}', skeleton(*p), TEXT['jump'][i]))
    out.append(('grind_0', skeleton(*GRIND), TEXT['grind']))
    for i, p in enumerate(GLIDE):
        out.append((f'glide_{i}', skeleton(*p), TEXT['glide'][i]))
    out.append(('boost_0', skeleton(*BOOST), TEXT['boost']))
    return out


if __name__ == '__main__':
    dst = Path(sys.argv[1] if len(sys.argv) > 1 else 'pose_preview')
    dst.mkdir(parents=True, exist_ok=True)
    poses = all_poses()
    sheet = Image.new('RGB', (200 * 8, 200 * 2))
    for i, (_, p, _) in enumerate(poses):
        sheet.paste(draw(p, 200), ((i % 8) * 200, (i // 8) * 200))
    sheet.save(dst / 'poses_skate.png')
    print(len(poses), 'poses →', dst / 'poses_skate.png')
