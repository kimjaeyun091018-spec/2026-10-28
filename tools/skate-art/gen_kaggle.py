# Kaggle GPU에서 실행: 스케이트 시제품(skate.html) 야외 도트 그림 생성 (SDXL + 픽셀아트 LoRA)
# 올리기: python tools/skate-art/push.py   받기·도트화: python tools/skate-art/process.py <받은 폴더>
import subprocess, sys, time, json
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'diffusers', 'peft', 'accelerate'], check=False)
import torch, torch.nn.functional as F
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
t0 = time.time()
vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)
pipe = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', vae=vae,
    torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
pipe.load_lora_weights('nerijs/pixel-art-xl', weight_name='pixel-art-xl.safetensors')
pipe.to('cuda')
print('loaded', round(time.time() - t0), flush=True)

def tile_x(on):
    """합성곱 패딩: 가로는 순환(왼쪽 끝과 오른쪽 끝이 이어짐), 세로는 보통"""
    for model in (pipe.unet, pipe.vae):
        for m in model.modules():
            if isinstance(m, torch.nn.Conv2d) and m.padding != (0, 0) and not isinstance(m.padding, str):
                if on:
                    py, px = m.padding
                    def fwd(x, m=m, px=px, py=py):
                        x = F.pad(x, (px, px, 0, 0), mode='circular')
                        x = F.pad(x, (0, 0, py, py), mode='constant')
                        return F.conv2d(x, m.weight, m.bias, m.stride, 0, m.dilation, m.groups)
                    m.forward = fwd
                elif 'forward' in m.__dict__:
                    del m.forward

# 스케이트 시제품(skate.html) 야외 그림 — 모두 Kaggle에서 생성
#  1) 먼 하늘 sk_sky: 위로 높이 날 수 있게 세로로 긴 밤하늘 + 먼 도시 (가로로 이어짐)
#  2) 중간 거리 sk_mid: 무너진 빌딩·고가도로 실루엣. 단색 하늘에 그려 나중에 하늘을 뺌 (가로로 이어짐)
#  3) 땅 단면 sk_ground: 길 단면(아스팔트·흙·뿌리), 땅 채우기 무늬 (가로로 이어짐)
#  4) 소품(밝은 회색 배경, 나중에 배경을 빼고 도트로): 잎 날개 · 환풍기 · 큰 꽃 · 버려진 차 · 부러진 가로등 · 덩굴 난 간판 · 큰 잎 덤불
BG = ('pixel art, detailed 16-bit indie game background, flat side view, the whole image filled edge to edge, '
      'calm blue night, dim cold blue light with a few glowing neon accents in pink and cyan, deep blue and violet shadows, muted colors, '
      'crisp chunky pixels, rich hand placed detail, atmospheric perspective')
SCENES = {
    'sk_sky': ('night sky over a ruined futuristic city overgrown by giant plants, many layers of soft clouds lit by a big pale moon, '
               'tiny distant skyline of broken skyscrapers and giant trees along the very bottom edge, stars, no people, no readable text', 1536, 896),
    'sk_mid': ('silhouettes of ruined skyscrapers, a broken elevated highway and giant trees with hanging vines in the middle distance, '
               'all standing on the bottom edge, against a plain flat empty pale lavender sky that fills the whole upper half, no clouds, no moon, no people, no readable text', 1536, 768),
    'sk_ground': ('cross section of the ground under a ruined city street seen from the side, cracked dark asphalt layer on top, '
                  'below it dark soil full of tangled plant roots, buried pipes and rubble, fills the whole image, no sky, no people, no readable text', 1536, 512),
}
NEG_BG = 'blurry, 3d render, photo, smooth gradient, text, letters, watermark, signature, people, person, character, frame, border'
PROP = ('pixel art, 16-bit video game sprite, one single object, strict side view, centered, whole object visible, '
        'muted moody night palette with faint neon accents, crisp chunky pixels with dark outline, plain flat light gray background, no ground shadow, ')
PROPS = {
    'glider': 'a hand made hang glider wing built from a few giant green leaves and white dandelion seed fluff tied onto a thin rusty metal frame, with a handle bar hanging below, seen from the side, wide and flat',
    'fan': 'a big rusty industrial floor ventilation fan grate seen from the side, set in a concrete block, with faint steam rising, overgrown with moss',
    'flower': 'a giant bouncy carnivorous flower with a wide flat bright magenta bloom facing up, thick green stem and leaves',
    'car': 'an abandoned rusty futuristic hover car wreck overgrown with moss vines and small ferns, side view',
    'lamp': 'a broken bent futuristic street lamp post with a faintly glowing cyan lamp, wrapped in vines',
    'sign': 'a broken neon billboard frame on two posts, cracked panel glowing faint pink, overgrown with hanging vines, no readable text',
    'bush': 'a dense clump of huge dark tropical leaves and ferns',
}
NEG_PROP = 'multiple objects, scenery, landscape, floor, sky, blurry, smooth shading, 3d render, photo, text, letters, watermark, signature, frame, border, people, person, character'
meta = {}
def gen(name, prompt, neg, w, h, seeds, steps=30, cfg=7.0):
    meta[name] = {'prompt': prompt, 'negative': neg, 'size': [w, h], 'seeds': list(seeds)}
    for seed in seeds:
        g = torch.Generator('cuda').manual_seed(seed)
        im = pipe(prompt, negative_prompt=neg, num_inference_steps=steps, guidance_scale=cfg, width=w, height=h, generator=g).images[0]
        im.save(f'/kaggle/working/{name}_s{seed}.png')
        print('saved', name, seed, round(time.time() - t0), flush=True)
tile_x(True)
for name, (desc, w, h) in SCENES.items():
    gen(name, f'{BG}, {desc}', NEG_BG, w, h, (11, 22, 33))
tile_x(False)
for name, desc in PROPS.items():
    gen(name, PROP + desc, NEG_PROP, 1024, 1024, (4, 5))
json.dump(meta, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
