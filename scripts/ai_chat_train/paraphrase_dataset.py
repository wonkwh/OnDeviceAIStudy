#!/usr/bin/env python3
"""생성기 질문을 Claude(claude -p)로 바꿔 써 학습 데이터를 늘린다 — 라벨은 원문 것을 그대로 쓴다.

바꿔 쓴 문장은 라벨을 정하는 낱말(숫자·날짜·시간대·사고·직전 결과)과 장소·주제 글자가 원문과 같을 때만 남긴다.
사용: uv run python paraphrase_dataset.py [--limit N] [--per 2] [--batch 40] [--jobs 4]
Claude 응답은 runs/paraphrase/<model>.jsonl 에 쌓여, 다시 돌리면 받은 것은 건너뛴다. 출력은 data/v3/.
"""

import argparse
import json
import random
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import generate_dataset as gd

HERE = Path(__file__).resolve().parent

INSTRUCTIONS = """You rewrite questions that people type into the chat of a dashcam companion app.
For each input question write the requested number of different rewrites, the way different real users would type the same request.
Vary wording, word order, length and tone (casual, terse, polite, chatty). Lowercase or missing punctuation is fine sometimes.
Keep exactly, with the same spelling:
- every number and clock time (keep "9:30 am" as digits; do not turn numbers into words or words into numbers)
- day words: today, yesterday, the day before yesterday, N days ago, month names, weekday names
- time-of-day words (morning, afternoon, evening, night, commute, work, home, am, pm, noon) — do not add or remove any
- every place name and setting name exactly as written in the input
- whether it asks to see a video/recording or a route/map, and whether it mentions an accident, crash, hard braking or similar
- words that point at the previous answer (that, then, the above) — do not add them when the input has none
Never add information the input does not have. Never use "last night", "tonight" or "it" to refer to the previous answer.
Off-topic questions stay off-topic."""

SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "paraphrases": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "paraphrases"]}}},
    "required": ["items"],
}

# 라벨을 정하는 낱말 — 원문과 바꿔 쓴 문장에서 같아야 한다
SIGNAL_WORDS = re.compile(
    r"\b(today|yesterday|before|ago|" + "|".join(m.lower() for m in gd.MONTHS) + "|"
    + "|".join(w.lower() for w in gd.WEEKDAYS)
    + r"|morning|afternoon|evening|night|commute|work|home|am|pm|a\.m\.|p\.m\.|noon|midnight)\b")
IMPACT = re.compile(
    r"accident|crash|collision|impact|near[- ]miss|brak|sudden stop|stopped suddenly|bump|\bhit\b|slam|swerv")
VIDEO = re.compile(r"video|footage|clip|recording|recorded|record|\bwatch|\bplay|replay|\bfilm|camera|\bcam\b")
REFERENCE = re.compile(r"\bthat\b|\bthen\b|the above")
BANNED = re.compile(r"last night|tonight")


def signature(question):
    q = question.lower().replace("a.m.", "am").replace("p.m.", "pm")
    return (
        sorted(re.findall(r"\d+", q)),
        sorted(set(SIGNAL_WORDS.findall(q))),
        bool(IMPACT.search(q)),
        bool(VIDEO.search(q)),
        bool(REFERENCE.search(q)),
    )


def accept(original, paraphrase, answer):
    """라벨이 그대로 맞는 바꿔 쓰기만 통과시킨다. 통과 못 하면 이유를 돌려준다."""
    if BANNED.search(paraphrase.lower()):
        return "banned"
    if signature(paraphrase) != signature(original):
        return "signal"
    try:
        gd.validate(paraphrase, answer)
    except AssertionError:
        return "slot"
    return None


def ask_claude(model, batch, per):
    payload = [{"id": i, "question": q} for i, q in batch]
    prompt = f"Write {per} rewrites for each question.\n" + json.dumps(payload, ensure_ascii=False)
    out = subprocess.run(
        ["claude", "-p", prompt, "--model", model, "--tools", "", "--system-prompt", INSTRUCTIONS,
         "--output-format", "json", "--json-schema", json.dumps(SCHEMA), "--no-session-persistence",
         "--disable-slash-commands", "--setting-sources", ""],
        capture_output=True, text=True, timeout=600, cwd="/tmp")
    result = json.loads(out.stdout)
    if result.get("is_error"):
        raise RuntimeError(result.get("result"))
    return result["structured_output"]["items"], result.get("total_cost_usd", 0)


