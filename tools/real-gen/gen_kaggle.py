# Kaggle GPU에서 실행: 사실적인 배경·땅 질감 생성 (RealVisXL, 안 되면 SDXL base)
# 종이 주인공이 '진짜 세상'을 걷는 느낌을 내기 위한 그림. push.py가 그대로 올림.
# 결과: /kaggle/working/<이름>_s<시드>.png, prompts.json
import subprocess, sys, time, json
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'diffusers', 'accelerate'], check=False)
import torch
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
t0 = time.time()
model = 'SG161222/RealVisXL_V4.0'
try:
    pipe = StableDiffusionXLPipeline.from_pretrained(model, torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
except Exception as e:
    print('RealVisXL 실패, SDXL base로', e, flush=True); model = 'stabilityai/stable-diffusion-xl-base-1.0'
    vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)
    pipe = StableDiffusionXLPipeline.from_pretrained(model, vae=vae, torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
pipe.to('cuda')
print('loaded', model, round(time.time() - t0), flush=True)

PHOTO = 'realistic photograph, highly detailed, natural colors, sharp focus'
ITEMS = {
    # 먼 배경: 옆에서 본 숲 (게임 화면 뒤, 가운데 아래는 비교적 비어 있게)
    'bg_forest': ((1344, 768), 4, f'{PHOTO}, wide side view of a sunlit forest, tall tree trunks, ferns and moss, '
                  'distant trees fading into soft haze, warm afternoon light rays, eye level, cinematic, no people'),
    'bg_river': ((1344, 768), 4, f'{PHOTO}, wide side view of a calm forest stream bank, smooth rocks, reeds, '
                 'trees in the background with soft haze, warm afternoon light, eye level, cinematic, no people'),
    # 땅 질감 (옆에서 본 단면, 가로로 이어 붙여 씀)
    'tex_soil': ((1024, 1024), 2, f'{PHOTO}, seamless texture, cross-section of earth, dark brown soil with small '
                 'pebbles and thin roots, flat even lighting, no shadows, fills the whole frame'),
    'tex_moss': ((1024, 1024), 2, f'{PHOTO}, seamless texture, dense green moss and tiny grass seen from above, '
                 'flat even lighting, fills the whole frame'),
    'tex_wood': ((1024, 1024), 2, f'{PHOTO}, seamless texture, weathered old wooden plank, horizontal grain, '
                 'flat even lighting, fills the whole frame'),
}
NEG = ('painting, illustration, cartoon, anime, 3d render, cgi, text, watermark, logo, signature, frame, border, '
       'people, person, animal, blurry, lowres, oversaturated')
meta = {'model': model}
for name, ((w, h), n, prompt) in ITEMS.items():
    meta[name] = prompt
    for seed in (11, 22, 33, 44)[:n]:
        g = torch.Generator('cuda').manual_seed(seed)
        im = pipe(prompt, negative_prompt=NEG, num_inference_steps=30, guidance_scale=5.5, width=w, height=h,
                  generator=g).images[0]
        im.save(f'/kaggle/working/{name}_s{seed}.png')
        print('saved', name, seed, round(time.time() - t0), flush=True)
json.dump({'negative': NEG, 'prompts': meta}, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
