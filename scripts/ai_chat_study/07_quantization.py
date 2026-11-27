"""7단계 — 양자화: 숫자를 적은 비트로 줄여 적는다. 64개씩 묶어 묶음마다 기준값과 간격을 따로 둔다."""

import json
import struct

import numpy as np

from common import ROOT

rng = np.random.default_rng(7)
weights = rng.normal(0, 0.02, 1024 * 1024).astype(np.float32)


def quantize(values, bits, group=64):
    groups = values.reshape(-1, group)
    low = groups.min(axis=1, keepdims=True)
    step = (groups.max(axis=1, keepdims=True) - low) / (2**bits - 1)
    codes = np.round((groups - low) / step)  # 저장하는 것은 0 … 2^bits-1 의 정수뿐
    return (codes * step + low).reshape(values.shape)  # 쓸 때 다시 실수로 편다


print("비트  가중치당 저장 비트  평균 오차(가중치 크기 대비)")
for bits in (8, 6, 4, 2):
    restored = quantize(weights, bits)
    error = np.abs(restored - weights).mean() / np.abs(weights).mean()
    stored = bits + 2 * 16 / 64  # 묶음(64개)마다 16비트 숫자 둘: 기준값·간격
    print(f"{bits:3d}  {stored:14.2f}  {error:10.2%}")

# 실제 4비트 모델 파일의 한 층이 어떻게 저장돼 있는지 머리말만 읽는다
model_file = ROOT / "scripts/ai_chat_train/runs/base/Qwen3-0.6B-4bit-public/model.safetensors"
if model_file.exists():
    with model_file.open("rb") as file:
        header = json.loads(file.read(struct.unpack("<Q", file.read(8))[0]))
    print("\n실제 파일의 k_proj (원래 1024 x 1024 표)")
    for name, entry in header.items():
        if "layers.0.self_attn.k_proj" in name:
            print(f"  {name.split('.')[-1]:8} {entry['dtype']:5} {entry['shape']}")
    print("  weight: 1024줄 x 128칸 x 32비트 = 줄마다 4,096비트 = 가중치 1,024개 x 4비트")
    base = ROOT / "scripts/ai_chat_train/runs/base"
    for folder in ("Qwen3-0.6B-bf16", "Qwen3-0.6B-4bit-public"):
        path = base / folder / "model.safetensors"
        if path.exists():
            print(f"  {folder:24} {path.stat().st_size / 1e6:7.0f} MB")
else:
    print("\n(받아 둔 모델 폴더가 없어 실제 파일 확인은 건너뛴다)")
