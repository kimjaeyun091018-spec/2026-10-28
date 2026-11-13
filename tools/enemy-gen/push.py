"""gen_kaggle.py를 Kaggle에 올려 GPU로 실행한다.  사용: python push.py [사용자/노트북]"""
import base64, json, os, sys, urllib.request
from pathlib import Path
slug = sys.argv[1] if len(sys.argv) > 1 else 'yuzen3220/plant-enemy-gen'
src = (Path(__file__).resolve().parent / 'gen_kaggle.py').read_text()
body = {'slug': slug, 'newTitle': slug.split('/')[1], 'text': src, 'language': 'python', 'kernelType': 'script',
        'isPrivate': True, 'enableGpu': True, 'enableInternet': True, 'datasetDataSources': [],
        'competitionDataSources': [], 'kernelDataSources': [], 'categoryIds': [], 'machineShape': 'NvidiaTeslaT4'}
auth = base64.b64encode(f"{os.environ.get('KAGGLE_USERNAME', 'x')}:{os.environ.get('KAGGLE_KEY', 'proxy-injected')}".encode()).decode()
req = urllib.request.Request('https://www.kaggle.com/api/v1/kernels/push', data=json.dumps(body).encode(), method='POST',
                             headers={'Content-Type': 'application/json', 'Authorization': 'Basic ' + auth})
r = json.loads(urllib.request.urlopen(req, timeout=120).read())
print(r.get('url'), 'version', r.get('versionNumber'), r.get('error') or '')
