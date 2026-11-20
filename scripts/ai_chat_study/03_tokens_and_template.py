"""3단계 — 모델은 글이 아니라 토큰 번호를 읽는다. 채팅 템플릿은 메시지를 그 모델의 양식으로 감싼다."""

import json

from mlx_lm import load

from common import BASE, ROOT, SYSTEM_PROMPT, chat_prompt

_, tokenizer = load(BASE)

for text in ("Show me yesterday's video", "어제 영상 보여줘"):
    ids = tokenizer.encode(text, add_special_tokens=False)
    print(f"{text!r}: {len(text)}글자 -> {len(ids)}토큰")
    print("  번호", ids)
    print("  조각", [tokenizer.decode([i]) for i in ids])

# 앱이 전용 모델에 보내는 것과 같은 프롬프트
fixture = json.loads(
    (ROOT / "scripts/fixtures/ai_chat_parser_prompt_tokens.json").read_text())
user = f"{fixture['today']}\nquestion: {fixture['question']}"
prompt = chat_prompt(tokenizer, SYSTEM_PROMPT, user)
print("\n--- 채팅 템플릿을 거친 글 ---")
print(prompt)
tokens = tokenizer.encode(prompt, add_special_tokens=False)
print(f"--- {len(tokens)}토큰 ---")
# 실기 테스트(testDedicatedParserPromptMatchesTraining)가 Swift 쪽 토큰열과 대조하는 기대값
assert tokens == fixture["tokens"]
print("앱 테스트의 기대 토큰열과 같다")
