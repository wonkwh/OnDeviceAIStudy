"""1단계 — 학습: 가중치(다이얼)를 조금씩 돌려 오차를 줄인다.

정답이 y = 2x + 1 인 점 100개를 주고, w 와 b 를 0 에서 시작해 맞춘다.
"""

import numpy as np
from numpy.random import Generator

randomGenerator: Generator = np.random.default_rng(seed=7)
# x = rng.uniform(-1, 1, 100)
x = randomGenerator.uniform(-1, 1, 100)
y = 2 * x + 1 + randomGenerator.normal(0, 0.05, 100)  # 약간의 잡음

w, b, learning_rate = 0.0, 0.0, 0.1
for step in range(201):
    error = (w * x + b) - y
    loss = (error**2).mean()  # 손실: 정답과 얼마나 다른가
    if step % 40 == 0:
        print(f"step {step:3d}  loss {loss:.4f}  w {w:.3f}  b {b:.3f}")
    # 손실을 w·b 로 미분한 값(기울기)의 반대쪽으로 조금 움직인다
    w -= learning_rate * 2 * (error * x).mean()
    b -= learning_rate * 2 * error.mean()

assert abs(w - 2) < 0.1 and abs(b - 1) < 0.1
print("w 는 2, b 는 1 근처로 왔다 — 가중치 2개짜리 모델의 학습이 끝났다")
