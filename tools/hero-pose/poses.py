"""걷기·점프 프레임별 사람 관절 포즈 (옆모습, 오른쪽을 봄) → OpenPose 스켈레톤 그림.

ControlNet OpenPose에 넣을 조건 그림을 만든다. Kaggle 생성 스크립트(gen_kaggle.py)가 이 파일을 그대로 품어 쓴다.
좌표: 키 1.0 기준, 정수리 y=0, 발바닥 y=1.0. 오른쪽(+x)이 앞.
오른쪽을 보는 옆모습이라 카메라 쪽 팔다리는 OpenPose의 R(오른쪽), 먼 쪽은 L(왼쪽).
"""
import math

from PIL import Image, ImageDraw

THIGH, SHIN, FOOT = 0.235, 0.225, 0.07
UPPER, FORE = 0.15, 0.14
HIP_Y = 0.53          # 서 있을 때 엉덩이 높이 (정수리에서)
NECK_DROP = 0.33      # 엉덩이 → 목 길이

# 걷기 8프레임: (가까운 다리 허벅지 각도, 무릎 굽힘), (먼 다리 …), 몸 높이 변화, 상체 기울기
# 각도는 도. 허벅지 각도 +는 앞으로, 무릎 굽힘은 정강이가 허벅지보다 뒤로 꺾인 정도.
WALK = [
    # 0 접지: 앞발 뒤꿈치가 땅에 닿고 뒷발은 발끝으로 밈
    ((24, 4), (-20, 12), 0.000, 4),
    # 1 하강: 앞발에 체중이 실리며 무릎을 살짝 굽힘, 뒷발은 땅을 떠나며 무릎이 많이 굽음
    ((14, 18), (-12, 45), 0.025, 5),
    # 2 통과: 지지하는 다리는 수직, 뒤에서 오는 다리는 무릎을 굽혀 발을 들어 앞으로 지나감
    ((2, 8), (12, 70), 0.010, 4),
    # 3 상승: 지지 다리가 뒤로 가며 발끝으로 밀어 몸이 가장 높음, 흔드는 다리는 앞으로 뻗기 시작
    ((-14, 4), (28, 35), -0.012, 3),
]
WALK = WALK + [((b[0], b[1]), (a[0], a[1]), h, l) for (a, b, h, l) in WALK]   # 4~7: 다리 바꿔 반복

# 점프 6프레임: (가까운 다리), (먼 다리), 몸 높이 변화(+는 낮아짐), 상체 기울기, 팔 자세
JUMP = [
    # 0 준비: 깊게 웅크림, 무릎이 많이 굽고 상체를 앞으로 숙임, 팔은 뒤로
    ((55, 110), (48, 100), 0.13, 22, 'back'),
    # 1 도약: 다리를 쭉 펴서 발끝으로 땅을 박참, 몸이 앞으로 기울고 팔은 위로 휘두름
    ((-8, 2), (-14, 6), -0.03, 10, 'up'),
    # 2 상승: 무릎을 가슴 쪽으로 끌어올리며 다리를 접기 시작
    ((60, 95), (45, 100), 0.04, 6, 'up'),
    # 3 정점: 다리를 가장 많이 오므림 (무릎이 가슴 가까이, 발뒤꿈치가 엉덩이 쪽)
    ((78, 125), (68, 125), 0.06, 4, 'out'),
    # 4 하강: 다리를 아래로 펴며 착지 준비, 앞다리가 약간 앞, 팔은 균형을 잡으려 벌림
    ((22, 30), (-6, 40), 0.00, 2, 'out'),
    # 5 착지: 충격을 받으며 무릎을 굽혀 낮게 앉음, 팔은 앞으로
    ((40, 85), (30, 80), 0.10, 16, 'front'),
]

WALK_TEXT = [
    'walk cycle contact pose: the front leg is stretched forward with the heel striking the ground, the back leg is behind pushing off on the toes, long stride',
    'walk cycle down pose: weight shifts onto the front leg with the knee slightly bent, the back foot lifts off the ground with the knee bending',
    'walk cycle passing pose: the supporting leg is straight under the body, the other leg is lifted with the knee bent and the foot passing forward beside it',
    'walk cycle up pose: the body rises on the toes of the back supporting leg, the swinging leg reaches forward ready to step',
]
WALK_TEXT = WALK_TEXT + WALK_TEXT
JUMP_TEXT = [
    'jump anticipation: crouching low with knees deeply bent, upper body leaning forward, arms swung back, ready to spring',
    'jump takeoff: legs fully extended pushing off the ground on the toes, body stretched upward and leaning forward, arms swinging up',
    'jumping upward in mid-air: knees pulled up toward the chest, legs folding under the body, coat flaring',
    'peak of the jump in mid-air: legs tightly tucked, knees close to the chest and heels near the hips, compact pose',
    'falling in mid-air: legs extending down to prepare for landing, front leg slightly forward, arms out for balance, coat flowing upward',
    'landing: knees bent absorbing the impact, crouching low, upper body leaning forward, arms forward for balance',
]


