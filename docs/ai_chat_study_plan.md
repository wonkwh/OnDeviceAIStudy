# AI 채팅 스터디 플랜 — AI 를 처음 배우는 사람이 이 브랜치를 끝까지 이해하기

작성 2026-11-16 · 브랜치 `feature/ai_chat` · 실습 코드 `Scripts/ai_chat_study/`

## 이 문서의 쓰임

AI 를 전혀 모르는 상태에서 시작해, 이 브랜치의 AI 채팅 코드(Foundation Models · MLX · LoRA · RAG)를
한 줄씩 설명할 수 있게 되는 것이 목표다. 15단계이고, 단계마다 네 가지가 있다.

- **읽을 것** — 개념을 배우는 자료. 한국어 자료를 먼저 적었다. "책"은 아래 "책과 함께 보기"의 그 책이고,
  "HF"는 "Hugging Face Learn 과 함께 보기"의 무료 강좌, "DW"는 "Datawhale 자료와 함께 보기"의 중국어 자료다.
- **돌려 볼 것** — 20~60줄짜리 코드. 아래에 적힌 출력은 2026-11-16 에 이 저장소에서 실제로 돌려 얻은 것이다.
- **우리 코드** — 그 개념이 이 브랜치의 어느 파일에 있는지.
- **스스로 답해 볼 것** — 답을 못 하면 그 단계를 다시 본다. 답은 접어 두었다.

먼저 큰 그림을 보려면 `docs/explain/2026-11-16-explanation-ai-chat-on-device-llm.html` 을 읽는다.
그 글이 "무엇을 왜"라면 이 문서는 "직접 해 보며 확인하기"다. 결정과 측정 기록은 `docs/ai_chat_mlx_design.md` 에 있다.

## 전체 지도

| # | 배우는 것 | 실습 파일 | 실행 시간 | 공부 시간(어림) | 책의 절 |
|---|---|---|---|---|---|
| 0 | 준비 | — | 5분 | 30분 | 부록 A |
| 1 | 학습 = 가중치 맞추기 | `01_gradient_descent.py` | 1초 | 2시간 | 1.1 · 3.4.3 |
| 2 | 언어 모델 = 다음 낱말 확률표 | `02_next_token.py` | 1초 | 2시간 | 1.1.3 · 1.2 · 2장 |
| 3 | 토큰과 채팅 템플릿 | `03_tokens_and_template.py` | 5초 | 1.5시간 | 2.2 · 3.3.2 |
| 4 | 추론 | `04_inference.py` | 5초 | 2시간 | 3.5 · 7.1 |
| 5 | 구조화 출력 | `05_structured_output.py` | 10초 | 1.5시간 | 9.3 |
| 6 | RAG | `06_rag.py` | 15초 | 2시간 | 1.3.4 · 9.1 · 10.1 · 10.4 · 10.5.1 |
| 7 | 양자화 | `07_quantization.py` | 2초 | 1시간 | 5.1 · 5.5.1 · 7.2 |
| 8 | LoRA | `08_lora.py` | 20초 | 2시간 | 4.1 · 5.4 · 5.5 |
| 9 | 평가 | `09_evaluate.py` | 2분 | 1.5시간 | 6.2 · 13.2.3 · 13.3 |
| 10 | 직접 학습해 보기 | 명령 3개 | 4분 | 1.5시간 | 1.3.2 · 6장 |
| 11 | 앱의 규칙 코드 | `11_app_query_rules.swift` | 10초 | 1시간 | — |
| 12 | 앱의 문서 검색 | `12_app_doc_search.swift` | 10초 | 1시간 | 10.1.4 · 10.5.1 |
| 13 | Foundation Models | `13_foundation_models.swift` | 20초 | 2시간 | — |
| 14 | 앱 안의 MLX | (실제 기기 테스트) | — | 2시간 | 7.1.2 · 7.1.4 |
| 15 | 전체 흐름과 화면 | (단위 테스트 읽기) | — | 2시간 | 9장 도입 |

1~4 는 원리, 5~10 은 이 프로젝트가 쓰는 기법, 11~15 는 앱 코드다. 순서대로 가는 것을 권한다.
공부 시간은 읽을 것의 "필수"만 본 경우의 어림이고, 합치면 25시간쯤이다.

## 책과 함께 보기 — 「LLM을 활용한 실전 AI 애플리케이션 개발」

