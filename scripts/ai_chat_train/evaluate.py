#!/usr/bin/env python3
"""전용 모델 채점 — 영어 평가셋 정확도와 안내 답변 표본 (docs/ai_chat_mlx_design.md T3).

앱과 달리 문법 강제(XGrammar)가 없어 JSON 이 깨지면 오답으로 센다.
사용: uv run python evaluate.py --model runs/<이름>/fused-4bit [--adapter-path DIR] [--guide]
"""

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

from generate_dataset import ENUMS, KEYS, ROOT, SYSTEM_PROMPT

FALLBACK = {"intent": "unknown", "period": "any", "event": "any", "reference": "none"}
PM_PERIODS = {"eveningCommute", "afternoon", "evening"}
INT_KEYS = ("daysAgo", "month", "dayOfMonth", "hour", "minute")
# 평가 날짜를 고정해 다시 돌려도 같은 프롬프트가 되게 한다.
TODAY_LINE = "today: 2026-11-16 (Mon) 10:00"
GUIDE_QUESTIONS = [
    "How do I reduce parking recordings?",
    "How can I stop the dashcam from draining my car battery?",
    "What does parking mode do?",
    "How do I lower the impact sensitivity while parked?",
    "What's the difference between time-lapse and low-power mode?",
]


def decode(text):
    """모델 출력을 HubQueryDTO 로 읽는다. JSONDecoder 가 실패할 형태면 None."""
    start, end = text.find("{"), text.rfind("}")
    try:
        dto = json.loads(text[start:end + 1])
    except ValueError:
        return None
    if not isinstance(dto, dict) or not isinstance(dto.get("intent"), str):
        return None
    for key in KEYS[1:]:
        kind = int if key in INT_KEYS else str
        value = dto.get(key)
        if value is not None and (not isinstance(value, kind) or isinstance(value, bool)):
            return None
    return dto


def map_query(dto):
    """HubQueryMapper.map 과 같은 규칙으로 옮긴다. topic 은 유무만 남긴다(AIChatEvalCase.matches)."""
    def choice(key):
        return dto.get(key) if dto.get(key) in ENUMS[key] else FALLBACK[key]

    def text(key):
        return (dto.get(key) or "").strip() or None

    period = choice("period")
    month, day, days_ago = dto.get("month"), dto.get("dayOfMonth"), dto.get("daysAgo")
    if month is not None and day is not None and 1 <= month <= 12 and 1 <= day <= 31:
        when = ("date", month, day)
    elif days_ago is not None and 0 <= days_ago <= 365:
        when = ("daysAgo", days_ago)
    else:
        when = None
    clock = None
    hour = dto.get("hour")
    if hour is not None and 0 <= hour <= 23:
        minute = dto.get("minute")
        minute = minute if minute is not None and 0 <= minute <= 59 else 0
        clock = (hour + 12 if period in PM_PERIODS and hour < 12 else hour, minute)
    return {
        "intent": choice("intent"), "day": when, "clock": clock, "period": period,
        "origin": text("origin"), "destination": text("destination"), "event": choice("event"),
        "reference": choice("reference"), "topic": text("topic") is not None,
    }


def chat_prompt(tokenizer, system, user):
    # 앱은 Qwen3 사고 모드를 끈다(MLXChatBackend.templateContext). Gemma 는 이 인자를 무시한다.
    return tokenizer.apply_chat_template(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)


