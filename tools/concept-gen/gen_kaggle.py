# Kaggle GPU에서 실행: 종이 세계 배경·캐릭터 시안 생성 (SDXL base)
# push.py가 그대로 올림. 결과: /kaggle/working/<이름>_s<시드>.png, prompts.json
import subprocess, sys, time, json
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'diffusers', 'accelerate'], check=False)
import torch
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
t0 = time.time()
vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)
pipe = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', vae=vae,
    torch_dtype=torch.float16, variant='fp16', use_safetensors=True).to('cuda')
print('loaded', round(time.time() - t0), flush=True)

STYLE = ('papercraft diorama, layered cut paper art, handmade origami paper texture, visible paper fibers, '
         'soft studio lighting, gentle drop shadows between paper layers, muted warm pastel palette, '
         'cream, sage green, dusty teal, terracotta, high detail')
ITEMS = {
    # 게임 배경: 옆에서 본 종이 숲 (가로로 긴 화면, 가운데 아래는 비워 캐릭터가 걸을 자리)
    'bg_forest': ((1344, 768), 'side view landscape for a 2d platformer game background, layered paper cut forest '
                  'with folded paper trees, paper hills receding into distance, paper clouds on strings, '
                  'flat ground strip along the bottom, empty foreground, no characters'),
    'bg_town': ((1344, 768), 'side view landscape for a 2d platformer game background, a small village of folded '
                'paper houses with paper roofs, paper lanterns, paper bridge, layered paper mountains behind, '
                'flat ground strip along the bottom, empty foreground, no characters'),
    # 캐릭터 시안: 종이로 접은 주인공
    'hero': ((1024, 1024), 'character concept art, a small cute hero folded entirely from a single sheet of '
             'cream origami paper, visible crease lines and folded facets, simple triangle head, tiny dot eyes, '
             'holding a folded paper sword, full body, front three-quarter view, plain light gray background'),
}
NEG = ('photo, realistic, 3d render plastic, blurry, text, watermark, signature, logo, frame, border, '
       'people, human, hands, lowres, jpeg artifacts')
meta = {}
for name, ((w, h), desc) in ITEMS.items():
    prompt = f'{STYLE}, {desc}'
    meta[name] = prompt
    for seed in (11, 22, 33, 44):
        g = torch.Generator('cuda').manual_seed(seed)
        im = pipe(prompt, negative_prompt=NEG, num_inference_steps=30, guidance_scale=6.5, width=w, height=h,
                  generator=g).images[0]
        im.save(f'/kaggle/working/{name}_s{seed}.png')
        print('saved', name, seed, round(time.time() - t0), flush=True)
json.dump({'negative': NEG, 'prompts': meta}, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
