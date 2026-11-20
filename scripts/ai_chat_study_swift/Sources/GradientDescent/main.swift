// 1단계 — 학습: 가중치(다이얼)를 조금씩 돌려 오차를 줄인다.
// 정답이 y = 2x + 1 인 점 100개를 주고, w 와 b 를 0 에서 시작해 맞춘다.

import Foundation
import MLX

let (xKey, noiseKey) = MLXRandom.split(key: MLXRandom.key(7))
let x = MLXRandom.uniform(low: -1, high: 1, [100], key: xKey)
let y = 2 * x + 1 + MLXRandom.normal([100], loc: 0, scale: 0.05, key: noiseKey)  // 약간의 잡음

var w: Float = 0, b: Float = 0
let learningRate: Float = 0.1
for step in 0...200 {
    let error = (w * x + b) - y
    let loss = (error * error).mean()  // 손실: 정답과 얼마나 다른가
    if step % 40 == 0 {
        print(String(format: "step %3d  loss %.4f  w %.3f  b %.3f", step, loss.item(Float.self), w, b))
    }
    // 손실을 w·b 로 미분한 값(기울기)의 반대쪽으로 조금 움직인다
    w -= learningRate * 2 * (error * x).mean().item(Float.self)
    b -= learningRate * 2 * error.mean().item(Float.self)
}

precondition(abs(w - 2) < 0.1 && abs(b - 1) < 0.1)
print("w 는 2, b 는 1 근처로 왔다 — 가중치 2개짜리 모델의 학습이 끝났다")
