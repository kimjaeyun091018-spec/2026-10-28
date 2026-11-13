"""gen_kaggle.py에 참고 그림(지금 주인공)을 끼워 Kaggle에 올리고 GPU로 실행.  사용: python push.py <참고그림.png> [사용자/노트북]"""
import base64, io, json, os, sys, urllib.request
from pathlib import Path
from PIL import Image
buf = io.BytesIO(); Image.open(sys.argv[1]).convert('RGB').save(buf, 'PNG')
slug = sys.argv[2] if len(sys.argv) > 2 else 'yuzen3220/plant-hero-small'
src = (Path(__file__).resolve().parent / 'gen_kaggle.py').read_text().replace('__REF_B64__', base64.b64encode(buf.getvalue()).decode())
body = {'slug': slug, 'newTitle': slug.split('/')[1], 'text': src, 'language': 'python', 'kernelType': 'script',
        'isPrivate': True, 'enableGpu': True, 'enableInternet': True, 'datasetDataSources': [],
        'competitionDataSources': [], 'kernelDataSources': [], 'categoryIds': [], 'machineShape': 'NvidiaTeslaT4'}
auth = base64.b64encode(f"{os.environ.get('KAGGLE_USERNAME', 'x')}:{os.environ.get('KAGGLE_KEY', 'proxy-injected')}".encode()).decode()
req = urllib.request.Request('https://www.kaggle.com/api/v1/kernels/push', data=json.dumps(body).encode(), method='POST',
                             headers={'Content-Type': 'application/json', 'Authorization': 'Basic ' + auth})
r = json.loads(urllib.request.urlopen(req, timeout=120).read())
print(r.get('url'), 'version', r.get('versionNumber'), r.get('error') or '')
