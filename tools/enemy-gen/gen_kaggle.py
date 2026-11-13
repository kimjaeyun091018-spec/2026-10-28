# Kaggle GPU에서 실행: 적 디자인 시안 생성 (2차: 꽃 포탑만. 1차는 덩굴 뭉치·꽃·가시덤불, 결과 assets/enemies/gen) (SDXL + 픽셀아트 LoRA, 주인공과 같은 화풍)
# 쓴 프롬프트: 1차(덩굴 뭉치 blob_s202 채택) assets/enemies/gen/prompts_run1.json, 2차(꽃 포탑 flower_s101 채택) prompts_run2.json
# push.py가 그대로 올림. 결과: /kaggle/working/<적>_s<시드>.png, prompts.json
import subprocess, sys, time, json
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'diffusers', 'peft', 'accelerate'], check=False)
import torch
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
t0 = time.time()
vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)
pipe = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', vae=vae,
    torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
pipe.load_lora_weights('nerijs/pixel-art-xl', weight_name='pixel-art-xl.safetensors')
pipe.to('cuda')
print('loaded', round(time.time() - t0), flush=True)

STYLE = ('pixel art, 16-bit video game sprite, single object, full view, strict side view facing left, '
         'muted earthy palette of olive green, moss green, dark brown, charcoal and dull crimson, '
         'crisp chunky pixels with dark outline, plain flat light gray background, no ground, no shadow, no text')
ENEMIES = {
    # 씨앗을 쏘는 적: 꽃 포탑 (생물 몸이 아닌 식물 자체로 묘사해야 사람 모양으로 안 그림)
    'flower': ('a tall carnivorous plant like a giant venus flytrap growing out of a pile of cracked concrete rubble, '
               'one long curved thick green stem bending to the left, a big flytrap head with dark crimson inside '
               'and pale spiky teeth along the edges, mouth slightly open, two broad leaves on the stem, '
               'plant only, no eyes, no face, no arms, no legs'),
}
NEG = ('3d render, realistic photo, blurry, smooth shading, text, watermark, signature, multiple plants, '
       'cropped, frame, border, scenery, human, person, hat, humanoid, creature, monster body, arms, legs, eyes, face')
meta = {}
for name, desc in ENEMIES.items():
    prompt = f'{STYLE}, {desc}'
    meta[name] = prompt
    w, h = (1024, 1024) if name != 'thorns' else (1344, 768)
    for seed in (101, 202, 303, 404, 505, 606):
        g = torch.Generator('cuda').manual_seed(seed)
        im = pipe(prompt, negative_prompt=NEG, num_inference_steps=30, guidance_scale=7.0, width=w, height=h, generator=g).images[0]
        im.save(f'/kaggle/working/{name}_s{seed}.png')
        print('saved', name, seed, round(time.time() - t0), flush=True)
json.dump({'negative': NEG, 'prompts': meta}, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
