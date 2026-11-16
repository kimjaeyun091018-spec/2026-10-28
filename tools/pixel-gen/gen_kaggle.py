# Kaggle GPU에서 실행: 도트(픽셀아트) 배경·땅 질감 생성 (SDXL base + 픽셀아트 LoRA, plant-world-action과 같은 방식)
# push.py가 그대로 올림. 결과: /kaggle/working/<이름>_s<시드>.png, prompts.json
# 받은 뒤 tools/pixel-gen/to_pixel.py로 도트 격자에 맞춰 줄임
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

STYLE = ('pixel art, 16-bit video game, crisp chunky pixels, limited palette, '
         'mysterious and dreamy atmosphere, soft glowing light')
ITEMS = {
    # 먼 배경: 옆에서 본 숲 / 냇가 (2D 플랫포머 배경, 아래쪽은 비교적 비워 둠)
    'bg_forest': ((1344, 768), 4, f'{STYLE}, side view parallax background for a 2d platformer, ancient forest with '
                  'huge mossy tree trunks, ferns, glowing fireflies, light rays through mist, deep green and teal, '
                  'empty ground area at the bottom, no characters'),
    'bg_river': ((1344, 768), 4, f'{STYLE}, side view parallax background for a 2d platformer, quiet forest stream '
                 'with smooth stones and reeds, distant misty trees, golden evening light, sparkles on the water, '
                 'empty ground area at the bottom, no characters'),
    # 땅 질감 (가득 채운 무늬, 받은 뒤 도트로 줄여 반복해 씀)
    'tex_soil': ((1024, 1024), 2, 'pixel art, 16-bit game tile texture, dark brown earth with small stones and '
                 'roots, seamless pattern, flat lighting, fills the whole frame, top-down'),
    'tex_moss': ((1024, 1024), 2, 'pixel art, 16-bit game tile texture, green grass and moss, seamless pattern, '
                 'flat lighting, fills the whole frame, top-down'),
    'tex_wood': ((1024, 1024), 2, 'pixel art, 16-bit game tile texture, old wooden planks, horizontal boards, '
                 'seamless pattern, flat lighting, fills the whole frame'),
}
NEG = ('3d render, realistic photo, blurry, smooth shading, text, watermark, signature, frame, border, '
       'people, person, character, animal, ui')
meta = {}
for name, ((w, h), n, prompt) in ITEMS.items():
    meta[name] = prompt
    for seed in (11, 22, 33, 44)[:n]:
        g = torch.Generator('cuda').manual_seed(seed)
        im = pipe(prompt, negative_prompt=NEG, num_inference_steps=30, guidance_scale=7.0, width=w, height=h,
                  generator=g).images[0]
        im.save(f'/kaggle/working/{name}_s{seed}.png')
        print('saved', name, seed, round(time.time() - t0), flush=True)
json.dump({'negative': NEG, 'prompts': meta}, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