def leg_points(hip, thigh_deg, knee_bend):
    t = math.radians(thigh_deg)
    knee = (hip[0] + THIGH * math.sin(t), hip[1] + THIGH * math.cos(t))
    s = t - math.radians(knee_bend)
    ankle = (knee[0] + SHIN * math.sin(s), knee[1] + SHIN * math.cos(s))
    return knee, ankle


def arm_points(sho, upper_deg, elbow_bend):
    u = math.radians(upper_deg)
    elb = (sho[0] + UPPER * math.sin(u), sho[1] + UPPER * math.cos(u))
    f = u + math.radians(elbow_bend)
    wri = (elb[0] + FORE * math.sin(f), elb[1] + FORE * math.cos(f))
    return elb, wri


def skeleton(near, far, drop, lean, arms='walk', phase=0.0):
    """18개 관절 (OpenPose COCO 순서). 보이지 않는 관절은 None."""
    hip = (0.0, HIP_Y + drop)
    ln = math.radians(lean)
    neck = (hip[0] + NECK_DROP * math.sin(ln), hip[1] - NECK_DROP * math.cos(ln))
    nose = (neck[0] + 0.075, neck[1] - 0.075)
    eye = (neck[0] + 0.06, neck[1] - 0.105)
    ear = (neck[0] + 0.005, neck[1] - 0.095)
    sho_n = (neck[0] + 0.01, neck[1] + 0.025)
    sho_f = (neck[0] - 0.01, neck[1] + 0.02)
    k_n, a_n = leg_points((hip[0] + 0.01, hip[1]), *near)
    k_f, a_f = leg_points((hip[0] - 0.01, hip[1]), *far)
    # 팔: 가까운 손은 화분을 가슴 앞에 들고, 먼 손은 바구니를 들고 걸음에 맞춰 흔들림
    if arms == 'walk':
        e_n, w_n = arm_points(sho_n, 20, 95)
        e_f, w_f = arm_points(sho_f, -18 * math.cos(phase), 12)
    elif arms == 'back':
        e_n, w_n = arm_points(sho_n, -35, 40)
        e_f, w_f = arm_points(sho_f, -50, 20)
    elif arms == 'up':
        e_n, w_n = arm_points(sho_n, 120, 40)
        e_f, w_f = arm_points(sho_f, 100, 30)
    elif arms == 'out':
        e_n, w_n = arm_points(sho_n, 70, 50)
        e_f, w_f = arm_points(sho_f, -60, 20)
    else:  # front
        e_n, w_n = arm_points(sho_n, 60, 60)
        e_f, w_f = arm_points(sho_f, 40, 30)
    return [nose, neck, sho_n, e_n, w_n, sho_f, e_f, w_f,
            (hip[0] + 0.01, hip[1]), k_n, a_n, (hip[0] - 0.01, hip[1]), k_f, a_f,
            eye, None, ear, None]


LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13),
         (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]
COLORS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0),
          (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255),
          (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]


def draw(points, size=1024, height=0.78, top=0.12, cx=0.5):
    """OpenPose 스타일 그림 (검은 바탕, 색 막대 + 관절 점)."""
    im = Image.new('RGB', (size, size), (0, 0, 0))
    d = ImageDraw.Draw(im)
    P = [None if p is None else (size * cx + p[0] * size * height, size * top + p[1] * size * height) for p in points]
    for i, (a, b) in enumerate(LIMBS):
        if P[a] is None or P[b] is None:
            continue
        c = tuple(int(v * 0.6) for v in COLORS[i])
        d.line([P[a], P[b]], fill=c, width=max(4, size // 110))
    for i, p in enumerate(P):
        if p is not None:
            r = max(3, size // 160)
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=COLORS[i])
    return im


def all_poses():
    out = []
    for i, (n, f, h, l) in enumerate(WALK):
        out.append((f'walk_{i}', skeleton(n, f, h, l, 'walk', phase=i / 8 * 2 * math.pi), WALK_TEXT[i]))
    for i, (n, f, h, l, arms) in enumerate(JUMP):
        out.append((f'jump_{i}', skeleton(n, f, h, l, arms), JUMP_TEXT[i]))
    return out


if __name__ == '__main__':
    import sys
    from pathlib import Path
    dst = Path(sys.argv[1] if len(sys.argv) > 1 else 'pose_preview')
    dst.mkdir(parents=True, exist_ok=True)
    poses = all_poses()
    thumbs = [draw(p, 256) for _, p, _ in poses]
    sheet = Image.new('RGB', (256 * 8, 256 * 2))
    for i, t in enumerate(thumbs[:8]):
        sheet.paste(t, (i * 256, 0))
    for i, t in enumerate(thumbs[8:]):
        sheet.paste(t, (i * 256, 256))
    sheet.save(dst / 'poses.png')
    print('saved', dst / 'poses.png')
