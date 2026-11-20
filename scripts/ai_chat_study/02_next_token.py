"""2단계 — 언어 모델은 '다음 낱말의 확률표'다.

평가셋 질문 112개로 가장 단순한 언어 모델(직전 낱말 하나만 보는 bigram)을 만든다.
"""

import json
import random
from collections import Counter, defaultdict

from common import ROOT

cases = json.loads((ROOT / "scripts/fixtures/ai_chat_eval_en.json").read_text())
counts = defaultdict(Counter)
for case in cases:
    words = ["<s>"] + case["q"].split() + ["</s>"]
    for previous, following in zip(words, words[1:]):
        counts[previous][following] += 1  # 이 모델의 '학습'은 세는 것이 전부다


def table(previous):
    """previous 다음에 올 낱말의 확률표."""
    total = sum(counts[previous].values())
    return {word: n / total for word, n in counts[previous].most_common()}


def generate(temperature, seed=0):
    rng, word, out = random.Random(seed), "<s>", []
    while len(out) < 15:
        probabilities = table(word)
        if temperature == 0:
            word = max(probabilities, key=probabilities.get)  # 확률이 가장 높은 것만
        else:
            weights = [p ** (1 / temperature) for p in probabilities.values()]
            word = rng.choices(list(probabilities), weights)[0]
        if word == "</s>":
            break
        out.append(word)
    return " ".join(out)


print("'Show' 다음 낱말:", {w: round(p, 2) for w, p in list(table("Show").items())[:4]})
print("temperature 0:", generate(0))
print("temperature 0:", generate(0), "<- 다시 해도 같다")
print("temperature 1:", generate(1, seed=1))
print("temperature 1:", generate(1, seed=2), "<- 할 때마다 다르다")
assert generate(0) == generate(0)
