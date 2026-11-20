"""5단계 — 구조화 출력: 양식에 맞지 않는 토큰을 후보에서 지운다(제약 디코딩).

앱은 12칸 전체를 XGrammar 로 강제한다. 여기서는 같은 원리를 intent 한 칸에만 손으로 적용한다.
아직 과외(미세조정)를 받지 않은 모델이라, 형식은 고쳐지지만 내용까지 맞지는 않는다.
"""

import mlx.core as mx
from mlx_lm import generate, load

from common import BASE, SYSTEM_PROMPT, chat_prompt

CHOICES = ["video", "drive", "settingsHelp", "unknown"]

model, tokenizer = load(BASE)


def prompt_for(question):
    user = f"today: 2026-11-16 (Mon) 14:00\nquestion: {question}"
    return chat_prompt(tokenizer, SYSTEM_PROMPT, user)


def constrained_intent(question):
    """{"intent":" 까지 써 주고, 다음 토큰을 CHOICES 로 이어질 수 있는 것으로만 제한한다."""
    prefix = tokenizer.encode(prompt_for(question) + '{"intent":"', add_special_tokens=False)
    sequences = {c: tokenizer.encode(c, add_special_tokens=False) for c in CHOICES}
    written = []
    while True:
        alive = {c: s for c, s in sequences.items() if s[: len(written)] == written}
        finished = [c for c, s in alive.items() if len(s) == len(written)]
        if finished:
            return finished[0]
        allowed = sorted({s[len(written)] for s in alive.values()})
        probabilities = mx.softmax(model(mx.array([prefix + written]))[0, -1])
        favourite = mx.argmax(probabilities).item()
        shown = {tokenizer.decode([t]): f"{probabilities[t].item():.4f}" for t in allowed}
        print(
            f"    제약이 없으면 1등은 {tokenizer.decode([favourite])!r} "
            f"({probabilities[favourite].item():.3f}) / 허용된 후보 {shown}")
        # 허용되지 않은 토큰은 확률이 아무리 높아도 고를 수 없다
        written.append(max(allowed, key=lambda token: probabilities[token].item()))


for question in ("Show me the video from yesterday at 9:30 am", "Where did I drive today?"):
    print(f"\n질문: {question}")
    free = generate(model, tokenizer, prompt=prompt_for(question), max_tokens=40)
    print("  제약 없이:", free.replace("\n", " ")[:110])
    print("  intent 칸을 네 값으로 제한하면:")
    print("   ->", constrained_intent(question))
