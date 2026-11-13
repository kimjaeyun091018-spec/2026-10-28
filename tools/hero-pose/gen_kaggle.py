# Kaggle GPU에서 실행: 고른 주인공의 걷기 8 · 점프 6 프레임 생성
# SDXL + 픽셀아트 LoRA + ControlNet OpenPose(프레임별 관절 포즈) + IP-Adapter(주인공 참고 그림)
# 이 파일은 그대로 올리지 않고, push.py가 poses.py 내용과 참고 그림을 끼워 넣어 올린다.
import subprocess, sys, io, base64, time, json
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'diffusers', 'peft', 'accelerate', 'transformers'], check=False)

import torch
from PIL import Image
from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel, AutoencoderKL
from transformers import CLIPVisionModelWithProjection

POSES_SRC = base64.b64decode('__POSES_B64__').decode()
ns = {'__name__': 'poses'}
exec(POSES_SRC, ns)
REF = Image.open(io.BytesIO(base64.b64decode('__REF_B64__'))).convert('RGB')

t0 = time.time()
log = lambda *a: print(round(time.time() - t0), *a, flush=True)
vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)
cn = ControlNetModel.from_pretrained('xinsir/controlnet-openpose-sdxl-1.0', torch_dtype=torch.float16)
enc = CLIPVisionModelWithProjection.from_pretrained('h94/IP-Adapter', subfolder='models/image_encoder', torch_dtype=torch.float16)
pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
    'stabilityai/stable-diffusion-xl-base-1.0', controlnet=cn, vae=vae, image_encoder=enc,
    torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
pipe.load_ip_adapter('h94/IP-Adapter', subfolder='sdxl_models', weight_name='ip-adapter-plus_sdxl_vit-h.safetensors')
pipe.load_lora_weights('nerijs/pixel-art-xl', weight_name='pixel-art-xl.safetensors', adapter_name='pixel')
pipe.to('cuda')
log('loaded on', torch.cuda.get_device_name(0))

# 주인공 묘사 (모든 프레임 공통). 참고 그림과 같은 인물이 되도록 생김새를 하나하나 적음
CHARACTER = (
    'pixel art, 16-bit video game sprite, one single character, full body from hat to boots, '
    'strict side view profile facing right, '
    'a lean plant hunter wearing a brown wide-brim fedora hat with a darker band, '
    'a black gas mask with one large round glowing cyan-green lens and bright green glowing tubes running down the chest, '
    'a long dark olive green tattered trench coat that reaches below the knees with ragged hem, '
    'a brown leather belt with small pouches, dark green trousers, tall brown leather lace-up boots, '
    'holding a small terracotta flower pot with a leafy green plant and an orange flower in the near hand at chest height, '
    'a woven brown wicker basket full of green herbs hanging from the far hand, '
    'muted earthy palette of olive green, brown and dark charcoal, crisp chunky pixels with dark outline, '
    'plain flat light gray background, no ground shadow')
NEG = ('front view, facing the viewer, three-quarter view, back view, multiple characters, two people, duplicate, '
       'extra legs, extra arms, missing legs, deformed hands, fused legs, blurry, smooth shading, 3d render, '
       'realistic photo, text, watermark, signature, frame, cropped feet, cut off hat, scenery, floor, grass')

# 실행 설정 (push.py 인자로 바꿀 수 있음)
ONLY = '__ONLY__'            # 'walk' / 'jump' / '' (전부)
SEEDS = __SEEDS__
CN_SCALE = __CN__
pipe.set_ip_adapter_scale(__IP__)
EXTRA = {'jump': ', dynamic action pose, the long coat flares up and back so the bent legs and boots are clearly visible'}
meta = []
for name, pts, action in ns['all_poses']():
    if ONLY and not name.startswith(ONLY):
        continue
    pose = ns['draw'](pts, 1024)
    pose.save(f'/kaggle/working/pose_{name}.png')
    prompt = f'{CHARACTER}, {action}' + EXTRA.get(name.split('_')[0], '')
    for seed in SEEDS:
        g = torch.Generator('cuda').manual_seed(seed)
        img = pipe(prompt=prompt, negative_prompt=NEG, image=pose, ip_adapter_image=REF,
                   controlnet_conditioning_scale=CN_SCALE, num_inference_steps=30, guidance_scale=6.5,
                   width=1024, height=1024, generator=g).images[0]
        img.save(f'/kaggle/working/{name}_s{seed}.png')
        log('saved', name, seed)
    meta.append({'name': name, 'prompt': prompt})
json.dump({'negative': NEG, 'seeds': SEEDS, 'frames': meta}, open('/kaggle/working/prompts.json', 'w'), ensure_ascii=False, indent=1)
log('done')