def run_parser(model, tokenizer, cases, dump):
    hits, intent_hits, invalid, seconds = 0, 0, 0, []
    misses = Counter()
    outputs = {}
    for case in cases:
        prompt = chat_prompt(tokenizer, SYSTEM_PROMPT, f"{TODAY_LINE}\nquestion: {case['q']}")
        started = time.time()
        output = generate(model, tokenizer, prompt=prompt, max_tokens=200)
        seconds.append(time.time() - started)
        outputs[case["q"]] = output
        want = map_query(case["expect"])
        dto = decode(output)
        if dto is None:
            invalid += 1
            print(f"INVALID {case['q']}\n  {output[:160]!r}")
            misses[want["intent"]] += 1
            continue
        got = map_query(dto)
        intent_hits += got["intent"] == want["intent"]
        if got == want:
            hits += 1
            continue
        misses[want["intent"]] += 1
        diff = {key: (got[key], want[key]) for key in got if got[key] != want[key]}
        print(f"MISS {case['q']}\n  (got, want) {diff}")
    total = len(cases)
    print(
        f"intent {intent_hits}/{total} full {hits}/{total} ({hits / total:.0%}) invalid {invalid} "
        f"avg {sum(seconds[1:]) / max(1, total - 1):.2f}s misses by intent {dict(misses)}")
    if dump:
        # 양자화 전후의 탐욕 출력을 문항별로 맞대어 보려고 남긴다.
        dump.write_text(json.dumps(outputs, ensure_ascii=False, indent=0))


def write_prompt_fixture(tokenizer, path):
    """앱이 만들 파서 프롬프트의 토큰열을 남긴다 — 실기 테스트가 Swift 쪽 토큰열과 대조한다."""
    question = "Show me the video from yesterday at 9:30 am"
    prompt = chat_prompt(tokenizer, SYSTEM_PROMPT, f"{TODAY_LINE}\nquestion: {question}")
    tokens = tokenizer.encode(prompt, add_special_tokens=False)
    path.write_text(json.dumps({"question": question, "today": TODAY_LINE, "tokens": tokens}) + "\n")
    print(f"prompt fixture: {len(tokens)} tokens -> {path}")


def swift_string(path, name):
    """Swift 여러 줄 문자열을 읽는다 — 줄 끝 `\\` 는 줄을 잇는다."""
    body = re.search(rf'static let {name} = """\n(.*?)\n\s*"""', path.read_text(), re.S).group(1)
    text = ""
    for line in body.split("\n"):
        line = line.strip()
        text += line[:-1] if line.endswith("\\") else line + "\n"
    return text.rstrip("\n")


def run_guide(model, tokenizer):
    """HubGuidePrompt 와 같은 형식으로 묻고 답을 그대로 보여 준다. 품질은 사람이 읽고 판단한다."""
    instructions = swift_string(
        ROOT / "Hub/Domain/UseCases/AIChat/HubGuidePrompt.swift", "instructions")
    guide = json.loads((ROOT / "Hub/Resources/AIChat/settings_guide.json").read_text())
    for question in GUIDE_QUESTIONS:
        lowered = question.lower()
        sections = [
            section for section in guide["sections"]
            if any(keyword.lower() in lowered for keyword in section["keywords"])][:3]
        lines = ["guide:"] + [f"- {s['title']['en']}: {s['body']['en']}" for s in sections]
        lines.append("protocol reference:")
        prompt = chat_prompt(tokenizer, instructions, "\n".join(lines) + f"\n\nquestion: {question}")
        answer = generate(
            model, tokenizer, prompt=prompt, max_tokens=200, sampler=make_sampler(temp=0.3))
        answer = answer.split("</think>")[-1].strip()
        print(f"Q {question} (sections {len(sections)})\nA {answer}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter-path")
    parser.add_argument("--guide", action="store_true", help="안내 답변 표본도 출력한다")
    parser.add_argument(
        "--eval", type=Path, default=ROOT / "scripts/fixtures/ai_chat_eval_en.json")
    parser.add_argument("--dump", type=Path, help="문항별 출력을 이 파일에 JSON 으로 남긴다")
    parser.add_argument(
        "--prompt-fixture", type=Path, help="파서 프롬프트 토큰열을 이 파일에 쓰고 끝낸다")
    args = parser.parse_args()
    model, tokenizer = load(args.model, adapter_path=args.adapter_path)
    if args.prompt_fixture:
        return write_prompt_fixture(tokenizer, args.prompt_fixture)
    run_parser(model, tokenizer, json.loads(args.eval.read_text()), args.dump)
    if args.guide:
        run_guide(model, tokenizer)


if __name__ == "__main__":
    main()
