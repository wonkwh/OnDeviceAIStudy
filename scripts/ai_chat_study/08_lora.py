"""8단계 — LoRA: 원래 표 W 는 그대로 두고 얇은 표 A·B 만 학습한다. 끼웠다 뺄 수 있다."""

import json
import struct

import numpy as np
from mlx_lm import generate, load

from common import BASE, RESOURCES, ROOT, SYSTEM_PROMPT, adapter_dir, chat_prompt, swift_string

# (가) 식: y = x·W + scale × (x·A·B)
rng = np.random.default_rng(7)
x = rng.normal(size=(1, 1024))
W = rng.normal(0, 0.02, (1024, 1024))
A = rng.normal(0, 0.02, (1024, 8))
B = np.zeros((8, 1024))  # 학습은 B = 0 에서 시작한다
print("W", W.size, "개 / A+B", A.size + B.size, f"개 ({(A.size + B.size) / W.size:.1%})")
print("B 가 0 이면 출력이 원래와 같다:", np.allclose(x @ W, x @ W + 20 * (x @ A @ B)))
B = rng.normal(0, 0.02, (8, 1024))
print("B 를 채우면 달라진다:", not np.allclose(x @ W, x @ W + 20 * (x @ A @ B)))

# (나) 앱에 들어 있는 실제 어댑터
with (RESOURCES / "ai_chat_parser_adapter.safetensors").open("rb") as file:
    header = json.loads(file.read(struct.unpack("<Q", file.read(8))[0]))
tensors = {name: entry["shape"] for name, entry in header.items() if name != "__metadata__"}
total = sum(int(np.prod(shape)) for shape in tensors.values())
print(f"\n앱의 어댑터: 표 {len(tensors)}개(= {len(tensors) // 2}곳 x A·B), 가중치 {total:,}개")
print(" ", json.loads((RESOURCES / "ai_chat_parser_adapter.json").read_text()))

# (다) 끼웠을 때와 뺐을 때
parse_user = "today: 2026-11-16 (Mon) 14:00\nquestion: Show me the video from yesterday at 9:30 am"
guide_system = swift_string(
    ROOT / "Hub/Domain/UseCases/AIChat/HubGuidePrompt.swift", "instructions")
guide_user = (
    "guide:\n- Parking impact sensitivity: Sets how sensitive impact detection is while parked. "
    "Lowering it reduces parking event recordings caused by door slams or passing vehicles.\n"
    "protocol reference:\n\nquestion: How do I reduce parking recordings?")

for label, adapter in (("어댑터 뺌", None), ("어댑터 끼움", adapter_dir())):
    model, tokenizer = load(BASE, adapter_path=adapter)
    parsed = generate(
        model, tokenizer, prompt=chat_prompt(tokenizer, SYSTEM_PROMPT, parse_user), max_tokens=120)
    guided = generate(
        model, tokenizer, prompt=chat_prompt(tokenizer, guide_system, guide_user), max_tokens=80)
    print(f"\n[{label}]")
    print("  12칸 옮기기:", parsed.replace("\n", " ")[:230])
    print("  안내 문장  :", guided.split("</think>")[-1].strip().replace("\n", " ")[:230])
