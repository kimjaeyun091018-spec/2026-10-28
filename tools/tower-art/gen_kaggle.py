# Kaggle GPU에서 실행: 원통 탑 도트 그림 생성 (SDXL + 픽셀아트 LoRA)
# 2차(지금 내용): 무너진 미래 도시 벽 4종 · 자기부상 열차 옆면 · 잠수부 헬멧 주인공 시안. 1차(벽돌 지하철·덩굴·풀·고사리·첫 주인공 시안)는 assets/tower/prompts.json
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

BG = ('pixel art, detailed 16-bit indie game background, flat side view of a wall seen straight on, the whole image filled edge to edge, '
      'dark night scene, dim cold blue light with a few glowing neon accents in pink and cyan, deep blue and violet shadows, muted colors, '
      'crisp chunky pixels, rich hand placed detail')
WALLS = {   # 무너진 미래 도시 + 식물 아포칼립스
    'neo_entrance': 'ground floor wall of a ruined futuristic skyscraper metro tower, shattered glass panels, broken holographic billboard frames, dead neon tube signs, steel beams, giant tree roots and vines bursting through the wall, tall wild grass at the bottom, no people, no readable text',
    'neo_service': 'maintenance level wall inside a ruined futuristic metro tower, sleek metal panels and hexagonal vents, thick bundles of cables, broken server racks and glowing status lights, pipes, creeping vines and moss covering everything, no people, no readable text',
    'neo_subway': 'interior wall of an abandoned futuristic underground metro concourse, smooth white composite panels cracked open, dead neon line maps, broken advertising screens, emergency lights, thick roots and hanging ivy, no people, no readable text',
    'neo_station': 'far wall of an abandoned futuristic maglev subway platform, sleek curved panels with a faded glowing stripe, broken digital timetable screens, overgrown with vines ferns and roots, no people, no readable text',
}
NEG_BG = 'blurry, 3d render, photo, smooth gradient, text, letters, watermark, signature, people, person, character, vanishing point, perspective, frame, border, empty background, plain gray background'
SPR = ('pixel art, 16-bit game sprite, single object, full view, strict side view, plain flat light gray background, '
       'no ground, no shadow, crisp chunky pixels, dark outline, muted palette')
NEG_SPR = '3d render, realistic photo, blurry, smooth shading, text, watermark, signature, frame, border, scenery, ground, people, person'
TRAIN = 'a long sleek futuristic maglev subway train car seen exactly from the side, rounded aerodynamic body, long dark window band, abandoned and dirty, overgrown with moss and hanging vines, one cracked window, faded cyan stripe'
CHR = ('pixel art character sprite, detailed modern 16-bit indie metroidvania style, small slim character about three heads tall with a big head, '
       'full body, strict side view facing right, standing, thick dark outline, muted moody palette, plain flat light gray background, no ground shadow')
HERO = ('a lone survivor wearing a big round old brass deep sea diving helmet with one round glass porthole glowing faint green and rivets, '
        'a breathing hose from the helmet to a small tank on the back, long tattered dark teal raincoat flowing behind, thin legs, heavy boots, '
        'carrying a small glass pot with a little carnivorous sprout')
NEG_CHR = '3d render, realistic photo, blurry, smooth shading, text, watermark, signature, multiple characters, character sheet, cropped, frame, border, scenery, front view, back view, chibi, fat'
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
    gen('wall_' + name, f'{BG}, {desc}', NEG_BG, 1536, 640, (11, 22, 33))
tile_x(False)
gen('train', f'{SPR}, {TRAIN}', NEG_SPR, 1536, 512, (7, 8, 9))
gen('hero', f'{CHR}, {HERO}', NEG_CHR, 1024, 1024, (101, 202, 303, 404, 505, 606, 707, 808))
json.dump(meta, open('/kaggle/working/prompts.json', 'w'), indent=1)
print('done', round(time.time() - t0))
