"""뿌리 아래로 - 배경 생성기 (Hugging Face ZeroGPU Space)

식물이 지배하는 세계 게임의 챕터 배경을 도트 그림으로 만든다.
- 기본 모델: FLUX.1 [schnell] (Apache 2.0, 4단계라 빠름)
- 내 화풍 LoRA가 생기면 Space 설정의 Variables에 LORA_REPO를 넣으면 자동으로 씀
- 결과는 원본 크기와 게임 해상도(426x240) 두 가지로 받음
"""
import os
import random

import gradio as gr
import spaces
import torch
from diffusers import FluxPipeline
from PIL import Image

BASE_MODEL = os.environ.get("BASE_MODEL", "black-forest-labs/FLUX.1-schnell")
LORA_REPO = os.environ.get("LORA_REPO", "").strip()        # 예: 내아이디/plant-world-lora
LORA_TRIGGER = os.environ.get("LORA_TRIGGER", "").strip()  # LoRA 학습 때 쓴 트리거 단어
HF_TOKEN = os.environ.get("HF_TOKEN")                      # dev 모델이나 비공개 LoRA를 쓸 때만 필요
IS_SCHNELL = "schnell" in BASE_MODEL.lower()

GAME_W, GAME_H = 426, 240  # 게임에서 쓰는 배경 크기 (assets/ch1-bg.png와 같음)
MAX_SEED = 2**31 - 1

pipe = FluxPipeline.from_pretrained(BASE_MODEL, torch_dtype=torch.bfloat16, token=HF_TOKEN)
if LORA_REPO:
    pipe.load_lora_weights(LORA_REPO, token=HF_TOKEN)
pipe.to("cuda")

STYLE = (
    "pixel art, 16-bit side-scrolling game background, detailed environment, "
    "soft atmospheric lighting, lush overgrown plants, moss and hanging vines, "
    "post-apocalyptic city reclaimed by nature, no characters, no text"
)

CHAPTERS = {
    "1구역 이끼 덮인 지하철": "abandoned subway platform, old train covered in moss, broken benches, "
                         "hanging station sign, light shafts through a collapsed ceiling",
    "환기구 (세로 갱도)": "tall vertical ventilation shaft, rusted ladders and pipes wrapped in thick roots, "
                    "dim light from far above, dripping water",
    "2구역 가시덤불 도심": "ruined city street choked by giant thorny brambles, cracked skyscrapers, "
                      "red thorns, dusty orange sunset haze",
    "3구역 식충식물 온실": "giant collapsed glass greenhouse, huge carnivorous plants and pitcher plants, "
                      "humid blue-green fog, broken glass panes",
    "4구역 균류 동굴": "underground cave full of giant glowing mushrooms, bioluminescent spores, "
                  "old tunnel tiles, deep teal and purple light",
    "5구역 세계수 뿌리 핵": "colossal world tree roots forming a cathedral-like chamber, glowing sap veins, "
                       "golden light, ancient and sacred",
}

SIZES = {
    "16:9 가로 (1344x768)": (1344, 768),
    "21:9 넓게 (1536x640)": (1536, 640),
    "세로 갱도용 (768x1344)": (768, 1344),
}


def build_prompt(chapter, extra):
    parts = [LORA_TRIGGER] if LORA_TRIGGER else []
    parts += [CHAPTERS.get(chapter, ""), extra.strip(), STYLE]
    return ", ".join(p for p in parts if p)


def to_game_size(img, portrait):
    w, h = (GAME_H, GAME_W) if portrait else (GAME_W, GAME_H)
    # 비율이 다르면 가운데를 잘라 맞춘 뒤 BOX로 줄인다 (도트가 뭉개지지 않게)
    src_ratio, dst_ratio = img.width / img.height, w / h
    if src_ratio > dst_ratio:
        nw = round(img.height * dst_ratio)
        img = img.crop(((img.width - nw) // 2, 0, (img.width - nw) // 2 + nw, img.height))
    elif src_ratio < dst_ratio:
        nh = round(img.width / dst_ratio)
        img = img.crop((0, (img.height - nh) // 2, img.width, (img.height - nh) // 2 + nh))
    return img.resize((w, h), Image.BOX)


def gpu_time(chapter, extra, size, seed, randomize, lora_scale, progress=None):
    return 20 if IS_SCHNELL else 90


@spaces.GPU(duration=gpu_time)
def generate(chapter, extra, size, seed, randomize, lora_scale, progress=gr.Progress(track_tqdm=True)):
    if randomize:
        seed = random.randint(0, MAX_SEED)
    w, h = SIZES[size]
    kwargs = dict(
        prompt=build_prompt(chapter, extra),
        width=w,
        height=h,
        generator=torch.Generator("cuda").manual_seed(int(seed)),
    )
    if IS_SCHNELL:
        kwargs.update(num_inference_steps=4, guidance_scale=0.0, max_sequence_length=256)
    else:
        kwargs.update(num_inference_steps=28, guidance_scale=3.5)
    if LORA_REPO:
        kwargs["joint_attention_kwargs"] = {"scale": float(lora_scale)}
    img = pipe(**kwargs).images[0]
    game = to_game_size(img, portrait=h > w)
    return img, game, int(seed), kwargs["prompt"]


with gr.Blocks(title="뿌리 아래로 - 배경 생성기") as demo:
    gr.Markdown(
        "## 뿌리 아래로 · 배경 생성기\n"
        f"모델 `{BASE_MODEL}`" + (f" + LoRA `{LORA_REPO}`" if LORA_REPO else " (LoRA 없음)")
        + "\n\n같은 시드를 쓰면 같은 그림이 나와요. 마음에 드는 그림의 시드를 적어 두세요."
    )
    with gr.Row():
        with gr.Column(scale=1):
            chapter = gr.Dropdown(list(CHAPTERS), value=list(CHAPTERS)[0], label="구역")
            extra = gr.Textbox(label="추가 설명 (영어가 잘 먹혀요)", placeholder="e.g. rainy, lanterns, a broken escalator", lines=2)
            size = gr.Radio(list(SIZES), value=list(SIZES)[0], label="크기")
            with gr.Row():
                seed = gr.Number(value=0, precision=0, label="시드")
                randomize = gr.Checkbox(value=True, label="시드 무작위")
            lora_scale = gr.Slider(0.0, 1.5, value=1.0, step=0.05, label="LoRA 세기", visible=bool(LORA_REPO))
            btn = gr.Button("만들기", variant="primary")
        with gr.Column(scale=2):
            out = gr.Image(label="원본", format="png")
            game = gr.Image(label=f"게임용 ({GAME_W}x{GAME_H}) - 이걸 assets/에 넣으면 돼요", format="png")
            used_seed = gr.Number(label="쓴 시드", interactive=False)
            used_prompt = gr.Textbox(label="실제 프롬프트", interactive=False, lines=3)
    btn.click(generate, [chapter, extra, size, seed, randomize, lora_scale], [out, game, used_seed, used_prompt])

demo.queue().launch()
