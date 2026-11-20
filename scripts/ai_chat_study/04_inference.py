"""4단계 — 추론: 토큰열을 넣으면 '다음 토큰 확률표'가 나온다. 하나 고르고 붙이기를 되풀이하면 글이 된다."""

import mlx.core as mx
from mlx_lm import load

from common import BASE

model, tokenizer = load(BASE)
ids = tokenizer.encode("The capital of France is", add_special_tokens=False)


def next_token_table(token_ids):
    logits = model(mx.array([token_ids]))[0, -1]  # 마지막 자리의 점수, 어휘 크기만큼
    return mx.softmax(logits)  # 점수 -> 합이 1 인 확률


probabilities = next_token_table(ids)
print(f"어휘 {probabilities.shape[0]:,}개 가운데 다음 토큰 상위 5개")
for token in mx.argsort(probabilities)[-5:].tolist()[::-1]:
    print(f"  {tokenizer.decode([token])!r:12} {probabilities[token].item():.3f}")

print("\n가장 확률 높은 토큰을 골라 붙이기를 6번")
for _ in range(6):
    probabilities = next_token_table(ids)
    token = mx.argmax(probabilities).item()
    ids.append(token)
    print(f"  + {tokenizer.decode([token])!r:12} {probabilities[token].item():.3f}")
print(tokenizer.decode(ids))
