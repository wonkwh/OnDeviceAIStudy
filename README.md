# OnDeviceAIStudy

## Python 환경 (uv)

`scripts/ai_chat_train`(데이터 생성·LoRA 학습·평가)과 `scripts/ai_chat_study`(실습)는 각자
`pyproject.toml`·`uv.lock` 을 가진 [uv](https://docs.astral.sh/uv/) 프로젝트다. 의존성은 `mlx-lm`
하나이고(mlx·numpy 포함) Apple Silicon Mac 에서만 돈다.

```bash
brew install uv                              # 처음 한 번
uv sync --project scripts/ai_chat_train      # → scripts/ai_chat_train/.venv
uv sync --project scripts/ai_chat_study      # → scripts/ai_chat_study/.venv

# 실습 — 저장소 루트에서
uv run --project scripts/ai_chat_study python scripts/ai_chat_study/01_gradient_descent.py

# 평가 — ai_chat_train 안에서
cd scripts/ai_chat_train && uv run python evaluate.py --model runs/base/Qwen3-0.6B-4bit-public
```

- `.venv/` 는 커밋하지 않고 `uv.lock` 은 커밋한다. 패키지 추가는 `uv add --project <폴더> <패키지>`.
- `generate_dataset.py` 는 표준 라이브러리만 써서 `python3` 로 돌려도 된다.
- 단계별 순서는 [`docs/ai_chat_study_plan.md`](docs/ai_chat_study_plan.md), 학습 기록은
  [`docs/ai_chat_mlx_design.md`](docs/ai_chat_mlx_design.md) 를 본다.
