"""작은 주인공(2.5등신, 게임 키 약 22px)용 프레임별 관절 포즈 → OpenPose 스켈레톤 그림.

poses.py와 같은 방식이지만 머리가 크고(키의 약 40%) 팔다리가 짧은 체형.
동작: idle 1 · walk 8 · jump 6 · whip 4(화분 덩굴 채찍 휘두르기) · grapple 1(화분을 앞 위로 겨눔)
좌표: 키 1.0 기준, 정수리 y=0, 발바닥 y=1.0. 오른쪽(+x)이 앞. 카메라 쪽 팔다리 = OpenPose R, 먼 쪽 = L.
Kaggle 생성 스크립트가 이 파일을 그대로 품어 씀 (다른 파일을 import하지 않음).
"""
import math

from PIL import Image, ImageDraw

THIGH, SHIN = 0.165, 0.155
UPPER, FORE = 0.12, 0.11
HIP_Y = 0.67          # 서 있을 때 엉덩이 높이
NECK_DROP = 0.25      # 엉덩이 → 목 (몸통이 짧음)

# 다리: (허벅지 각도, 무릎 굽힘) 도. 팔: (윗팔 각도, 팔꿈치 굽힘) 도 — 0은 아래, +는 앞, 180은 위
POT = (25, 100)       # 가까운 손: 화분을 가슴 앞에
WALK = [  # (가까운 다리, 먼 다리, 몸 높이 변화, 상체 기울기, 먼 팔 흔들기 각도)
    ((24, 4), (-20, 12), 0.000, 4, -22),
    ((14, 20), (-12, 50), 0.020, 5, -10),
    ((2, 8), (14, 75), 0.008, 4, 6),
    ((-14, 4), (28, 38), -0.010, 3, 20),
]
WALK = WALK + [(b, a, h, l, -s) for (a, b, h, l, s) in WALK]
JUMP = [  # (가까운 다리, 먼 다리, 몸 높이 변화, 기울기, 가까운 팔, 먼 팔)
    ((55, 110), (48, 100), 0.12, 20, (-30, 40), (-50, 20)),     # 준비: 깊게 웅크림, 팔은 뒤로
    ((-8, 2), (-14, 6), -0.03, 8, (140, 30), (120, 30)),        # 도약: 다리를 펴서 박참, 팔은 위로
    ((70, 100), (55, 105), 0.03, 6, (120, 40), (90, 40)),       # 상승: 무릎을 가슴으로 끌어올림
    ((88, 130), (78, 130), 0.05, 4, (80, 60), (-60, 30)),       # 정점: 가장 오므림
    ((25, 30), (-8, 45), 0.00, 2, (70, 40), (-70, 20)),         # 하강: 다리를 아래로 폄, 팔 벌림
    ((42, 88), (32, 80), 0.09, 14, (60, 60), (40, 30)),         # 착지: 무릎 굽혀 충격 흡수
]
WHIP = [  # (가까운 팔, 상체 기울기) — 다리는 앞뒤로 벌린 자세
    ((-150, 40), -6),     # 뒤로 크게 젖힘
    ((170, 20), 0),       # 머리 위로
    ((95, 0), 12),        # 앞으로 내리침
    ((40, 10), 16),       # 휘두른 뒤 아래로
]
GRAPPLE = ((135, 0), 4)   # 화분을 앞 위로 쭉 뻗어 겨눔

TEXT = {
    'idle': 'standing still, relaxed, holding the flower pot at chest height',
    'walk': [
        'walking, contact pose: front leg forward with the heel touching the ground, back leg pushing off on the toes',
        'walking, down pose: weight on the front leg with the knee slightly bent, back foot lifting off',
        'walking, passing pose: supporting leg straight under the body, other leg lifted with knee bent passing forward',
        'walking, up pose: rising on the toes of the back leg, swinging leg reaching forward',
    ],
    'jump': [
        'crouching low before a jump, knees deeply bent, arms swung back',
        'jumping off the ground, legs fully extended, arms swinging up',
        'in mid-air rising, knees pulled up toward the chest',
        'at the peak of a jump in mid-air, legs tightly tucked, knees near the chest',
        'falling in mid-air, legs extending down to land, arms out for balance',
        'landing, knees bent absorbing the impact, crouching',
    ],
    'whip': [
        'swinging back the flower pot behind the head, winding up an attack',
        'raising the flower pot high above the head',
        'swinging the flower pot forward hard, arm stretched forward',
        'follow-through after a swing, arm down and forward, leaning forward',
    ],
    'grapple': 'aiming the flower pot forward and upward with the arm fully stretched out',
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
    nose = (neck[0] + 0.11, neck[1] - 0.13)            # 큰 머리
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
    out = [('idle_0', skeleton((4, 4), (-4, 4), 0.0, 2, POT, (-6, 10)), TEXT['idle'])]
    for i, (n, f, h, l, sw) in enumerate(WALK):
        out.append((f'walk_{i}', skeleton(n, f, h, l, POT, (sw, 12)), TEXT['walk'][i % 4]))
    for i, (n, f, h, l, an, af) in enumerate(JUMP):
        out.append((f'jump_{i}', skeleton(n, f, h, l, an, af), TEXT['jump'][i]))
    for i, (an, l) in enumerate(WHIP):
        out.append((f'whip_{i}', skeleton((18, 8), (-18, 14), 0.02, l, an, (-30, 20)), TEXT['whip'][i]))
    an, l = GRAPPLE
    out.append(('grapple_0', skeleton((12, 6), (-16, 12), 0.0, l, an, (-40, 20)), TEXT['grapple']))
    return out


if __name__ == '__main__':
    import sys
    from pathlib import Path
    dst = Path(sys.argv[1] if len(sys.argv) > 1 else 'pose_preview')
    dst.mkdir(parents=True, exist_ok=True)
    poses = all_poses()
    sheet = Image.new('RGB', (200 * 10, 200 * 2))
    for i, (_, p, _) in enumerate(poses):
        sheet.paste(draw(p, 200), ((i % 10) * 200, (i // 10) * 200))
    sheet.save(dst / 'poses_small.png')
    print(len(poses), 'poses →', dst / 'poses_small.png')
