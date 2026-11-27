# Kaggle GPU에서 실행: 얼음 바다 스케이트(ice.html) 야외 도트 그림 생성 (SDXL + 픽셀아트 LoRA)
# 올리기: python tools/ice-art/push.py   받기·도트화: python tools/ice-art/process.py <받은 폴더>
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

# 얼음 바다 스케이트(ice.html) 야외 그림
#  1) 먼 하늘 ice_sky: 위로 높이 날 수 있게 세로로 긴 극지의 밤하늘 + 수평선의 빙산 (가로로 이어짐)
#  2) 중간 거리 ice_mid: 빙산·얼어붙은 난파선·얼음 능선 실루엣. 단색 하늘에 그려 하늘을 뺌 (가로로 이어짐)
#  3) 얼음 단면 ice_ground: 두꺼운 바다 얼음 단면(푸른 층·기포) 아래 어두운 바닷물 (가로로 이어짐)
#  4) 소품(밝은 회색 배경 → 배경을 빼고 도트로)
BG = ('pixel art, detailed 16-bit indie game background, flat side view, the whole image filled edge to edge, '
      'calm polar night, cold deep blue and teal palette with soft pale highlights, faint green aurora light, muted colors, '
      'crisp chunky pixels, rich hand placed detail, atmospheric perspective')
SCENES = {
    'ice_sky': ('polar night sky over an endless frozen sea in a new ice age, wide soft green and violet aurora curtains, '
                'thin clouds, many stars, a small pale moon, a thin line of distant icebergs along the very bottom edge, no people, no readable text', 1536, 896),
    'ice_mid': ('silhouettes of huge icebergs, a giant cargo ship frozen and tilted in the sea ice, a frozen lighthouse and jagged ice pressure ridges in the middle distance, '
                'all standing on the bottom edge, against a plain flat empty pale lavender sky that fills the whole upper half, no clouds, no moon, no aurora, no people, no readable text', 1536, 768),
    'ice_ground': ('cross section of very thick sea ice seen from the side, a thin layer of snow on top, below it translucent layered blue ice full of trapped air bubbles and cracks, '
                   'getting darker toward the deep dark ocean water at the bottom, fills the whole image, no sky, no people, no readable text', 1536, 512),
}
NEG_BG = 'blurry, 3d render, photo, smooth gradient, text, letters, watermark, signature, people, person, character, frame, border, plants, trees, grass'
PROP = ('pixel art, 16-bit video game sprite, one single object, strict side view, centered, whole object visible, '
        'cold muted polar night palette, crisp chunky pixels with dark outline, plain flat light gray background, no ground shadow, ')
PROPS = {
    'kite': 'a hand made traction kite wing made of patched canvas and fur strips stretched on bent bone and wood sticks, arched like a parafoil, with lines going down to a handle bar, seen from the side, wide',
    'ship': 'the bow of an old rusty fishing ship frozen in ice, tilted up, covered in icicles and snow, railings and a broken mast',
    'barrel': 'a rusty metal fire barrel with a warm orange fire burning inside, sparks, standing on snow',
    'hut': 'a small ice fishing hut made of scrap metal and planks, snow on the roof, a stovepipe, a warm glowing window',
    'buoy': 'an old navigation buoy frozen in ice, tilted, covered in frost, a dim red lamp on top',
    'berg': 'a small jagged chunk of blue glacier ice with sharp edges and snow on top',
    'flag': 'a tall wooden pole with a tattered red cloth flag and a small lantern, frozen, marking a trail on the ice',
}
NEG_PROP = 'multiple objects, scenery, landscape, floor, sky, blurry, smooth shading, 3d render, photo, text, letters, watermark, signature, frame, border, people, person, character, plants'
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
