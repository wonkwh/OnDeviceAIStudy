"""9단계 — 평가: 정답을 아는 질문으로 채점한다. 같은 모델이 시험지에 따라 다른 점수를 받는다.

틀린 문항은 MISS 줄로 나온다. 약 2분 걸린다.
"""

import json

from mlx_lm import load

from common import BASE, ROOT, adapter_dir, run_parser

model, tokenizer = load(BASE, adapter_path=adapter_dir())
for name, path in (
    ("내 평가셋 (생성기와 같은 작성자)", "scripts/fixtures/ai_chat_eval_en.json"),
    ("독립 평가셋 (다른 작성자)", "scripts/ai_chat_train/eval_independent_en.json"),
):
    print(f"\n== {name}")
    run_parser(model, tokenizer, json.loads((ROOT / path).read_text()), None)
