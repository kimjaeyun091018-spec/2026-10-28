---
title: 뿌리 아래로 배경 생성기
emoji: 🌿
colorFrom: green
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
license: apache-2.0
---

# 뿌리 아래로 · 배경 생성기

식물이 지배하는 세계 게임(`plant-world-action` 브랜치)의 구역 배경을 도트 그림으로 만드는 허깅페이스 Space입니다.

## 올리는 방법

1. [huggingface.co](https://huggingface.co)에 가입하고 이메일 인증. **가입 30일이 지나야** 무료 계정으로 ZeroGPU Space를 만들 수 있어요.
2. 오른쪽 위 **New → Space**
   - SDK: **Gradio**
   - Hardware: **ZeroGPU**
   - 공개 여부는 자유 (Private이어도 됨)
3. 만들어진 Space의 **Files → Add file → Upload files**로 이 폴더의 `app.py`, `requirements.txt`, `README.md` 세 개를 올리기
4. 처음 켜질 때 모델(약 30GB)을 받느라 몇 분 걸려요. "Running"이 뜨면 사용

## 사용량

- ZeroGPU 사용 시간은 **쓰는 사람의 하루 할당량**에서 빠져요. 무료 계정 하루 5분, PRO 40분.
- 기본 모델 FLUX.1 [schnell]은 1장에 몇 초라서 무료로도 하루 수십 장 정도 만들 수 있어요.
- 진짜 무제한은 그래픽카드가 있는 내 컴퓨터에서 돌리는 것뿐이에요.

## 내 화풍 LoRA 붙이기 (나중에)

LoRA를 학습해서 허깅페이스 모델 저장소에 올린 뒤, Space의 **Settings → Variables and secrets**에서:

| 이름 | 종류 | 값 |
|---|---|---|
| `LORA_REPO` | Variable | LoRA 저장소 이름 (예: `내아이디/plant-world-lora`) |
| `LORA_TRIGGER` | Variable | 학습 때 쓴 트리거 단어 |
| `BASE_MODEL` | Variable | (선택) `black-forest-labs/FLUX.1-dev`. Replicate의 FLUX 학습기로 만든 LoRA는 dev에서 가장 잘 맞음 |
| `HF_TOKEN` | **Secret** | dev 모델이나 비공개 LoRA를 쓸 때만. dev는 모델 페이지에서 라이선스 동의 필요 |

설정을 바꾸면 Space가 다시 시작돼요.

## 라이선스 주의

- FLUX.1 [schnell]: Apache 2.0, 상업적 사용 가능
- FLUX.1 [dev]: 비상업 라이선스. 게임을 팔 생각이면 dev로 만든 결과물을 쓰기 전에 라이선스를 확인하세요.
