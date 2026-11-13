"""gen_kaggle.py에 poses.py와 참고 그림을 끼워 넣어 Kaggle에 올리고 GPU로 실행한다.

사용:  python push.py <참고그림.png> [--only jump] [--seeds 1,2,3] [--cn 1.3] [--ip 0.35] [--slug 사용자/노트북]
인증:  Kaggle API (사용자 이름 + 키, Basic 인증). 클라우드 세션에서는 프록시가 넣어 줌.
결과:  Kaggle 노트북 Output에 프레임별 PNG(걷기 8, 점프 6, 시드 2개씩)와 prompts.json
"""
import base64
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
import argparse
ap = argparse.ArgumentParser()
ap.add_argument('ref')
ap.add_argument('--slug', default='yuzen3220/plant-hero-pose')
ap.add_argument('--only', default='', help="'walk' 또는 'jump'만 생성")
ap.add_argument('--seeds', default='1234,5678')
ap.add_argument('--cn', type=float, default=0.95, help='포즈를 따르는 강도')
ap.add_argument('--ip', type=float, default=0.55, help='참고 그림을 닮게 하는 강도')
args = ap.parse_args()
ref_path, slug = args.ref, args.slug

buf = io.BytesIO()
Image.open(ref_path).convert('RGB').save(buf, 'PNG')
src = (HERE / 'gen_kaggle.py').read_text()
src = src.replace('__POSES_B64__', base64.b64encode((HERE / 'poses.py').read_bytes()).decode())
src = src.replace('__REF_B64__', base64.b64encode(buf.getvalue()).decode())
src = src.replace('__ONLY__', args.only).replace('__SEEDS__', '[' + args.seeds + ']')
src = src.replace('__CN__', str(args.cn)).replace('__IP__', str(args.ip))

body = {'slug': slug, 'newTitle': slug.split('/')[1], 'text': src, 'language': 'python', 'kernelType': 'script',
        'isPrivate': True, 'enableGpu': True, 'enableInternet': True, 'datasetDataSources': [],
        'competitionDataSources': [], 'kernelDataSources': [], 'categoryIds': [], 'machineShape': 'NvidiaTeslaT4'}
user = os.environ.get('KAGGLE_USERNAME', 'x')
key = os.environ.get('KAGGLE_KEY', 'proxy-injected')
req = urllib.request.Request('https://www.kaggle.com/api/v1/kernels/push', data=json.dumps(body).encode(), method='POST',
                             headers={'Content-Type': 'application/json',
                                      'Authorization': 'Basic ' + base64.b64encode(f'{user}:{key}'.encode()).decode()})
r = json.loads(urllib.request.urlopen(req, timeout=120).read())
print(r.get('url'), 'version', r.get('versionNumber'), r.get('error') or '')