def fetch(model, questions, cache, per, batch_size, jobs):
    """질문마다 바꿔 쓴 문장을 받아 cache 파일에 쌓는다."""
    done = {}
    if cache.exists():
        for line in cache.read_text().splitlines():
            row = json.loads(line)
            done[row["question"]] = row["paraphrases"]
    todo = [q for q in dict.fromkeys(questions) if q not in done]
    batches = [list(enumerate(todo[i:i + batch_size])) for i in range(0, len(todo), batch_size)]
    print(f"cached {len(done)}, asking {len(todo)} in {len(batches)} calls", file=sys.stderr)
    cost = 0.0
    with ThreadPoolExecutor(jobs) as pool, cache.open("a") as file:
        futures = [(batch, pool.submit(ask_claude, model, batch, per)) for batch in batches]
        for n, (batch, future) in enumerate(futures, 1):
            try:
                items, spent = future.result()
            except Exception as error:  # 한 묶음이 실패해도 나머지는 쌓고, 다시 돌리면 그 묶음만 묻는다
                print(f"batch {n} failed: {error}", file=sys.stderr)
                continue
            cost += spent
            by_id = dict(batch)
            for item in items:
                if item["id"] in by_id:
                    question = by_id[item["id"]]
                    done[question] = item["paraphrases"]
                    file.write(json.dumps({"question": question, "paraphrases": item["paraphrases"]},
                                          ensure_ascii=False) + "\n")
            file.flush()
            print(f"batch {n}/{len(batches)} ${cost:.2f}", file=sys.stderr)
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=6000, help="generate_dataset 과 같은 값")
    parser.add_argument("--seed", type=int, default=7, help="generate_dataset 과 같은 값")
    parser.add_argument("--limit", type=int, help="앞에서 이만큼만 바꿔 쓴다(시험용)")
    parser.add_argument("--per", type=int, default=2)
    parser.add_argument("--batch", type=int, default=40)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--out", type=Path, default=HERE / "data/v3")
    args = parser.parse_args()

    rows, _ = gd.generate(args.count, args.seed)
    valid_count = max(1, len(rows) // 20)  # generate_dataset.main 과 같은 나누기
    sources = rows[:args.limit] if args.limit else rows
    cache = HERE / f"runs/paraphrase/{args.model}.jsonl"
    cache.parent.mkdir(parents=True, exist_ok=True)
    paraphrases = fetch(args.model, [r["question"] for r in sources], cache, args.per, args.batch, args.jobs)

    held_out = {gd.normalize(c["q"]) for name in (gd.ROOT / "scripts/fixtures/ai_chat_eval_en.json",
                                                   HERE / "eval_independent_en.json",
                                                   HERE / "eval_independent_v2_en.json")
                for c in json.loads(name.read_text())}
    seen = {gd.normalize(r["question"]) for r in rows}
    reasons, kept = Counter(), Counter()
    splits = {"valid": [r["messages"] for r in rows[:valid_count]],
              "train": [r["messages"] for r in rows[valid_count:]]}
    samples = []
    for index, row in enumerate(sources):
        system, user, assistant = row["messages"]
        for text in paraphrases.get(row["question"], [])[:args.per]:
            text = re.sub(r"\s+", " ", text).strip()
            key = gd.normalize(text)
            reason = "eval" if key in held_out else "duplicate" if key in seen else \
                accept(row["question"], text, assistant["content"])
            if reason:
                reasons[reason] += 1
                continue
            seen.add(key)
            kept[row["kind"]] += 1
            prompt = user["content"].rsplit("question: ", 1)[0] + "question: " + text
            # 원문이 valid 면 바꿔 쓴 것도 valid — 같은 질문이 양쪽에 걸치지 않게
            splits["valid" if index < valid_count else "train"].append(
                [system, {"role": "user", "content": prompt}, assistant])
            samples.append((row["question"], text))

    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, part in splits.items():
        rng.shuffle(part)
        with (args.out / f"{name}.jsonl").open("w") as file:
            for messages in part:
                file.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")
    total = sum(kept.values()) + sum(reasons.values())
    print(f"paraphrases {total}: kept {sum(kept.values())} {dict(kept)}, dropped {dict(reasons)}")
    print(f"rows train {len(splits['train'])}, valid {len(splits['valid'])} -> {args.out}")
    for original, text in rng.sample(samples, min(15, len(samples))):
        print(f"  {original}\n    -> {text}")


if __name__ == "__main__":
    main()
