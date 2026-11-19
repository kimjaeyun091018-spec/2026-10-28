# Kaggle GPU에서 실행: 원통 탑 도트 그림 생성 (SDXL + 픽셀아트 LoRA)
#  1) 층별 벽 그림 — 가로로 이어지는(원통을 감싸도 이음새가 없는) 그림: 합성곱 패딩을 가로만 순환으로 바꿔 생성
#  2) 식물 스프라이트 — 덩굴 커튼·긴 풀 덤불·고사리·늘어진 뿌리 (밝은 회색 배경, 나중에 배경을 빼고 도트로 줄임)
#  3) 주인공 모스 시안 — 큰 머리·굵은 외곽선·따뜻한 음영의 요즘 인디 도트 화풍 (특정 게임 캐릭터를 따라 그리지 않음)
# push.py가 그대로 올림. 결과: /kaggle/working/<이름>_s<시드>.png, prompts.json
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

BG = ('pixel art, detailed 16-bit indie game background, flat side view of a wall seen straight on, '
      'dark night scene, dim warm lamp light, deep blue and violet shadows, warm amber and olive highlights, '
      'crisp chunky pixels, rich hand placed detail')
WALLS = {
    'wall_subway': 'interior wall of an abandoned underground subway station overgrown by plants, dirty white ceramic tiles, rusty pipes and cables running along the wall, faded torn posters, hanging ivy and moss, no people, no text',
    'wall_service': 'maintenance corridor wall in an abandoned metro tunnel, riveted metal panels, rusted pipes, electrical boxes, wooden crates and toolboxes against the wall, cables, creeping vines and moss, no people, no text',
    'wall_entrance': 'ground floor wall of a ruined subway tower, broken arched windows with pale moonlight, cracked concrete, thick tree roots and vines growing through the wall, tall wild grass at the bottom, no people, no text',
    'wall_station': 'far wall of an abandoned subway platform seen across the tracks, tiled wall with a long faded colored stripe, old benches and a dead vending machine, overgrown with vines and ferns, no people, no text',
}
NEG_BG = 'blurry, 3d render, photo, smooth gradient, text, letters, watermark, signature, people, person, character, vanishing point, perspective, frame, border'
SPR = ('pixel art, 16-bit game sprite, single object, full view, side view, plain flat light gray background, '
       'no ground, no shadow, crisp chunky pixels, dark outline, palette of olive green, moss green, dark teal and warm yellow green highlights')
PLANTS = {
    'vine_hang': ('a curtain of hanging ivy vines with many small leaves dangling from the top edge of the image, tapering to thin curling tips at the bottom', 768, 1280),
    'grass': ('a dense clump of tall wild grass and reeds with long thin swaying blades, yellow green and olive, a few seed heads', 1280, 768),
    'fern': ('a lush fern bush with many arching fronds', 1024, 1024),
    'roots': ('thick twisted tree roots and vines hanging down from the top edge of the image', 768, 1280),
}
NEG_SPR = '3d render, realistic photo, blurry, smooth shading, text, watermark, signature, frame, border, scenery, ground, pot, human, person, animal'
CHR = ('pixel art character sprite, detailed modern 16-bit indie game style, chunky cute proportions with a big head about one third of the body height, '
       'full body, side view facing right, standing, thick dark outline, warm cinematic shading, plain flat light gray background, no ground shadow')
HERO = ('a small young scavenger, rusty brown wide brimmed hat, teal gas mask with two round glowing green lenses and a filter canister, '
        'dark olive green patched long coat, heavy brown boots, holding a small terracotta pot with a little carnivorous sprout in one hand, '
        'a pruning sickle hanging on the belt')
NEG_CHR = '3d render, realistic photo, blurry, smooth shading, text, watermark, signature, multiple characters, cropped, frame, border, scenery, front view, back view'
meta = {}
def gen(name, prompt, neg, w, h, seeds, steps=30, cfg=7.0):
    meta[name] = {'prompt': prompt, 'negative': neg, 'size': [w, h], 'seeds': list(seeds)}
    for seed in seeds:
        g = torch.Generator('cuda').manual_seed(seed)
        im = pipe(prompt, negative_prompt=neg, num_inference_steps=steps, guidance_scale=cfg, width=w, height=h, generator=g).images[0]
        im.save(f'/kaggle/working/{name}_s{seed}.png')
        print('saved', name, seed, round(time.time() - t0), flush=True)
tile_x(True)
for name, desc in WALLS.items():
    gen(name, f'{BG}, {desc}', NEG_BG, 1536, 640, (11, 22))
tile_x(False)
for name, (desc, w, h) in PLANTS.items():
    gen(name, f'{SPR}, {desc}', NEG_SPR, w, h, (3, 4, 5) if name in ('vine_hang', 'grass') else (3, 4))
gen('hero', f'{CHR}, {HERO}', NEG_CHR, 1024, 1024, (101, 202, 303, 404, 505, 606))
json.dump(meta, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