허정준 지음, 책만, 2024-07-25, 556쪽 ([교보문고](https://product.kyobobook.co.kr/detail/S000213834592)).
아래 대응은 교보문고에 실린 **목차와 장별 소개**만 보고 정했다. 본문은 읽지 못했으므로, 절 제목과 실제 내용이 다르면 책을 따른다.

이 책과 이 프로젝트는 다루는 범위가 다르다. 미리 알고 읽으면 헷갈리지 않는다.

- **책의 실습은 구글 코랩(GPU)과 허깅페이스 라이브러리로 한다.** 우리 실습은 Mac 과 mlx-lm 이다. 개념은 같고 도구와 코드가 다르다.
  책의 코드는 코랩에서, 이 문서의 코드는 Mac 에서 돌린다.
- **책에 없는 것:** MLX, Foundation Models, Swift, 쓰는 동안 형식을 막는 제약 디코딩. 책이 Apple 의 Foundation Models 보다 먼저 나왔다.
  11·13단계는 책 없이 간다.
- **책에는 있고 우리가 쓰지 않는 것:** 임베딩 모델, 벡터 데이터베이스, 서버에서 모델 돌리기(서빙). 우리 검색은 낱말 겹침 방식이라
  책 10장의 TF-IDF·BM25 쪽이 가깝다.

| 책의 장 | 읽는 정도 | 도움이 되는 단계 | 왜 |
|---|---|---|---|
| 1장 LLM 지도 | 전부 | 1·2·6·10 | 전체 그림. 1.3.2 sLLM 과 1.3.4 RAG 가 이 프로젝트의 두 축이다 |
| 2장 트랜스포머 아키텍처 | 전부 | 2·3 | 2.2.1 토큰화, 2.3 어텐션, 2.7.2 GPT, 2.8.1 인과적 언어 모델링 |
| 3장 허깅페이스 트랜스포머 | 3.2 · 3.3.2 · 3.4.3 · 3.5 | 1·3·4·15 | 모델 허브(우리가 모델을 받는 곳), 토크나이저, 학습 루프, 직접 추론 |
| 4장 말 잘 듣는 모델 만들기 | 4.1 만 | 8·10 | 사전 학습과 미세 조정의 차이, 좋은 학습 데이터의 조건. 4.2 이후(RLHF·DPO)는 쓰지 않는다 |
| 5장 GPU 효율적인 학습 | 5.1 · 5.4 · 5.5 | 7·8·10 | 양자화와 LoRA 의 본문. 5.2·5.3(분산 학습)은 건너뛴다 |
| 6장 sLLM 학습하기 | 전부 | 9·10 | **이 프로젝트와 가장 닮은 장.** 자연어를 정해진 형식(SQL)으로 옮기는 작은 모델을 만들고 평가한다 |
| 7장 모델 가볍게 만들기 | 7.1 · 7.2 · 7.3 | 4·7·14 | 생성 과정과 KV 캐시, 양자화 도구들, 지식 증류 |
| 8장 sLLM 서빙하기 | 건너뛴다 | — | 서버에서 여러 요청을 처리하는 내용이다. 우리는 휴대폰에서 한 번에 한 질문만 처리한다 |
| 9장 LLM 애플리케이션 개발하기 | 9.1 · 9.3 | 5·6·15 | RAG 의 구성, 출력 검증 |
| 10장 임베딩 모델 | 10.1 · 10.4 · 10.5.1 은 정독, 10.2–10.3 은 훑기 | 6·12 | TF-IDF·BM25 가 우리 검색과 같은 계열이다. 임베딩 방식은 택하지 않은 쪽을 알기 위해 본다 |
| 11장 임베딩 모델 미세 조정 | 건너뛴다 | — | 임베딩 모델을 쓰지 않는다 |
| 12장 벡터 데이터베이스 | 건너뛴다 | — | 조각이 460개쯤이라 메모리에서 전부 비교한다 |
| 13장 LLM 운영하기 | 13.2.3 · 13.3 | 9 | 평가가 왜 어려운지, 평가 방식의 종류 |
| 14–16장 멀티 모달·에이전트·새 아키텍처 | 건너뛴다 | — | 이 프로젝트와 무관하다 |

책을 따라 읽는다면 순서는 1장 → 2장 → 3장(골라서) → 4.1 → 5장(골라서) → 6장 → 7장 → 9.1·9.3 → 10장(골라서) → 13.3 이고,
각 장을 읽은 뒤 표에 적힌 단계의 실습을 돌린다.

## Hugging Face Learn 과 함께 보기

[huggingface.co/learn](https://huggingface.co/learn) 의 무료 강좌(영어) 가운데 이 프로젝트에 맞는 절만 단계별 "HF" 줄에 적었다.
책과 같이 실습은 코랩·PyTorch·transformers 로 한다. 개념만 가져오고 코드는 이 문서의 Mac 실습을 돌린다.

| 강좌 | 쓰는 절 | 도움이 되는 단계 | 건너뛰는 것 |
|---|---|---|---|
| [LLM Course](https://huggingface.co/learn/llm-course/chapter1/1) | 1.4 · 1.8 · 2.2 · 2.4 · 3.4 · 3.5 · 6.5 · 11장 | 1~4 · 8~10 | 5장(Datasets) · 7장(고전 NLP) · 9~10장(Gradio·Argilla) · 12장(GRPO 추론 모델) |
| [smol-course](https://huggingface.co/learn/smol-course/unit0/1) | Unit 1 (2 · 3 · 3a) | 3 · 8 · 10 | Unit 2(DPO) · Unit 3(VLM) |
| [Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction) | Unit 1 의 LLM · 메시지 절, Bonus 1 의 함수 호출 | 2 · 3 · 5 | Unit 2~4(에이전트 프레임워크) |
| [Cookbook](https://huggingface.co/learn/cookbook/en/index) | structured_generation · advanced_rag · llm_judge · JSON 미세조정 | 5 · 6 · 9 · 10 | 서버·벡터 DB·멀티모달 예제 |

LLM Course 11장(채팅 템플릿 → SFT → LoRA → 평가)이 5~10단계를 한 흐름으로 다룬다. 10단계를 마친 뒤 한 번에 읽으면 복습이 된다.

## Datawhale 자료와 함께 보기

중국 오픈소스 학습 모임 Datawhale 의 GitHub 저장소 세 개에서 맞는 글만 단계별 "DW" 줄에 적었다. **모두 중국어**라 번역기를 켜고 읽는다.
코드는 대부분 Linux·NVIDIA GPU 기준이지만, self-llm 의 `models_mlx` 는 우리와 같은 Mac·mlx-lm 이다.

| 저장소 | 성격 | 쓰는 글 | 도움이 되는 단계 | 건너뛰는 것 |
|---|---|---|---|---|
| [happy-llm](https://github.com/datawhalechina/happy-llm) | 「처음부터 만드는 대형 모델」. 원리를 코드로 직접 짠다 | 2장 · 4.2 · 5.2 · 6.2–6.3 · 7.1–7.3 | 2 · 3 · 6 · 8~10 | 1·3장(고전 NLP·BERT 계열), 5.1·5.3(LLaMA2 사전학습), 6.1(분산 학습), 8장(강화학습) |
| [llm-cookbook](https://github.com/datawhalechina/llm-cookbook) | Andrew Ng 의 DeepLearning.AI 강좌 중국어판. API 로 앱을 만드는 쪽 | C2(시스템 만들기) 2·3·7·9·10, C4(문서 질의) 3·5, 선택 과목 Finetuning | 3 · 5 · 6 · 9 · 10 | C1(프롬프트 작성)·C3(LangChain), 서버 API 전제 예제 |
| [self-llm](https://github.com/datawhalechina/self-llm) | 「오픈소스 대형 모델 사용 안내서」. 모델별 배포·미세조정 따라 하기 | `models/Qwen3` 05·07·08, `models_mlx` | 3 · 4 · 8 · 10 | 다른 모델 폴더, vLLM·AMD·Ascend 배포 |

**가장 가까운 글 두 개.** self-llm 의 [Qwen3 08 「0.6B 작은 모델은 어디에 쓰나」](https://github.com/datawhalechina/self-llm/blob/master/models/Qwen3/08-Qwen3_0_6B%E7%9A%84%E5%B0%8F%E6%A8%A1%E5%9E%8B%E6%9C%89%E4%BB%80%E4%B9%88%E7%94%A8.md)는 Qwen3-0.6B 를 LoRA 로 미세조정해
문장에서 JSON 칸을 뽑는다. 모델 크기와 할 일이 우리와 같다(도구만 transformers·peft).
[models_mlx](https://github.com/datawhalechina/self-llm/tree/master/models_mlx)는 mlx-lm 으로 Qwen3 을 Mac 에서 돌리는 노트북이라 4단계 실습과 도구가 같다.

## 0단계 — 준비

Python 을 처음 쓴다면 문법부터 본다. 변수·리스트·딕셔너리·반복문·함수까지만 알면 실습 코드를 읽을 수 있다.

- 읽을 것: [teddylee777/machine-learning `00-Python`](https://github.com/teddylee777/machine-learning/tree/master/00-Python)
  의 01~09 노트북(한국어). Swift 개발자라면 03(딕셔너리)·08(Comprehension)·09(함수)만 봐도 된다.
- 책: 부록 A.1 구글 코랩 사용법, A.2 허깅페이스 토큰 — 책의 실습을 따라 할 때만 필요하다.

실습 환경은 [uv](https://docs.astral.sh/uv/) 로 만든다. `Scripts/ai_chat_study` 와 `Scripts/ai_chat_train` 은
각자 `pyproject.toml`·`uv.lock` 을 가진 uv 프로젝트이고, 의존성은 `mlx-lm` 하나다(mlx·numpy 가 따라온다).
Apple Silicon Mac 에서만 돈다. 7단계(LoRA 학습)는 `ai_chat_train` 환경을 쓰므로 둘 다 만든다.

```shell
brew install uv                              # 처음 한 번
uv sync --project Scripts/ai_chat_study      # → Scripts/ai_chat_study/.venv
uv sync --project Scripts/ai_chat_train      # → Scripts/ai_chat_train/.venv
```

- `.venv/` 는 커밋하지 않고 `uv.lock` 은 커밋한다. 패키지를 더할 때는 `uv add --project <폴더> <패키지>`.
- `generate_dataset.py` 는 표준 라이브러리만 쓰므로 `python3` 로 바로 돌린다.

모든 Python 실습은 저장소 루트에서 이렇게 돌린다. `NN_이름` 자리만 바꾼다.

```shell
uv run --project Scripts/ai_chat_study python Scripts/ai_chat_study/01_gradient_descent.py
```

3단계부터는 모델 파일이 필요하다. `Scripts/ai_chat_train/runs/base/Qwen3-0.6B-4bit-public` 폴더가 있으면
그것을 쓰고, 없으면 첫 실행 때 Hugging Face 에서 약 350MB 를 받는다(`common.py`).
Apple silicon Mac 이 필요하다.

## 1단계 — 학습이란 가중치를 맞추는 일이다

**목표** "모델을 학습시킨다"가 무슨 계산인지 숫자 두 개짜리 모델로 본다.

**읽을 것**
- 필수: [3Blue1Brown, But what is a neural network?](https://www.youtube.com/watch?v=aircAruvnKk) (영어, 19분) —
  신경망이 숫자 표의 곱셈과 덧셈이라는 것.
- 필수: [3Blue1Brown, Gradient descent, how neural networks learn](https://www.youtube.com/watch?v=IHZwWFHWa-w) (영어, 21분)
- 실습 노트북(한국어): teddylee777/machine-learning 의
  [`02-PyTorch/02-경사하강법-구현.ipynb`](https://github.com/teddylee777/machine-learning/blob/master/02-PyTorch/02-%EA%B2%BD%EC%82%AC%ED%95%98%EA%B0%95%EB%B2%95-%EA%B5%AC%ED%98%84.ipynb),
  [`07-Scikit-Learn/tutorial`](https://github.com/teddylee777/machine-learning/tree/master/07-Scikit-Learn/tutorial) 의 02(경사하강법)
- 더 보기: [Google ML Crash Course — Gradient descent](https://developers.google.com/machine-learning/crash-course/linear-regression/gradient-descent),
  [MLX 문서의 Linear Regression 예제](https://ml-explore.github.io/mlx/build/html/examples/linear_regression.html) (같은 일을 MLX 로)
- 책: 1.1 딥러닝과 언어 모델링, 3.4.3 트레이너 API를 사용하지 않고 학습하기(학습 루프).
  경사하강법을 제목으로 내건 절은 목차에 없다. 원리는 위 영상으로 먼저 본다.
- HF: [LLM Course 3.4 A full training loop](https://huggingface.co/learn/llm-course/chapter3/4) — 손실 → `backward` → optimizer 한 걸음의 반복을
  transformers 로 쓴 것이다. 실습의 `for` 루프와 견주어 본다.

**돌려 볼 것** `01_gradient_descent.py`

```text
step   0  loss 2.1924  w 0.000  b 0.000
step  40  loss 0.0074  w 1.864  b 0.987
step 200  loss 0.0019  w 1.993  b 0.993
```

정답(`w` 2, `b` 1)을 알려 주지 않았는데 손실이 줄면서 그 값에 다가간다. `learning_rate` 를 1.5 로 바꾸면 어떻게 되는지 해 본다.

**우리 코드** 10단계의 학습이 같은 일을 가중치 5,046,272개에 대해 한다. 학습 로그의 `train_loss` 가 이 `loss` 다.

**스스로 답해 볼 것**
1. 손실(loss)은 무엇을 재는 숫자인가?
2. 학습률을 너무 크게 하면 왜 손실이 오히려 커지는가?

<details><summary>답</summary>

1. 모델의 출력이 정답과 얼마나 다른지. 학습은 이 숫자를 줄이는 방향으로 가중치를 고친다.
2. 기울기의 반대쪽으로 한 걸음 가는데, 걸음이 너무 크면 가장 낮은 곳을 지나쳐 반대편 더 높은 곳에 떨어진다.
</details>

## 2단계 — 언어 모델은 다음 낱말의 확률표다

**목표** 언어 모델이 "생각"하는 것이 아니라 확률표에서 고르는 것임을, 세기만으로 만든 모델로 본다.

**읽을 것**
- 필수: [Andrej Karpathy, Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g) (영어, 1시간) 의 앞 20분
- 필수: [3Blue1Brown, Transformers, the tech behind LLMs](https://www.youtube.com/watch?v=wjZofJX0v4M) (영어, 27분)
- 깊이: [Karpathy, building makemore](https://www.youtube.com/watch?v=PaCmpygFfXo) (영어, 2시간) — 이 실습과 같은 bigram 모델을 처음부터 만든다.
  [코드](https://github.com/karpathy/makemore)
- 더 보기: [3Blue1Brown, Attention in transformers](https://www.youtube.com/watch?v=eMlx5fFNoYc),
  [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/),
  teddylee777/machine-learning 의 `02-PyTorch/24-seq2seq-with-attention-chatbot.ipynb` (한국어, 어텐션 실습)
- 책: 1.1.3 언어 모델링, 1.2 언어 모델이 챗GPT가 되기까지, 2장 전체 — 특히 2.3 어텐션, 2.6 디코더, 2.7.2 GPT,
  2.8.1 인과적 언어 모델링. 실습의 bigram 이 "직전 낱말만 본다"는 한계를 어텐션이 어떻게 넘는지가 2장이다.
- HF: [Agents Course — What are LLMs?](https://huggingface.co/learn/agents-course/unit1/what-are-llms) — 다음 토큰 예측, EOS 에서 멈추기, 디코딩 방식.
  [LLM Course 1.4 How do Transformers work?](https://huggingface.co/learn/llm-course/chapter1/4) — 인과적 언어 모델링과 디코더 구조.
- DW: [happy-llm 2장 Transformer 구조](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter2/%E7%AC%AC%E4%BA%8C%E7%AB%A0%20Transformer%E6%9E%B6%E6%9E%84.md) 의 2.1.5 마스크 자기 어텐션 — "앞 토큰만 본다"를 위삼각 행렬 마스크로
  구현한다. bigram(직전 하나)과 LLM(앞 전부)의 차이를 코드로 본다.

**돌려 볼 것** `02_next_token.py` — 평가셋 질문 112개에서 "이 낱말 다음에 무엇이 왔나"를 센다.

```text
'Show' 다음 낱말: {'me': 0.73, 'the': 0.21, 'that': 0.03, 'my': 0.03}
temperature 0: Show me the video from yesterday
temperature 1: Show the location of the morning commute video from yesterday evening commute video from today?
```

직전 낱말 하나만 보는 모델이라 문장이 금방 엉킨다. 실제 LLM 은 앞의 토큰 전부를 보고(어텐션) 표를 만든다는 점만 다르다.

**우리 코드** `temperature: 0` 이 `FMQueryParser.swift` 에 있다. 같은 질문에 늘 같은 12칸이 나오게 하려는 것이다.
안내 문장을 쓸 때는 0.3 이다(`FMGuideAnswerer.swift`, `MLXChatBackend.answer`).

**스스로 답해 볼 것**
1. temperature 0 과 1 의 차이는?
2. 이 bigram 모델과 Qwen3 의 공통점과 차이점을 한 문장씩.

<details><summary>답</summary>

1. 0 은 확률이 가장 높은 것만 골라 결과가 늘 같다. 1 은 확률에 비례해 뽑으므로 할 때마다 다르다.
2. 공통점: 둘 다 다음 토큰의 확률표를 만들고 거기서 하나를 골라 붙이기를 반복한다. 차이점: bigram 은 직전 낱말 하나만 보고 표를 세어서 만들며, Qwen3 은 앞의 토큰 전부를 보고 가중치 약 6억 개로 표를 계산한다.
</details>

## 3단계 — 토큰과 채팅 템플릿

**목표** 모델에 실제로 들어가는 것이 글자가 아니라 번호의 열임을 보고, 채팅 템플릿이 왜 정확히 같아야 하는지 안다.

**읽을 것**
- 필수: [Hugging Face LLM Course — Tokenizers](https://huggingface.co/learn/llm-course/chapter2/4)
- 필수: [Hugging Face — Chat templates](https://huggingface.co/docs/transformers/chat_templating)
- 깊이: [LLM Course — Byte-Pair Encoding tokenization](https://huggingface.co/learn/llm-course/chapter6/5),
  [Karpathy, Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE) (영어, 2시간)
- 도구: [Tiktokenizer](https://tiktokenizer.vercel.app/) — 글을 넣으면 토큰으로 쪼개 보여 준다(OpenAI 모델 기준이라 Qwen 과 번호는 다르다).
- 모델 카드: [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) — `enable_thinking` 설명이 있다.
- 책: 2.2.1 토큰화, 2.2.2 토큰 임베딩으로 변환하기, 3.3.2 토크나이저 활용하기.
  채팅 템플릿을 제목으로 내건 절은 목차에 없다. 위 Hugging Face 문서로 본다.
- HF: [Agents Course — Messages and Special Tokens](https://huggingface.co/learn/agents-course/unit1/messages-and-special-tokens) —
  `<|im_start|>` 같은 특수 토큰과 템플릿이 모델마다 다른 이유. 실습 출력과 같은 모양을 설명한다.
  [LLM Course 11.2 Chat Templates](https://huggingface.co/learn/llm-course/chapter11/2), [smol-course 1.2 Chat Templates](https://huggingface.co/learn/smol-course/unit1/2) —
  `apply_chat_template` 과 학습 데이터에 템플릿을 입히는 법.
- DW: [self-llm Qwen3 07 「Qwen3 Think 해부」](https://github.com/datawhalechina/self-llm/blob/master/models/Qwen3/07-Qwen3-Think-%E8%A7%A3%E5%AF%86-Blog.md) — Qwen3 의 Jinja 채팅 템플릿을 펼쳐 `enable_thinking` 이
  빈 `<think></think>` 를 넣는 원리를 보여 준다. 실습 출력 끝의 그 두 줄이다.
- DW: [happy-llm 5장](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter5/%E7%AC%AC%E4%BA%94%E7%AB%A0%20%E5%8A%A8%E6%89%8B%E6%90%AD%E5%BB%BA%E5%A4%A7%E6%A8%A1%E5%9E%8B.md) 의 5.2 Tokenizer 훈련 — BPE·WordPiece·Unigram 비교 후 BPE 토크나이저를 직접 학습한다.
  [llm-cookbook C2-2 언어 모델·대화 형식·토큰](https://github.com/datawhalechina/llm-cookbook/blob/main/docs/C2/2.%20%E8%AF%AD%E8%A8%80%E6%A8%A1%E5%9E%8B%EF%BC%8C%E6%8F%90%E9%97%AE%E8%8C%83%E5%BC%8F%E4%B8%8E%20Token%20Language%20Models,%20the%20Chat%20Format%20and%20Tokens.md) — 토큰과 system/user/assistant 형식의 입문.

**돌려 볼 것** `03_tokens_and_template.py`

```text
"Show me yesterday's video": 25글자 -> 5토큰
  조각 ['Show', ' me', ' yesterday', "'s", ' video']
'어제 영상 보여줘': 9글자 -> 7토큰
  조각 ['어', '제', ' 영', '상', ' 보', '여', '줘']

<|im_start|>system
Convert a question about a dashcam app into search fields. ...<|im_end|>
<|im_start|>user
today: 2026-11-16 (Mon) 10:00
question: Show me the video from yesterday at 9:30 am<|im_end|>
<|im_start|>assistant
<think>

</think>

--- 120토큰 ---
앱 테스트의 기대 토큰열과 같다
```

볼 것 세 가지. 한국어는 영어보다 토큰을 훨씬 많이 쓴다. `<|im_start|>` 같은 특수 토큰은 사람이 쓴 글이 아니라 템플릿이 넣는다.
끝의 빈 `<think></think>` 는 사고 모드를 끈 흔적이다.

**우리 코드**
- 프롬프트 조립: `HubQueryPrompt.userPrompt` (today 줄, previous result 줄, question 줄)
- 템플릿 적용: `MLXChatBackend.prepare` 와 `templateContext` (`enable_thinking: false`)
- 같은지 확인: `HubDevTests/Fixtures/ai_chat_parser_prompt_tokens.json` 이 이 120토큰이고,
  `MLXQueryParserEvalTests.testDedicatedParserPromptMatchesTraining` 이 Swift 쪽 결과와 대조한다.

**스스로 답해 볼 것**
1. 컨텍스트 창이 4,096 토큰이면 한국어 글은 영어 글보다 많이 들어가는가, 적게 들어가는가?
2. 학습할 때와 앱에서 쓸 때 템플릿이 한 토큰이라도 다르면 왜 문제인가?

<details><summary>답</summary>

1. 적게 들어간다. 같은 뜻을 적는 데 토큰을 더 쓴다.
2. 어댑터는 그 120토큰 모양의 입력 다음에 JSON 을 쓰도록 배웠다. 모양이 달라지면 배운 적 없는 입력이 되어 정확도가 떨어지고, 오류 없이 조용히 나빠지므로 테스트로 고정해 둔다.
</details>

## 4단계 — 추론

**목표** 진짜 LLM 에서 확률표를 직접 꺼내 보고, 생성이 "고르고 붙이기"의 반복임을 확인한다.

**읽을 것**
- 필수: [WWDC25 — Get started with MLX for Apple silicon](https://developer.apple.com/videos/play/wwdc2025/315/)
- 필수: [WWDC25 — Explore large language models on Apple silicon with MLX](https://developer.apple.com/videos/play/wwdc2025/298/)
- 참고: [MLX 문서](https://ml-explore.github.io/mlx/build/html/index.html) 의
  [Lazy Evaluation](https://ml-explore.github.io/mlx/build/html/usage/lazy_evaluation.html),
  [Unified Memory](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html)
- 참고: [mlx-lm 저장소](https://github.com/ml-explore/mlx-lm) 의 README 와
  [`generate.py`](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/generate.py)
- 깊이: [Karpathy, Let's build GPT](https://www.youtube.com/watch?v=kCc8FmEb1nY) (영어, 2시간),
  [Deep Dive into LLMs like ChatGPT](https://www.youtube.com/watch?v=7xTGNNLPyMI) (영어, 3.5시간)
- 이 Mac 에 있는 자료: `~/.claude/skills/apple-mlx/references/part-12-mlx-python/references/01-core-fundamentals.md`,
  `04-mlx-lm-cli-generation-and-caching.md`
- 책: 3.5 모델 추론하기(3.5.2 직접 추론하기는 제목으로 보아 이 실습과 같은 일을 허깅페이스로 하는 절이다),
  7.1.1 언어 모델이 언어를 생성하는 방법, 7.1.2 중복 연산을 줄이는 KV 캐시.
- HF: [LLM Course 2.2 Behind the pipeline](https://huggingface.co/learn/llm-course/chapter2/2) — 토크나이저 → 모델 → logits → softmax.
  실습의 `model(...)` 한 줄 앞뒤가 이것이다.
  [LLM Course 1.8 Inference with LLMs](https://huggingface.co/learn/llm-course/chapter1/8) — prefill·decode 두 단계, temperature, KV 캐시.
- DW: [self-llm `models_mlx`](https://github.com/datawhalechina/self-llm/tree/master/models_mlx) — [MLX 소개](https://github.com/datawhalechina/self-llm/blob/master/models_mlx/docs/MLX-LM_Intro.md)(통합 메모리, vLLM 과의 구조 차이)와
  [Qwen3 MLX 배포 노트북](https://github.com/datawhalechina/self-llm/blob/master/models_mlx/notebooks/Qwen3_MLX_%E9%83%A8%E7%BD%B2%E4%B8%8E%E4%BA%A4%E4%BA%92.ipynb). 같은 mlx-lm 으로 Qwen3 을 불러 temperature·사고 모드를 바꿔 본다.

**돌려 볼 것** `04_inference.py`

```text
어휘 151,936개 가운데 다음 토큰 상위 5개
  ' Paris'     0.264
  ' in'        0.091
  ...
The capital of France is Paris, and the capital of
```

`model(mx.array([ids]))` 한 줄이 추론의 전부다. 토큰 번호를 넣으면 어휘 151,936개 각각의 점수가 나온다.

**우리 코드** Swift 쪽 같은 자리는 `MLXChatBackend.answer` 의 `generate(input:parameters:context:)` 다.
생성이 끝날 때마다 `MLX.Memory.clearCache()` 를 부르는 이유는 위 Unified Memory 문서와
`part-13-mlx-swift/references/01-mlx-swift-lm-in-an-app.md` 의 메모리 절에 있다.

**스스로 답해 볼 것**
1. 모델이 한 번 계산해서 내놓는 것은 문장인가?
2. "Paris" 의 확률이 0.264 뿐인데 왜 그것이 뽑혔나?

<details><summary>답</summary>

1. 아니다. 다음 토큰 하나에 대한 확률표다. 문장은 그 계산을 토큰 수만큼 반복한 결과다.
2. 151,936개 가운데 가장 높았기 때문이다. 가장 높은 것만 고르는 방식(temperature 0)으로 뽑았다.
</details>

## 5단계 — 구조화 출력

**목표** 형식이 깨진 출력을 "부탁"이 아니라 "차단"으로 막는 원리를 본다. 그리고 그것만으로는 부족함을 본다.

**읽을 것**
- 필수: [Apple — Generating Swift data structures with guided generation](https://developer.apple.com/documentation/foundationmodels/generating-swift-data-structures-with-guided-generation)
- 필수: [JSON Schema — Getting started](https://json-schema.org/learn/getting-started-step-by-step)
- 깊이: [XGrammar 저장소](https://github.com/mlc-ai/xgrammar), [문서](https://xgrammar.mlc.ai/docs/),
  [논문](https://arxiv.org/abs/2411.15100) — 앱의 `MLXGuidedGeneration` 이 안에서 쓰는 엔진이다.
- 책: 9.3 데이터 검증 — 출력을 받은 뒤에 검사하는 방식이다. 쓰는 동안 막는 제약 디코딩은 목차에 없다.
- HF: [Cookbook — Structured generation](https://huggingface.co/learn/cookbook/en/structured_generation) — Outlines 의 문법(grammar)으로 JSON 형식을
  강제하는 예제. 책에 없는 제약 디코딩을 서버 쪽 도구로 보여 준다.
- HF(택하지 않은 쪽): [Agents Course — What is Function Calling?](https://huggingface.co/learn/agents-course/bonus-unit1/what-is-function-calling) —
  모델이 함수를 고르는 방식. 우리는 작은 모델에 "도구 고르기" 대신 "정해진 칸 채우기"를 시킨다(계획 문서 PhoneClaw 절).
- DW: [llm-cookbook C2-3 입력 분류](https://github.com/datawhalechina/llm-cookbook/blob/main/docs/C2/3.%20%E8%AF%84%E4%BC%B0%E8%BE%93%E5%85%A5-%E5%88%86%E7%B1%BB%20Classification.md) — 질문을 정해진 분류로 나눠 JSON 키로 받는다. 우리 intent 칸과 같은 일을
  제약 없이 프롬프트로만 한다. [C2-7 출력 검사](https://github.com/datawhalechina/llm-cookbook/blob/main/docs/C2/7.%20%E6%A3%80%E6%9F%A5%E7%BB%93%E6%9E%9C%20Check%20Outputs.md) — 보여 주기 전에 출력을 검사한다(`HubQueryMapper` 의 자리).
- DW(택하지 않은 쪽): [happy-llm 7장](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter7/%E7%AC%AC%E4%B8%83%E7%AB%A0%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%BA%94%E7%94%A8.md) 의 7.3 Tiny-Agent — 모델이 도구 함수를 골라 부르는 에이전트를 직접 짠다.
- 비교(한국어): [teddylee777/langchain-kr `03-OutputParser`](https://github.com/teddylee777/langchain-kr/tree/main/03-OutputParser) —
  출력을 받은 뒤에 고치는 방식이다. 우리는 쓰는 동안 막는 방식이라 접근이 다르다. 서버 모델(API 키 필요)을 쓰는 예제다.
- 이 Mac 에 있는 자료: `~/.claude/skills/apple-mlx/references/part-13-mlx-swift/references/03-fm-bridge-and-guided-generation.md`

**돌려 볼 것** `05_structured_output.py` — 과외를 받지 않은 모델에 전용 지시문을 주고, intent 칸만 네 값으로 제한해 본다.

```text
질문: Show me the video from yesterday at 9:30 am
  제약 없이: ```json {   "intent": "Show me the video from yesterday at 9:30 am",   "daysAgo": "1",   "month": "November",
  intent 칸을 네 값으로 제한하면:
    제약이 없으면 1등은 'Show' (0.949) / 허용된 후보 {'settings': '0.0000', 'video': '0.0002', 'unknown': '0.0004', 'drive': '0.0000'}
   -> unknown

질문: Where did I drive today?
    제약이 없으면 1등은 'Where' (0.848) / 허용된 후보 {..., 'unknown': '0.0002', 'drive': '0.0200'}
   -> drive
```

이 출력이 이 단계의 핵심이다. 제약이 없으면 모델은 intent 칸에 질문을 통째로 적고, 숫자 칸에 문자열을 넣는다.
제약을 걸면 반드시 네 값 중 하나가 나온다. 그런데 첫 질문의 답은 `unknown` 으로 **형식은 맞고 내용은 틀렸다**.
허용된 후보의 확률이 모두 0.001 에도 못 미치기 때문이다. 형식은 제약이 고치고, 내용은 학습이 고친다(8단계에서 확인한다).

**우리 코드**
- 양식: `HubQueryPrompt.jsonSchema`, `schemaFields` (칸 순서, intent 가 맨 앞)
- 강제: `MLXChatBackend.guidedJSON` (`GrammarConstraint`, `GuidedGenerationLoop`), FM 쪽은 `FMHubQuery` 의 `@Generable`
- 양식을 통과한 뒤의 거름: `HubQueryMapper.map` (11단계에서 돌려 본다)

**스스로 답해 볼 것**
1. 제약 디코딩이 보장하는 것과 보장하지 않는 것은?
2. `schemaFields` 에서 intent 가 맨 앞인 이유는?

<details><summary>답</summary>

1. 출력이 양식에 맞는 것은 보장한다. 값이 옳은 것은 보장하지 않는다.
2. 모델은 앞에서부터 쓰고, 이미 쓴 것을 보고 다음을 정한다. 무엇을 원하는지를 먼저 적어야 나머지 칸이 그 의도에 맞게 채워진다.
</details>

## 6단계 — RAG

**목표** 문서를 조각내고, 찾고, 프롬프트에 붙이는 세 단계를 직접 해 본다.

**읽을 것**
- 필수(한국어): [teddylee777/langchain-kr `12-RAG`](https://github.com/teddylee777/langchain-kr/tree/main/12-RAG) 의
  `00-RAG-Basic-PDF.ipynb` — RAG 의 표준적인 모습(임베딩 + 벡터 검색). 같은 저자의 책이 README 에
  [위키독스 링크](https://wikidocs.net/book/14314)로 걸려 있다.
- 필수(한국어): 같은 저장소 [`10-Retriever`](https://github.com/teddylee777/langchain-kr/tree/main/10-Retriever) 의
  `10-Kiwi-BM25Retriever.ipynb` — 임베딩 없이 낱말 겹침으로 찾는 방식. 우리 방식과 같은 계열이다.
- 참고: [tf–idf (Wikipedia)](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) — IDF 의 정의
- 깊이: [RAG 원 논문](https://arxiv.org/abs/2005.11401)
- 책: 1.3.4 RAG 소개, 9.1 검색 증강 생성(9.1.2 프롬프트에 검색 결과 통합이 `HubGuidePrompt` 가 하는 일이다),
  10.1.3–10.1.4 백오브워즈·TF-IDF, 10.4.1 BM25, 10.5.1 BM25 구현하기 — 우리 검색(bigram + IDF)과 같은 계열이다.
  10.2–10.3 은 임베딩 방식으로, 우리가 택하지 않은 표준 방식을 알기 위해 훑는다. 11·12장은 건너뛴다.
- HF(택하지 않은 쪽): [Cookbook — Advanced RAG](https://huggingface.co/learn/cookbook/en/advanced_rag) — 조각내기·임베딩·재순위(rerank)를 갖춘
  표준 RAG. 조각내기 절은 우리에게도 해당하고, 임베딩·재순위는 쓰지 않는 쪽이다.
- DW: [llm-cookbook C4-3 문서 분할](https://github.com/datawhalechina/llm-cookbook/blob/main/docs/C4/3.%20%E6%96%87%E6%A1%A3%E5%88%86%E5%89%B2%20Splitting.md) — 글자·토큰·Markdown 제목 기준 분할. 우리 프로토콜 문서도 Markdown 이다.
  [C4-5 검색](https://github.com/datawhalechina/llm-cookbook/blob/main/docs/C4/5.%20%E6%A3%80%E7%B4%A2%20Retrieval.md) 은 임베딩 검색의 변형들이다.
- DW(택하지 않은 쪽): [happy-llm 7장](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter7/%E7%AC%AC%E4%B8%83%E7%AB%A0%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%BA%94%E7%94%A8.md) 의 7.2 Tiny-RAG — 임베딩·벡터 저장소로 RAG 를 처음부터 짠다.
- 참고(택하지 않은 쪽): [NatashaTheRobot — How to Train Your Own On-Device Search Model](https://www.natashatherobot.com/p/train-your-own-on-device-search) — 정해진 목록(설정 151개)에서
  고르는 검색을 25MB 임베딩 모델(all-MiniLM-L6-v2)로 한다. 우리 `SettingsGuide.search` 는 키워드가 글자 그대로 있어야 찾지만,
  이 방식은 뜻이 같은 다른 말("screen lights out" → Auto-Lock)도 찾는다. 영어 전용이다.

위 노트북은 LangChain 과 서버 모델을 쓴다. 우리 코드는 LangChain 도 임베딩도 쓰지 않는다. 개념(조각내기 → 검색 → 붙이기)만 가져온다.

**돌려 볼 것** `06_rag.py`

```text
문서 117,502글자 -> 조각 1,762개, 검색어 'impact sensitivity'
  4.515  | parksensorsen | Impact (event/shock) sensitivity (parking) |
  4.211  | infsensorsen | Impact (event/shock) sensitivity (continuous/driving) |
  4.166  | infeventsense | Driving impact (event/shock) sensitivity (OFF/LOW/MID/HIGH) |
  4.166  | infeventsense | Driving impact (event/shock) sensitivity (OFF/LOW/MID/HIGH) |

[자료 없이]
To lower the impact sensitivity while parked, you can adjust the sensitivity setting in your dashcam settings. ...

[자료와 함께: 안내문 1절 + 문서 조각 4개]
To lower the impact sensitivity while parked, go to the **parksensorsen** setting and set the value to **LOW**.
```

볼 것 세 가지.
- 자료가 없으면 어느 설정인지 말하지 못하는 두루뭉술한 답이 나온다. 자료가 있으면 구체적이 된다.
- 같은 조각이 두 번 나왔다. 이 실습은 줄 하나를 조각 하나로 보기 때문이다. 앱은 같은 설정 키를 한 조각으로 합친다(12단계에서 확인).
- 지시문에 "필드 이름을 말하지 말라"고 적혀 있는데도 답에 `parksensorsen` 이 나왔다. 작은 모델은 지시를 어길 수 있다.
  이 실습은 앱과 조건이 다르지만(조각내기 단순화, 화면 제목 없음), 안내 답변 품질을 실제 기기에서 재야 하는 이유를 보여 준다.

**우리 코드** `SettingsGuide.search` (키워드), `ProtocolDocIndex` (bigram + IDF), `HubGuidePrompt` (자료를 붙이는 양식과 규칙),
`HubChatEngine.guideAnswer` (세 가지를 엮는 곳)

**스스로 답해 볼 것**
1. 문서 전체를 프롬프트에 넣지 않는 이유는?
2. 점수를 조각 길이로 나누는 이유는?
3. 문서 검색에 질문 전체가 아니라 `topic` 을 쓰는 이유는?

<details><summary>답</summary>

1. 문서는 약 6만 토큰이고 내장 모델의 컨텍스트 창은 4,096 토큰이다.
2. 긴 조각은 두 글자 조각을 많이 가져 아무 질문과도 잘 겹친다. 길이로 눌러 주지 않으면 긴 문단이 늘 위에 온다.
3. 질문의 말끝("~하려면")이 엉뚱한 조각과 겹쳐 순위를 흐리기 때문이다.
</details>

## 7단계 — 양자화

**목표** 1.2GB 모델이 335MB 가 되는 계산을 직접 하고, 실제 파일이 그렇게 저장돼 있는지 확인한다.

**읽을 것**
- 필수: [Hugging Face Optimum — Quantization 개념 안내](https://huggingface.co/docs/optimum/concept_guides/quantization)
- 참고: [MLX `mx.quantize`](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html)
- 참고: [safetensors](https://github.com/huggingface/safetensors) — 가중치 파일 형식. 맨 앞에 JSON 머리말이 있어 실습에서 그것만 읽는다.
- 책: 5.1.1 딥러닝 모델의 데이터 타입, 5.1.2 양자화로 모델 용량 줄이기, 5.5.1 4비트 양자화와 2차 양자화,
  7.2 양자화로 모델 용량 줄이기. 7.2 의 도구(비츠앤바이츠·GPTQ·AWQ)는 GPU 서버용이라 MLX 와 다르다. 원리만 가져온다.
- HF: [LLM Course 2.8 Optimized Inference Deployment](https://huggingface.co/learn/llm-course/chapter2/8) — 서버 추론 도구에서 양자화가 쓰이는 자리.
  서버용이라 훑기만 한다.
- 이 Mac 에 있는 자료: `~/.claude/skills/apple-mlx/references/part-12-mlx-python/references/03-quantization.md`

**돌려 볼 것** `07_quantization.py`

```text
비트  가중치당 저장 비트  평균 오차(가중치 크기 대비)
  8            8.50       0.56%
  4            4.50       9.49%
  2            2.50      47.73%

실제 파일의 k_proj (원래 1024 x 1024 표)
  biases   BF16  [1024, 16]
  scales   BF16  [1024, 16]
  weight   U32   [1024, 128]
  Qwen3-0.6B-bf16             1192 MB
  Qwen3-0.6B-4bit-public       335 MB
```

`weight` 가 `[1024, 128]` 인 까닭을 계산해 본다. 한 줄에 가중치 1,024개 × 4비트 = 4,096비트 = 32비트 숫자 128개다.
`scales`·`biases` 가 `[1024, 16]` 인 것은 64개 묶음마다 하나씩이기 때문이다(1,024 ÷ 64 = 16).

**우리 코드** `ModelCatalog.verified` 의 `mlx-community/Qwen3-0.6B-4bit` 가 이 4비트 판이다.
4비트로 충분하다는 근거는 설계 문서 T3 기록의 표(8·6·4비트 비교)에 있다.

**스스로 답해 볼 것**
1. "4비트"인데 왜 가중치당 4.5비트를 쓰는가?
2. 실습의 4비트 오차는 9.5% 인데 정확도가 떨어지지 않았다는 것은 어떻게 확인했나?

<details><summary>답</summary>

1. 64개 묶음마다 16비트 숫자 둘(간격과 기준값)을 따로 저장한다. 32 ÷ 64 = 0.5비트가 더 든다.
2. 오차 수치가 아니라 평가셋으로 확인했다. 줄이기 전과 후의 답이 192문항 가운데 3문항에서만 달랐고 정답 수는 줄지 않았다.
</details>

## 8단계 — LoRA

**목표** 얇은 표 두 개가 무엇인지 식으로 보고, 앱에 든 어댑터를 열어 보고, 끼웠을 때와 뺐을 때의 차이를 본다.

**읽을 것**
- 필수: [mlx-lm `LORA.md`](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md) — 우리가 쓴 학습 도구의 설명서
- 필수: [mlx-lm `tuner/lora.py`](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/tuner/lora.py) —
  `LoRALinear` 의 `__call__` 이 식 `y + scale * z` 그대로다. 40줄쯤이다.
- 깊이: [LoRA 논문](https://arxiv.org/abs/2106.09685) 의 1·4절
- Swift 쪽: [mlx-swift-lm `LoRAContainer.swift`](https://github.com/ml-explore/mlx-swift-lm/blob/main/Libraries/MLXLMCommon/Adapters/LoRA/LoRAContainer.swift)
  (main 브랜치다. 우리는 3.32.3 을 쓴다)
- 비교(한국어): [teddylee777/langchain-kr `18-FineTuning`](https://github.com/teddylee777/langchain-kr/tree/main/18-FineTuning) —
  다른 도구(Unsloth)로 하는 미세조정. 데이터 형식과 흐름이 비슷하다.
- 책: 4.1 사전 학습과 지도 미세 조정, 5.4 LoRA 전체(5.4.2 LoRA 설정 살펴보기가 우리 설정 파일의 rank·scale 에 해당한다),
  5.5 QLoRA — 10단계에서 4비트 base 에 어댑터를 학습하는 것이 이 방식이다.
- HF: [LLM Course 11.4 LoRA](https://huggingface.co/learn/llm-course/chapter11/4), [smol-course 1.3a LoRA and PEFT](https://huggingface.co/learn/smol-course/unit1/3a) —
  rank 의 뜻, 어댑터를 base 에 합치기(merge). 우리는 합치지 않고 따로 끼운다(`model.perform(with:perform:)`).
- DW: [happy-llm 6장](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter6/%E7%AC%AC%E5%85%AD%E7%AB%A0%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E8%AE%AD%E7%BB%83%E6%B5%81%E7%A8%8B%E5%AE%9E%E8%B7%B5.md) 의 6.3 고효율 미세조정 — 6.3.3 저랭크 원리, 6.3.4 LoRA 층을 직접 바꿔 끼우는 코드, 6.3.5 peft.
  [4장](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E5%A4%A7%E8%AF%AD%E8%A8%80%E6%A8%A1%E5%9E%8B.md) 의 4.2 Pretrain·SFT·RLHF 는 책 4.1 과 같은 내용이다.
  [self-llm Qwen3 05 LoRA](https://github.com/datawhalechina/self-llm/blob/master/models/Qwen3/05-Qwen3-8B-LoRA%E5%8F%8ASwanLab%E5%8F%AF%E8%A7%86%E5%8C%96%E8%AE%B0%E5%BD%95.md) — peft 로 Qwen3 에 LoRA 를 걸고 어댑터를 불러 추론까지 한다.
- 이 Mac 에 있는 자료: `~/.claude/skills/apple-mlx/references/part-12-mlx-python/references/06-finetuning-and-porting-models.md`

**돌려 볼 것** `08_lora.py`

```text
W 1048576 개 / A+B 16384 개 (1.6%)
B 가 0 이면 출력이 원래와 같다: True
앱의 어댑터: 표 392개(= 196곳 x A·B), 가중치 5,046,272개
  {'fine_tune_type': 'lora', 'num_layers': 28, 'lora_parameters': {'rank': 8, 'dropout': 0.0, 'scale': 20.0}}

[어댑터 뺌]
  12칸 옮기기: ```json {   "intent": "Show me the video from yesterday at 9:30 am",   "daysAgo": "1",   "month": "November", ...
  안내 문장  : To reduce parking recordings, you can adjust the parking impact sensitivity setting in the dashcam app. ...

[어댑터 끼움]
  12칸 옮기기: {"intent":"video","daysAgo":1,"month":null,"dayOfMonth":null,"hour":9,"minute":30,"period":"any",...,"topic":null}
  안내 문장  : {"settingsHelp("parkingimpact","none","none","none","none","none","null","null",...
```

같은 base, 같은 질문인데 20MB 짜리 어댑터 하나로 결과가 뒤바뀐다. 끼우면 12칸은 정확해지고 안내 문장은 망가진다.
앱이 통역할 때만 어댑터를 끼우는 이유가 이 출력이다.

**우리 코드**
- 어댑터 파일: `Hub/Resources/AIChat/ai_chat_parser_adapter.safetensors` · `.json`
- 읽기: `MLXParserAdapterFiles.load`
- 끼웠다 빼기: `MLXChatBackend.parse` 의 `modelContext.model.perform(with: adapter, perform: generate)`
- 지시문 고르기: `Loaded.parserInstructions`
- `num_layers` 가 28 인 이유: 설계 문서 T3 기록의 "결정" 절

**스스로 답해 볼 것**
1. 학습을 시작할 때 B 를 0 으로 두는 이유는?
2. 설정 파일의 `scale` 이 빠지면 Swift 쪽에서 어떤 일이 생기나?
3. 어댑터를 다른 base 모델에 끼워도 되는가?

<details><summary>답</summary>

1. A·B 의 곱이 0 이라 처음에는 원래 모델과 똑같이 동작한다. 거기서부터 조금씩 달라지게 하려는 것이다.
2. Swift 의 기본값은 10 이고 학습은 20 으로 했다. 덧붙이는 양이 절반이 되어 정확도가 조용히 떨어진다.
3. 안 된다. A·B 는 그 base 의 가중치에 더해질 것을 전제로 학습됐다. 그래서 추천 목록은 판(revision)까지 고정한다.
</details>

## 9단계 — 평가

**목표** 채점기를 돌려 설계 문서의 숫자를 직접 재현하고, 두 시험지의 점수가 왜 다른지 설명할 수 있게 된다.

**읽을 것**
- 필수: [Google ML Crash Course — Overfitting](https://developers.google.com/machine-learning/crash-course/overfitting/overfitting)
- 필수(한국어): teddylee777/machine-learning [`07-Scikit-Learn/tutorial`](https://github.com/teddylee777/machine-learning/tree/master/07-Scikit-Learn/tutorial) 의
  03(데이터셋 다루기 — 학습용과 시험용을 나누는 법), 07(분류 평가지표)
- 비교(한국어): [teddylee777/langchain-kr `16-Evaluations`](https://github.com/teddylee777/langchain-kr/tree/main/16-Evaluations) —
  정답 비교가 아니라 다른 모델에게 채점시키는 방식 등. 우리는 정답이 정해져 있어 단순 비교를 쓴다.
- 이 Mac 에 있는 자료: `~/.claude/skills/apple-ai-evaluations/references/part-06-evaluations/references/01-foundations-and-hill-climbing.md`
- 우리 기록: 설계 문서의 T1·T2·T3 기록 (평가셋을 어떻게 만들었고 무엇을 조심했는지)
- 책: 6.2 성능 평가 파이프라인 준비하기(6.2.2 평가 데이터셋 구축), 13.2.3 LLM 평가의 어려움, 13.3 LLM 평가하기.
  장 소개에 따르면 13장은 정답이 하나로 정해지지 않는 평가의 어려움을 다룬다. 우리는 12칸의 정답 비교라 13.3.1 정량적 지표 쪽에 해당한다.
- HF: [LLM Course 11.5 Evaluation](https://huggingface.co/learn/llm-course/chapter11/5) — 공개 벤치마크만으로 부족해 도메인 평가셋을 따로 만드는 이유.
  우리 `eval_independent_en.json` 이 그 도메인 평가셋이다.
- HF(비교): [Cookbook — LLM-as-a-judge](https://huggingface.co/learn/cookbook/en/llm_judge) — 다른 모델에게 채점시키는 방식.
  안내 답변(6단계)처럼 정답이 하나가 아닌 출력을 잴 때 쓴다.
- DW: [llm-cookbook C2-9 평가(상) 정답이 있을 때](https://github.com/datawhalechina/llm-cookbook/blob/main/docs/C2/9.%20%E8%AF%84%E4%BC%B0%EF%BC%88%E4%B8%8A%EF%BC%89%20Evaluation-part1.md) — 어려운 문항 추가 → 지시문 수정 → 회귀 테스트 → 개발셋 정답률.
  우리 평가 방식과 같은 순서다. [C2-10 평가(하) 정답이 없을 때](https://github.com/datawhalechina/llm-cookbook/blob/main/docs/C2/10.%20%E8%AF%84%E4%BC%B0%EF%BC%88%E4%B8%8B%EF%BC%89Evaluation-part2.md) 는 모델에게 채점시키는 쪽이다.
- DW: [happy-llm 7장](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter7/%E7%AC%AC%E4%B8%83%E7%AB%A0%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%BA%94%E7%94%A8.md) 의 7.1 평가 — 공개 평가셋과 순위표. 우리가 도메인 평가셋을 따로 만든 이유의 배경으로 훑는다.

**돌려 볼 것** `09_evaluate.py` (약 2분)

```text
== 내 평가셋 (생성기와 같은 작성자)
intent 112/112 full 112/112 (100%) invalid 0 avg 0.53s

== 독립 평가셋 (다른 작성자)
MISS I want to watch yesterday's drive to Costco
  (got, want) {'intent': ('drive', 'video')}
MISS Can you play back the trip from home to Brighton? I want the video, not the map.
  (got, want) {'intent': ('drive', 'video')}
MISS Show the sudden stop on the motorway at 8:05 am today
  (got, want) {'intent': ('drive', 'video')}
intent 77/80 full 76/80 (95%) invalid 0 avg 0.53s
```

설계 문서의 "4bit base + 어댑터: 112/112 · 76/80" 과 같은 숫자다. MISS 줄을 읽어 본다. intent 를 틀린 세 문항이 모두 같은 유형이다.

**우리 코드** `Scripts/ai_chat_train/evaluate.py` 의 `map_query` 가 Swift 의 `HubQueryMapper.map` 과 같은 규칙이고,
`topic` 을 유무로만 비교하는 것은 Swift 의 `AIChatEvalCase.matches` (`HubDevTests/FMQueryParserEvalTests.swift`)와 같다.

**스스로 답해 볼 것**
1. 왜 내 평가셋 점수가 아니라 독립 평가셋 점수를 기준으로 삼나?
2. 독립 평가셋에서 틀린 문항을 보고 학습 데이터를 고치면 무엇이 문제인가?
3. 이 점수는 iPhone 에서의 점수인가?

<details><summary>답</summary>

1. 학습 데이터의 문형과 내 평가셋을 같은 사람이 써서 말버릇이 닮았다. 점수가 실력보다 높게 나온다.
2. 그 순간 독립 평가셋도 "본 시험"이 되어 다음 점수를 믿을 수 없다. 고치려면 독립 평가셋을 새로 써야 한다.
3. 아니다. Mac 에서, 형식 강제 없이 잰 값이다. 앱은 형식을 강제하고 다른 토크나이저 구현을 쓰므로 실제 기기 측정이 따로 필요하다.
</details>

## 10단계 — 직접 학습해 보기

**목표** 학습 데이터 한 줄의 모양을 보고, 100걸음만 학습시켜 0점이던 모델이 얼마나 달라지는지 본다.

**읽을 것** 8단계의 `LORA.md` 가운데 Data 절과 학습 옵션. 그리고 `Scripts/ai_chat_train/generate_dataset.py` 의 맨 위 60줄.

- 책: 6장 전체. 자연어 질문을 SQL 로 옮기는 작은 모델을 미세 조정하는 장이라, 질문을 12칸으로 옮기는 우리 작업과 구조가 같다.
  6.1.3 합성 데이터 활용 ↔ `generate_dataset.py`, 6.3.1 기초 모델 평가하기 ↔ 아래 표의 "학습 전 0/80",
  6.3.4 기초 모델 변경 ↔ Gemma 270M 과 Qwen3 0.6B 비교, 6.3.5 모델 성능 비교 ↔ 설계 문서 T3 의 표.
  1.3.2 sLLM 도 함께 본다.
- HF: [LLM Course 3.5 Understanding Learning Curves](https://huggingface.co/learn/llm-course/chapter3/5) — train/val 손실 곡선 읽기와 과적합 신호.
  아래 학습 로그의 `val` 줄을 이 눈으로 본다.
- HF: [LLM Course 11.3 Fine-Tuning with SFTTrainer](https://huggingface.co/learn/llm-course/chapter11/3), [smol-course 1.3 Supervised Fine-Tuning](https://huggingface.co/learn/smol-course/unit1/3) —
  같은 지도 미세조정을 TRL 로 한다. 도구는 다르고 데이터 모양(system · user · assistant)은 같다.
- HF: [Cookbook — Fine-tuning LLM to Generate … in JSON Format](https://huggingface.co/learn/cookbook/en/fine_tuning_llm_to_generate_persian_product_catalogs_in_json_format) —
  QLoRA 로 작은 모델이 JSON 을 쓰게 학습한다. 목적이 우리와 가깝다.
- DW: [self-llm Qwen3 08 「0.6B 작은 모델은 어디에 쓰나」](https://github.com/datawhalechina/self-llm/blob/master/models/Qwen3/08-Qwen3_0_6B%E7%9A%84%E5%B0%8F%E6%A8%A1%E5%9E%8B%E6%9C%89%E4%BB%80%E4%B9%88%E7%94%A8.md) — **Qwen3-0.6B** 를 LoRA 로 미세조정해 문장에서
  이름·주소 같은 JSON 칸을 뽑는다. 모델과 할 일이 우리와 가장 가깝다. 학습 데이터를 합성한 점도 같다(그쪽은 큰 모델로, 우리는 스크립트로).
- DW: [happy-llm 6장](https://github.com/datawhalechina/happy-llm/blob/main/docs/chapter6/%E7%AC%AC%E5%85%AD%E7%AB%A0%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E8%AE%AD%E7%BB%83%E6%B5%81%E7%A8%8B%E5%AE%9E%E8%B7%B5.md) 의 6.2 지도 미세조정 — 6.2.1 Pretrain 과 SFT 의 차이, 6.2.2 역할 표시·특수 토큰을 붙여 학습 데이터 만들기.
  [llm-cookbook 선택 과목 Finetuning LLMs](https://github.com/datawhalechina/llm-cookbook/tree/main/content/%E9%80%89%E4%BF%AE-Finetuning%20Large%20Language%20Models) — 왜 미세조정하나, 데이터 준비, 학습, 평가와 반복(노트북).
- 참고: 6단계의 [NatashaTheRobot 글](https://www.natashatherobot.com/p/train-your-own-on-device-search) 중 학습 과정 — 큰 모델이 검색어를 합성하고, 다른 모델(Claude)이 정답을 붙인 1,006개로
  큰 모델을 미세조정한 뒤, 그 모델이 검색어마다 붙인 확률(예: Auto-Lock 70%, Brightness 14%)을 작은 모델에 가르친다(증류).
  우리는 스크립트가 정답 하나를 붙인다. 테스트가 200개뿐이고 정답도 모델이 붙였다는 점을 감안해 읽는다.

**돌려 볼 것** 명령 세 개다. `Scripts/ai_chat_train` 에서 돌린다.

```shell
cd Scripts/ai_chat_train
uv sync
python3 generate_dataset.py
head -n 1 data/train.jsonl
```

한 줄이 system(지시문) · user(질문) · assistant(정답 JSON) 세 메시지다. 이제 100걸음만 학습한다(약 1분 30초).

```shell
AGX_RELAX_CDM_CTXSTORE_TIMEOUT=1 uv run mlx_lm.lora --model runs/base/Qwen3-0.6B-4bit-public \
  --train --data data --adapter-path /tmp/mini-adapter --iters 100 --batch-size 8 --num-layers 28 \
  --mask-prompt --learning-rate 1e-4 --steps-per-report 20 --steps-per-eval 50 --val-batches 5 \
  --max-seq-length 512 --seed 7
```

```text
Trainable parameters: 0.847% (5.046M/596.050M)
     1    val 1.942
    20    0.489
    40    0.064
   100    val 0.006
```

1단계에서 본 손실이 같은 모양으로 줄어든다. 이 어댑터와, 학습 전 모델을 독립 평가셋으로 채점한다.

```shell
uv run python evaluate.py --model runs/base/Qwen3-0.6B-4bit-public --eval eval_independent_en.json | tail -n 1
uv run python evaluate.py --model runs/base/Qwen3-0.6B-4bit-public --adapter-path /tmp/mini-adapter \
  --eval eval_independent_en.json | tail -n 1
```

| 모델 | 독립 평가셋 전체 | intent |
|---|---|---|
| 학습 전 | 0 / 80 (형식이 80문항 모두 깨짐) | 0 / 80 |
| 100걸음 학습 | 62 / 80 | 74 / 80 |
| 2,000걸음 학습 (앱에 든 어댑터) | 76 / 80 | 77 / 80 |

`runs/base/...` 폴더가 없으면 `--model mlx-community/Qwen3-0.6B-4bit` 로 바꾼다.
`AGX_RELAX_CDM_CTXSTORE_TIMEOUT=1` 이 없으면 화면이 켜진 Mac 에서 학습이 몇 걸음 만에 죽는다(설계 문서 T3 기록).
앱에 든 어댑터는 16비트 base 로 학습했고 여기서는 편의상 4비트 base 로 학습한다.

**우리 코드** 실제 학습 명령과 설정 이유는 설계 문서 T3 기록. 데이터 규칙(칸별 라벨 규칙)은 같은 문서 "학습 데이터" 절.

**스스로 답해 볼 것**
1. "Trainable parameters 0.847%" 는 무슨 뜻인가?
2. `--mask-prompt` 는 무엇을 하는가?
3. 정답을 먼저 뽑고 질문을 조립하는 방식의 장점과 한계는?

<details><summary>답</summary>

1. 가중치 5억 9,605만 개 가운데 504만 6천 개(어댑터)만 고친다는 뜻이다. 나머지는 고정이다.
2. 손실을 assistant 의 답 부분에서만 계산한다. 지시문과 질문을 따라 쓰는 연습에 학습을 쓰지 않는다.
3. 장점: 정답이 구성상 틀릴 수 없고, 외부 서비스 없이 같은 결과를 다시 만든다. 한계: 문형이 스크립트에 적은 것으로 한정돼, 사람이 실제로 쓰는 다양한 표현을 다 덮지 못한다. 독립 평가셋의 오답이 그 증거다.
</details>

## 11단계 — 앱의 규칙 코드를 Mac 에서 돌리기

여기서부터는 Swift 다. 앱의 도메인 파일은 Foundation 만 쓰므로 Xcode 프로젝트 없이 `swiftc` 로 바로 컴파일된다.
실습 파일은 앱 타깃에 들어 있지 않아 Xcode 에서 열면 빨간 오류가 보이는데, 아래 명령으로는 컴파일된다.

**목표** 모델이 쓴 JSON 이 앱 안에서 어떤 값으로 바뀌는지, 믿을 수 없는 입력이 어디서 걸러지는지 본다.

**읽을 것**
- 우리 코드: `Hub/Domain/Entities/AIChat/HubQueryDTO.swift`, `HubQuery.swift`, `Hub/Domain/UseCases/AIChat/HubQueryResolver.swift`
- 테스트: `HubDevTests/HubQueryMapperTests.swift`, `HubQueryResolverTests.swift` — 규칙 하나가 테스트 하나다.
- 배경: 이 Mac 의 `~/.claude/skills/type-driven-design-swift-ko/references/part2-parse-dont-validate.md` (왜 타입을 둘로 나누는가)
- 책: 해당하는 절이 없다. 9.3 데이터 검증이 "모델 출력을 믿지 않고 검사한다"는 같은 문제의식이다.

**돌려 볼 것** 저장소 루트에서:

```shell
swiftc -parse-as-library -o "$TMPDIR/study11" \
  Hub/Domain/Entities/AIChat/HubQuery.swift Hub/Domain/Entities/AIChat/HubQueryDTO.swift \
  Hub/Domain/UseCases/AIChat/HubQueryResolver.swift Scripts/ai_chat_study/11_app_query_rules.swift \
  && "$TMPDIR/study11"
```

```text
■ 퇴근길 6시 — 오후 시간대라 18시로 올린다
  intent=video day=daysAgo(0) clock=Optional(HubClockTime(hour: 18, minute: 0))
  찾을 범위: 11-16 17:55 ~ 11-16 18:05 시간대=nil 기준시각=11-16 18:00

■ 범위 밖 값(hour 25, 모르는 intent·period)은 버린다
  intent=unknown day=unspecified clock=nil
  찾을 범위: 10-17 00:00 ~ 11-16 14:00 시간대=nil 기준시각=없음
```

`outputs` 의 JSON 을 고쳐 가며 돌려 본다. 예를 들어 `month` 11, `dayOfMonth` 30 을 넣으면(지금이 11월 16일일 때) 어느 해가 되는가.

**스스로 답해 볼 것**
1. `HubQueryDTO` 와 `HubQuery` 를 왜 나눴나?
2. 시각만 말하고 날짜를 말하지 않으면 어느 날로 보나?

<details><summary>답</summary>

1. DTO 는 모델이 쓴 그대로라 무엇이든 들어올 수 있다. 경계에서 한 번 걸러 enum 으로 된 `HubQuery` 로 바꾸면 그 뒤의 코드는 틀린 값을 걱정하지 않는다.
2. 오늘. 다만 그 시각이 아직 오지 않았으면 어제(`HubQueryResolver.dayStart` 의 `.unspecified`).
</details>

## 12단계 — 앱의 문서 검색을 Mac 에서 돌리기

**목표** 6단계에서 흉내 낸 검색의 진짜 구현을 실제 문서에 돌려 보고, 단순화했던 부분이 무엇을 하는지 확인한다.

**읽을 것** `Hub/Domain/UseCases/AIChat/ProtocolDocIndex.swift` 전체(177줄), `HubDevTests/ProtocolDocIndexTests.swift`, `SettingsGuideTests.swift`

- 책: 10.1.4 TF-IDF, 10.5.1 BM25 구현하기 — 옆에 두고 `search` 의 점수 식과 견주어 본다.

**돌려 볼 것**

```shell
swiftc -parse-as-library -o "$TMPDIR/study12" \
  Hub/Domain/UseCases/AIChat/ProtocolDocIndex.swift Scripts/ai_chat_study/12_app_doc_search.swift \
  && "$TMPDIR/study12" .
```

```text
조각 수: 한국어 459 · 영어 463
"후방 전용" 의 bigram: ["전용", "후방"]

■ How do I lower the impact sensitivity while parked?  (검색어: impact sensitivity)
  [infeventsense] infeventsense: Driving impact (event/shock) sensitivity (OFF/LOW/MID/HIGH)
  [parksensorsen] parksensorsen: Event (impact/shock) sensitivity while parked (off: parking events not used
  [infsensorsen] infsensorsen: Event (impact/shock) sensitivity during continuous (driving) recording (off:
```

6단계와 견주어 본다. 조각이 1,762개에서 463개로 줄었고(머리 행 제외, 같은 키 합치기), 같은 조각이 두 번 나오지 않는다.

**스스로 답해 볼 것**
1. "후방 전용" 의 bigram 에 "방전" 이 없는 이유는?
2. 한국어 문서와 영어 문서 가운데 어느 쪽에서 찾을지는 무엇으로 정하나?

<details><summary>답</summary>

1. 띄어쓰기를 넘어서는 두 글자를 만들지 않는다. 만들면 "방전" 같은 엉뚱한 낱말이 생겨 관계없는 조각과 겹친다.
2. 질문에 한글이 들어 있는지. 휴대폰 언어가 아니다(`ProtocolDocLibrary.index(for:)`).
</details>

## 13단계 — Foundation Models

**목표** iOS·macOS 에 든 모델을 Swift 몇 줄로 부르고, 쓸 수 있는지 판정하는 코드를 이해한다.

**읽을 것**
- 필수: [WWDC25 — Meet the Foundation Models framework](https://developer.apple.com/videos/play/wwdc2025/286/)
- 필수: [WWDC25 — Deep dive into the Foundation Models framework](https://developer.apple.com/videos/play/wwdc2025/301/)
- 참고: [Foundation Models 문서](https://developer.apple.com/documentation/foundationmodels),
  [`SystemLanguageModel`](https://developer.apple.com/documentation/foundationmodels/systemlanguagemodel) (가용성),
  [`LanguageModelSession`](https://developer.apple.com/documentation/foundationmodels/languagemodelsession)
- 더 보기: [WWDC25 — Code-along](https://developer.apple.com/videos/play/wwdc2025/259/),
  [Explore prompt design & safety for on-device foundation models](https://developer.apple.com/videos/play/wwdc2025/248/),
  [Apple Intelligence 개발자 페이지](https://developer.apple.com/apple-intelligence/)
- 이 Mac 에 있는 자료: `~/.claude/skills/apple-foundation-models/references/part-02-foundation-models-everyday-api/`
- 책: 해당하는 절이 없다. 책이 이 프레임워크보다 먼저 나왔다.

**돌려 볼 것** macOS 26 이상이고 Apple Intelligence 가 켜진 Mac 에서:

```shell
swiftc -parse-as-library -o "$TMPDIR/study13" Scripts/ai_chat_study/13_foundation_models.swift \
  && "$TMPDIR/study13"
```

```text
availability: available
현재 언어 지원: true
어제 아침 9시 30분 영상 보여줘 -> intent=video daysAgo=Optional(1)
주차 녹화를 줄이려면? -> intent=settingsHelp daysAgo=Optional(0)
노래 틀어줘 -> intent=unknown daysAgo=Optional(0)
```

모델을 받지도, 메모리에 올리지도 않았다. 4단계·8단계와 견주면 FM 과 MLX 의 차이가 코드 분량으로 보인다.
둘째·셋째 줄에서 날짜를 말하지 않았는데 `daysAgo` 가 0 으로 채워졌다. 이 실습의 지시문이 앱보다 짧기 때문일 수 있다.
앱의 지시문(`HubQueryPrompt.instructions`)에 있는 "Fill only what the user said; leave other fields empty." 를
실습의 `instructions` 에 더해 다시 돌려 보고 달라지는지 본다. 프롬프트 한 줄이 출력을 바꾸는 것을 보는 연습이다.

**우리 코드**
- 판정: `Hub/Data/AIChat/AIChatAvailability.swift` — 이 실습의 `availability` 를 다섯 가지 사유로 나눈다.
- 통역: `FoundationModels/FMQueryParser.swift` (12칸 `@Generable`), 안내: `FMGuideAnswerer.swift`
- 채점: `HubDevTests/FMQueryParserEvalTests.swift`

**스스로 답해 볼 것**
1. `#if canImport(FoundationModels)` 와 `#available(iOS 26.0, *)` 는 각각 언제 검사되나?
2. iPhone 14 에 iOS 26 을 올리면 `availability` 는?

<details><summary>답</summary>

1. 앞의 것은 컴파일할 때(개발 도구에 그 프레임워크가 있는가), 뒤의 것은 실행할 때(이 기기의 iOS 버전이 26 이상인가).
2. `.unavailable(.deviceNotEligible)`. Apple Intelligence 지원 기종이 아니다. 앱은 "이 기기에서는 지원하지 않아요"를 띄운다.
</details>

## 14단계 — 앱 안의 MLX

**목표** 4·5·8단계에서 Python 으로 한 일이 Swift 에서 어떻게 생겼는지 읽고, 휴대폰에서 조심할 것(메모리)을 안다.

**읽을 것**
- 우리 코드: `Hub/Data/AIChat/MLX/MLXChatBackend.swift` 전체(256줄). 아래 표를 옆에 두고 읽는다.
- 참고: [mlx-swift-lm 저장소](https://github.com/ml-explore/mlx-swift-lm) 의 README
- 참고: [increased-memory-limit 권한](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.kernel.increased-memory-limit)
- 이 Mac 에 있는 자료: `~/.claude/skills/apple-mlx/references/part-13-mlx-swift/references/01-mlx-swift-lm-in-an-app.md`
  (메모리, 백그라운드 진입 시 종료), `02-generation-tools-and-caching.md`
- 책: 7.1.2 중복 연산을 줄이는 KV 캐시, 7.1.4 KV 캐시 메모리 줄이기 — 모델 크기 외에 여유 메모리(300MB)가 왜 필요한지의 배경이다.
  7.3 지식 증류는 큰 모델로 작은 모델을 가르치는 방법으로, 학습 데이터를 큰 모델로 늘리게 되면 필요해진다. MLX 자체는 책에 없다.

| Python 실습에서 한 일 | Swift 의 같은 자리 |
|---|---|
| `load(BASE)` (3·4단계) | `loadedModel()` — 올리기 전 여유 메모리 확인이 더 있다 |
| `chat_prompt(...)` (3단계) | `prepare(system:user:in:)` |
| 허용된 토큰만 고르기 (5단계) | `guidedJSON` 의 `GrammarConstraint` · `GuidedGenerationLoop` |
| `load(BASE, adapter_path=...)` (8단계) | `MLXParserAdapterFiles.load()` + `model.perform(with:perform:)` |
| `generate(...)` (6단계) | `answer(...)` 의 `generate(input:parameters:context:)` |

**돌려 볼 것** MLX 는 시뮬레이터에서 돌리지 않으므로 실제 기기가 필요하다. 이 테스트는 아직 한 번도 돌리지 않았다.

```shell
xcodebuild test -project Hub.xcodeproj -scheme Hub-Dev -destination 'platform=iOS,name=<기기 이름>' \
  -only-testing:HubDevTests/MLXQueryParserEvalTests
```

`[EVAL]` 로 시작하는 줄에 정확도·질문당 시간·최대 메모리가 나온다. 9단계의 Mac 점수와 견주어 본다.

**스스로 답해 볼 것**
1. `MLXChatBackend` 가 `actor` 인 이유는?
2. 모델을 올리기 전에 무엇을 확인하고, 왜 하나?
3. `unload()` 는 언제 부르라고 만든 것인가?

<details><summary>답</summary>

1. 모델 하나를 두 작업이 동시에 쓰지 않도록 Swift 가 줄을 세워 준다.
2. 지금 쓸 수 있는 메모리가 "모델 크기 + 300MB" 이상인지. 모자란데 올리면 iOS 가 앱을 강제로 끈다.
3. 메모리 경고, 백그라운드 진입, 채팅 종료 때. 부르는 쪽은 아직 연결하지 않았다.
</details>

## 15단계 — 전체 흐름과 화면

**목표** 질문 하나가 화면에서 출발해 카드로 돌아오기까지를 파일 이름으로 따라갈 수 있게 된다.

**읽는 순서** 테스트를 먼저 읽고 구현을 읽으면 "이 코드가 무엇을 약속하는가"부터 알 수 있다.

| 순서 | 테스트 | 구현 | 볼 것 |
|---|---|---|---|
| 1 | `HubChatEngineTests` | `HubChatEngine.swift` | intent 별 세 갈래, 실패해도 던지지 않는 것 |
| 2 | `RecordingFileNameTests` · `RecordingPickerTests` | `RecordingFile.swift` · `RecordingPicker.swift` | 파일 이름에서 날짜·종류 읽기, 기준 시각의 파일 고르기 |
| 3 | `DriveMatcherTests` | `DriveMatcher.swift` | 경로의 첫 점·끝 점과 지명 반경 |
| 4 | `AIChatReducerTests` · `AIChatEffectRunnerTests` | `AIChatReducer.swift` · `AIChatEffectRunner.swift` | 상태와 실행을 나눈 구조, 답을 기다리는 동안 전송 막기 |
| 5 | — | `AIChatCoordinator.swift` | 엔진 조립, 카드를 눌렀을 때 여는 기존 화면 |
| 6 | `LocalModelTests` · `ModelCatalogTests` · `HuggingFaceClientTests` · `LocalModelStoreTests` | `LocalModel.swift` 외 3개 | 모델 받기 전 검사, 크기 대조, 설치 |

- 구조 규칙: `.claude/rules/swiftui_architecture.md` (Reducer · Store · Effect), `.claude/rules/architecture.md`
- 모델 받기에 쓰는 서비스: [Hugging Face Hub 의 모델 저장소 설명](https://huggingface.co/docs/hub/models-the-hub),
  [mlx-community/Qwen3-0.6B-4bit](https://huggingface.co/mlx-community/Qwen3-0.6B-4bit)
- 책: 9장 도입부(LLM 애플리케이션에 모델 말고 무엇이 필요한가), 3.2.1 모델 허브.

**돌려 볼 것** 단위 테스트(시뮬레이터). 빌드는 직접 돌린다.

```shell
xcodebuild test -project Hub.xcodeproj -scheme Hub-Dev \
  -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:HubDevTests/HubChatEngineTests
```

**스스로 답해 볼 것** — 여기까지 왔으면 아래를 막힘 없이 설명할 수 있어야 한다.
1. "어제 9시 30분 영상 보여줘"가 영상 카드가 되기까지 거치는 타입과 함수를 순서대로.
2. 지금 iPhone 14 에서 채팅이 안 되는 이유와, 되게 하려면 고쳐야 하는 세 곳.
3. 모델이 쓴 글이 사용자에게 그대로 보이는 경우는 언제 하나뿐인가.

<details><summary>답</summary>

1. `AIChatReducer`(`.sendTapped` → `.ask`) → `AIChatEffectRunner` → `HubChatEngine.respond` → `HubQueryParsing.parse`(`HubQueryPrompt.userPrompt` → 모델 → `HubQueryDTO` → `HubQueryMapper.map` → `HubQuery`) → `HubQueryResolver.window` → 파일 목록 → `RecordingPicker.file` → `HubChatAnswer`(`.videos`, `.video` 카드) → `.answered` → 화면.
2. FM 은 Apple Intelligence 미지원 기종이라 `.deviceNotEligible` 이고, MLX 로 넘어가는 연결이 아직 없다. 고칠 곳: `AIChatAvailability.current()`(MLX 분기), `AIChatReducer.submit` 의 `backend == .foundationModels` 조건, `AIChatCoordinator.makeParser()`·`makeAnswerer()`. 모델 받기 화면도 필요하다.
3. 설정 안내(`HubChatReply.guide(text:)`). 나머지 답 문장은 앱에 미리 있는 문구다.
</details>

## 참고 자료를 고른 기준

- **teddylee777/machine-learning** 은 Python 기초(0단계), 경사하강법(1단계), 어텐션(2단계), 데이터 나누기와 평가지표(9단계)에 썼다.
  이 저장소는 고전적 머신러닝과 딥러닝 기초가 중심이고 LLM·RAG·LoRA 는 다루지 않는다.
- LLM 쪽 한국어 자료는 같은 저자의 **teddylee777/langchain-kr** 에서 골랐다(5·6·8·9단계). 다만 LangChain 과 서버 모델을 쓰는
  예제라 우리 코드와 도구가 다르다. 개념을 배우는 용도다.
- 온디바이스(MLX · Foundation Models)는 한국어 자료가 적어 Apple 의 WWDC25 세션과 공식 문서, mlx-lm 소스를 적었다.
- **「LLM을 활용한 실전 AI 애플리케이션 개발」** 은 목차와 장별 소개만 보고 대응시켰다. 본문은 확인하지 못했다.
- **Hugging Face Learn** 은 강좌 목차(GitHub 의 `_toctree.yml`)로 절을 고르고, 2026-11-27 에 각 페이지가 열리고
  설명에 적은 주제어(예: prefill, merge, grammar)가 본문에 있는 것까지 확인했다. 본문 전체를 읽지는 않았다.
- **Datawhale** 은 happy-llm · llm-cookbook · self-llm 세 저장소의 파일 목록과 각 글의 절 제목으로 골랐고, 인용한 글
  일부(Qwen3 07·08, C2-3·7·9·10, C4-3, MLX 소개)는 앞부분을 읽어 내용을 확인했다. 링크는 2026-11-27 에 열리는 것을 확인했다.
  처음 요청에 있던 `hello-llm` 저장소는 datawhalechina 에 없어 이름이 가장 가까운 happy-llm 으로 대신했다.
- **NatashaTheRobot 글**(2026-11-23)은 2026-11-27 에 본문 전체를 읽었다. 비용·정답률은 저자의 주장이고 따로 확인하지 않았다.
  글 끝에서 파는 유료 Starter 는 넣지 않았다.
- 링크는 2026-11-16 에 열리는 것을 확인했다. 위키독스 링크만 자동 확인이 막혀 langchain-kr 의 README 에 적힌 주소를 그대로 옮겼다.
  유튜브 영상은 제목·채널·길이를 확인했다. 영상과 Apple 자료는 영어다.
