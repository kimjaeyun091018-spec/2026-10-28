# Kaggle GPU에서 실행: 작은 주인공(키 약 22px 비율) 시안 생성 — 디자인 2가지 × 그림체 2가지 × 시드 4개
# (1차 프롬프트는 assets/hero2/gen/prompts_run1.json, 이 파일은 2차)
# A: 지금 주인공(방독면 식물 사냥꾼)을 작고 귀여운 비율로 (IP-Adapter로 지금 캐릭터를 참고)
# B: 새 주인공 (도토리 껍질 투구에 새싹, 큰 잎사귀 망토, 가지치기 낫)
# 그림체: pixel(픽셀아트 LoRA) / hand(손그림, LoRA 끔)
# push.py가 참고 그림을 끼워 넣어 올림. 결과: /kaggle/working/<디자인>_<그림체>_s<시드>.png, prompts.json
import subprocess, sys, io, base64, time, json
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'diffusers', 'peft', 'accelerate', 'transformers'], check=False)
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
from transformers import CLIPVisionModelWithProjection

REF = Image.open(io.BytesIO(base64.b64decode('__REF_B64__'))).convert('RGB')
t0 = time.time()
vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)
enc = CLIPVisionModelWithProjection.from_pretrained('h94/IP-Adapter', subfolder='models/image_encoder', torch_dtype=torch.float16)
pipe = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', vae=vae, image_encoder=enc,
    torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
pipe.load_ip_adapter('h94/IP-Adapter', subfolder='sdxl_models', weight_name='ip-adapter-plus_sdxl_vit-h.safetensors')
pipe.load_lora_weights('nerijs/pixel-art-xl', weight_name='pixel-art-xl.safetensors', adapter_name='pixel')
pipe.to('cuda')
print('loaded', round(time.time() - t0), flush=True)

# 2차: 1차(세 자세를 한 장에)에서 A 도트만 성공 → 한 장에 한 인물, 생김새를 직접 묘사해 다시 생성
SHEET = ('single character, full body from head to feet, side view facing right, standing, '
         'small cute chibi proportions about 2.5 heads tall, big head, tiny body, very clear readable silhouette, '
         'video game hero sprite, plain flat light gray background, no text')
DESIGNS = {
    'A': ('a tiny plant hunter wearing an oversized brown wide-brim hat, a black gas mask with one big round glowing cyan-green lens, '
          'a small dark olive green tattered trench coat, brown boots, holding a little terracotta flower pot with a sprouting plant'),
    'B': ('a tiny round creature wearing a big brown acorn cap as a helmet, a small green leaf sprout growing on top of the cap, '
          'a dark shadowy face with two glowing green dot eyes, its body wrapped in one big dark green leaf like a cloak, '
          'tiny thin legs, holding a small curved sickle, original creature design, not a human'),
}
STYLES = {
    'pixel': 'pixel art, 16-bit sprite, crisp chunky pixels with dark outline, muted earthy palette',
    'hand': ('2D cartoon game sprite, hand-drawn, thick clean black outlines, flat colors, simple cel shading, '
             'muted earthy palette, smooth lines, vector-like, not pixel art'),
}
RUNS = [('A', 'hand', 0.2), ('B', 'pixel', 0.0), ('B', 'hand', 0.0)]
NEG = ('3d render, realistic photo, blurry, text, watermark, signature, multiple characters, two characters, extra limbs, '
       'cropped, frame, scenery, white mask, horns, human face, hair, adult, armor, muscular, tall')
meta = {}
for d, st, ip in RUNS:
    if st == 'pixel':
        pipe.enable_lora()
    else:
        pipe.disable_lora()
    pipe.set_ip_adapter_scale(ip)
    prompt = f'{STYLES[st]}, {SHEET}, {DESIGNS[d]}'
    meta[f'{d}_{st}'] = {'prompt': prompt, 'ip_adapter_scale': ip}
    for seed in (11, 22, 33, 44):
        g = torch.Generator('cuda').manual_seed(seed)
        im = pipe(prompt=prompt, negative_prompt=NEG, ip_adapter_image=REF, num_inference_steps=30, guidance_scale=7.0,
                  width=1024, height=1024, generator=g).images[0]
        im.save(f'/kaggle/working/{d}_{st}_s{seed}.png')
        print('saved', d, st, seed, round(time.time() - t0), flush=True)
json.dump({'negative': NEG, 'runs': meta}, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
