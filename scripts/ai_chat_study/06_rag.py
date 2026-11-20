"""6단계 — RAG: 문서를 조각내고, 질문과 두 글자가 많이 겹치는 조각을 찾아, 프롬프트에 붙인다.

검색 식은 앱의 ProtocolDocIndex 와 같다. 조각내기만 단순화했다(줄 하나 = 조각 하나).
"""

import json
import math
import re
from collections import Counter

from mlx_lm import generate, load

from common import BASE, RESOURCES, ROOT, chat_prompt, swift_string

document = (RESOURCES / "dashcam_protocol_en.md").read_text()
chunks = [
    line.strip() for line in document.splitlines()
    if len(line.strip()) >= 20 and not set(line.strip()) <= set("|-: ")]


def bigrams(text):
    """낱말 안에서만 두 글자씩 끊는다."""
    grams = set()
    for word in re.findall(r"[^\W_]+", text.lower()):
        grams.update([word] if len(word) == 1 else [word[i:i + 2] for i in range(len(word) - 1)])
    return grams


gram_sets = [bigrams(chunk) for chunk in chunks]
document_frequency = Counter(gram for grams in gram_sets for gram in grams)
idf = {gram: math.log(len(chunks) / (1 + n)) for gram, n in document_frequency.items()}


def search(query, limit=4):
    """겹친 bigram 의 IDF 합 / sqrt(조각의 bigram 수 + 10) 이 큰 순."""
    wanted = bigrams(query)
    scored = [
        (sum(idf.get(g, 0) for g in wanted & grams) / math.sqrt(len(grams) + 10), index)
        for index, grams in enumerate(gram_sets)]
    ranked = sorted(scored, key=lambda pair: (-pair[0], pair[1]))[:limit]
    return [(score, chunks[index]) for score, index in ranked if score > 0]


question = "How do I lower the impact sensitivity while parked?"
topic = "impact sensitivity"  # 앱에서는 통역 단계가 뽑아 준다
print(f"문서 {len(document):,}글자 -> 조각 {len(chunks):,}개, 검색어 {topic!r}")
found = search(topic)
for score, chunk in found:
    print(f"  {score:.3f}  {chunk[:100]}")

# 다듬은 안내문은 키워드가 질문에 들어 있는 절(앱의 SettingsGuide.search)
guide = json.loads((RESOURCES / "settings_guide.json").read_text())["sections"]
sections = [s for s in guide if any(k.lower() in question.lower() for k in s["keywords"])][:3]

model, tokenizer = load(BASE)
instructions = swift_string(
    ROOT / "Hub/Domain/UseCases/AIChat/HubGuidePrompt.swift", "instructions")


def ask(sections, references):
    lines = ["guide:"] + [f"- {s['title']['en']}: {s['body']['en']}" for s in sections]
    lines += ["protocol reference:"] + [f"- {chunk[:240]}" for _, chunk in references]
    user = "\n".join(lines) + f"\n\nquestion: {question}"
    answer = generate(
        model, tokenizer, prompt=chat_prompt(tokenizer, instructions, user), max_tokens=120)
    return answer.split("</think>")[-1].strip()


print(f"\n질문: {question}")
print("\n[자료 없이]\n" + ask([], []))
print(f"\n[자료와 함께: 안내문 {len(sections)}절 + 문서 조각 {len(found)}개]\n" + ask(sections, found))
