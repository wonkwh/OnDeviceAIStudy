# AI 채팅 — MLX 백엔드 설계 (plan Task 11 구체화)

작성 2026-11-06 · 브랜치 `feature/ai_chat` · 상태: **S1 진행 중**

## 목표

Foundation Models(FM)를 못 쓰는 경우(iOS 18–25, Apple Intelligence 미지원 기기, AI 꺼짐, 미지원 언어)에도
AI 채팅이 동작하게 한다. Hugging Face 에서 MLX 모델을 받아 기기에서 돌린다. 모델 받기 방식은 FlowDown 을 따른다.

## 결정 사항 (2026-11-06 사용자 확인)

| 항목 | 결정 |
|---|---|
| 백엔드 | FM 을 쓸 수 있으면 FM, 아니면 MLX (plan 방안 B) |
| 모델 선택 | 검증 목록(추천) + HF 검색. 기기 RAM 기준 크기 제한 |
| 받기·관리 화면 | AI 채팅 화면 안 — 미지원 안내 자리에 "모델 받기", 내비 바 메뉴에서 변경·삭제 |
| 셀룰러 받기 | 막지 않는다. 받기 전에 총 크기를 보여 주고 확인을 받는다 |

## 흐름

```
채팅 진입 ─ AIChatAvailability.current()
  ├─ FM 사용 가능 ............................ .foundationModels
  ├─ 선택된 MLX 모델이 받아져 있음 ........... .mlx(modelID)
  └─ 그 외 .................................. .unavailable(.modelNotDownloaded) → "모델 받기" 버튼

모델 시트
  추천(검증 목록) ─┐
  HF 검색 ─────────┼─ 선택 → config.json 확인(지원 구조?) → 파일 목록·크기(tree API)
                   │        → 크기 제한 → (셀룰러면 크기 표시·확인) → 파일별 다운로드(진행률·재시도·취소)
                   │        → 임시 폴더 → Application Support/AIChat/Models/<repo> 로 이동
  받은 모델 ───────┴─ 선택 / 삭제
```

## FlowDown 에서 그대로 가져오는 것

| 항목 | FlowDown 구현 | Hub |
|---|---|---|
| 검색 | `GET huggingface.co/api/models?full=full&author=mlx-community&filter=text-generation&sort=downloads&search=…` | 같음 |
| 파일 목록 | `GET api/models/{repo}/tree/main?recursive=1` → `type == "file"` 만, `size` 합 = 총 크기 | 같음 |
| 파일 받기 | `{repo}/resolve/main/{path}`, 파일별 5회 재시도(진행이 있었던 실패는 횟수에서 뺌), 이미 받은 파일은 건너뜀, 취소 | 같음. 다운로더는 Digger 대신 URLSession(새 의존성 없음) |
| 저장 | 임시 폴더 `content/` + `manifest/info.plist` → 모델 폴더로 이동 | 같은 구조, manifest 는 JSON |
| 로드 | `LLMModelFactory.shared.loadContainer(from: 폴더, using: TokenizerLoader)` + swift-tokenizers `AutoTokenizer` 브리지 | 같음 |
| 메모리 권한 | `com.apple.developer.kernel.increased-memory-limit` | 같음 |

## FlowDown 과 다르게 하는 것

| 항목 | 이유 | Hub |
|---|---|---|
| mlx-swift-lm 를 `main` 브랜치로 참조 | 빌드가 재현되지 않는다 | **태그 3.32.3 고정** |
| 아무 모델이나 허용 | 채팅은 질문을 정확한 JSON(`HubQueryDTO`)으로 옮겨야 한다 | 검증 목록을 위에, 검색 결과에는 "검증 안 됨" 표시 |
| 크기 제한 없음 | 큰 모델은 메모리 초과로 앱이 종료된다 | 총 크기 ≤ 실제 메모리 × 0.25 (6GB → 1.5GB, 8GB → 2GB). 초기값이며 실측 후 조정 |
| 구조 확인 없음 | 지원하지 않는 구조는 다 받은 뒤 로드에서 실패한다 | 받기 전에 `config.json` 의 `model_type` 을 지원 목록과 대조 |
| 출력 형식 | 범용 채팅이라 자유 문장 | **`MLXGuidedGeneration`** 으로 출력을 `HubQueryDTO` JSON Schema 에 강제 — plan 의 `JSONObjectExtractor` 대체 |
| 메모리 경고 대응 없음 | 백그라운드에서 강제 종료 | 메모리 경고·백그라운드 진입 시 모델 해제 + `MLX.Memory.clearCache()` |
| 블랙박스 AP 연결 중 | 인터넷이 없어 실패 | `Current.isConnect` 면 받기를 막고 안내 |

## 의존성

| 패키지 | 버전 | product | 비고 |
|---|---|---|---|
| ml-explore/mlx-swift-lm | 3.32.3 (exact) | MLXLLM, MLXLMCommon, MLXGuidedGeneration | iOS 17+. MLXGuidedGeneration 은 XGrammar C++ 를 함께 빌드한다 |
| ml-explore/mlx-swift | mlx-swift-lm 이 지정(0.32.x) | (간접) | Metal 셰이더 포함 — 앱 크기 증가 |
| DePasqualeOrg/swift-tokenizers | 0.4.3 | Tokenizers | FlowDown 과 같은 토크나이저 로더 |
| swift-syntax | mlx-swift-lm 이 지정 | (해석만) | 매크로 product 를 쓰지 않으면 빌드하지 않는다 |

외부 작업: Apple Developer 에서 App ID 에 *Increased Memory Limit* capability 추가 → 프로비저닝 프로파일 재생성.

## 구조 (새 파일)

| 층 | 파일 | 책임 |
|---|---|---|
| Domain | `Domain/Entities/AIChat/LocalModel.swift` | 모델 메타(id·크기·받은 시각·검증 여부), 크기 제한 정책(순수) |
| Domain | `Domain/UseCases/AIChat/ModelCatalog.swift` | 검증 목록 + 검색 결과 합치기·정렬(순수) |
| Data | `Data/AIChat/MLX/HuggingFaceClient.swift` | 검색·tree·config.json·파일 받기(URLSession, 진행률·재시도·취소) |
| Data | `Data/AIChat/MLX/LocalModelStore.swift` | 저장 위치·manifest·목록·삭제·선택된 모델, 백업 제외 |
| Data | `Data/AIChat/MLX/MLXChatBackend.swift` | actor. 컨테이너 1개 캐시, `HubQueryParsing`·`HubGuideAnswering` 구현, guided JSON, 메모리 정리 |
| Data | `Data/AIChat/AIChatAvailability.swift` (수정) | `.mlx(modelID)`, `.modelNotDownloaded` |
| Presentation | `AIChatScene/Reducer/AIChatModelReducer.swift` | 모델 시트 상태(추천·검색·진행·받은 목록) |
| Presentation | `AIChatScene/AIChatModelEffectRunner.swift` | 검색·받기·삭제·선택 실행 |
| Presentation | `AIChatScene/View/AIChatModelView.swift` | 모델 시트 화면 |
| Presentation | `AIChatReducer.swift` (수정) | `backend.isReady`, "모델 받기" 탭 → `.openModels` Effect |

## 검증 목록 (스파이크로 확정)

후보 `mlx-community/Qwen3-1.7B-4bit`, `mlx-community/gemma-3-1b-it-qat-4bit`.
plan Task 0 평가셋(20문항)을 MLX 백엔드로 돌려 **intent 20/20 · 전체 17/20 이상 · 질문당 3초 이하(iPhone 15 기준) · 최대 메모리**를
기록하고, 통과한 것만 목록에 넣는다.

## 진행 순서 (슬라이스마다 승인)

| # | 내용 | 검증 |
|---|---|---|
| S1 | SPM 3개 + entitlement 추가, 평가셋으로 후보 모델 실측(스파이크) | 실기 빌드·평가 결과를 이 문서에 기록 |
| S2 | `HuggingFaceClient`·`LocalModelStore`·크기 제한·카탈로그 (TDD) | 단위 테스트(응답 JSON 픽스처) |
| S3 | `MLXChatBackend` (guided JSON 파서·가이드 답변·메모리 정리) | 실기 평가셋 |
| S4 | 가용성·리듀서·모델 시트 UI | 리듀서 테스트 + 시뮬레이터 화면 |
| S5 | 실기 매트릭스 — plan Task 10 표를 iOS 18 기기에서 반복, 10회 연속 질문 후 메모리 최대치·강제 종료 여부 | Instruments |

전용 모델(미세조정)은 별도 트랙 T1–T4 로 진행한다 — 아래 절.

## 전용 모델 트랙 (미세조정) — 2026-11-10 추가

범용 모델(1GB 안팎)을 받는 대신, 질문 파싱만 하도록 미세조정한 소형 모델을 검증 목록 첫 줄에 둔다.
받기·저장·로드·JSON 강제는 S2–S4 를 그대로 쓴다. 이 트랙의 작업은 대부분 앱 밖(데이터·학습)이다.

### 결정 사항 (2026-11-10 사용자 확인)

| 항목 | 결정 |
|---|---|
| 방식 | 소형 LLM 을 LoRA 로 미세조정 → 합치기(fuse) → 4bit MLX 폴더 |
| 언어 | **영어만.** 한국어 등 다른 언어는 이 트랙 범위 밖이다 |
| 학습 대상 | 질문 → `HubQueryDTO`(파서). 안내 답변은 학습하지 않고 T3 에서 품질만 잰다 |

택하지 않은 방식: FM 어댑터(시스템 모델 버전마다 재학습, 툴킷 26.0.0 이 마지막 릴리스),
인코더 분류기 + Core ML(새 추론 경로가 필요하고 안내 답변을 못 만든다).

### 학습 데이터

- 한 줄 형식(mlx-lm chat): system = 전용 지시문, user = `HubQueryPrompt.userPrompt` 출력과 글자 단위로 같은 형식,
  assistant = `schemaFields` 순서의 JSON(말하지 않은 값은 null).
- 만드는 순서: 칸 값을 무작위로 뽑는다 → 그 값에 맞는 영어 질문을 문형·낱말 목록에서 조립한다.
  라벨이 구성상 정확해 재파싱 필터가 필요 없고, 외부 API 없이 같은 seed 로 같은 결과가 나온다.
  큰 LLM 으로 바꿔 쓰기를 더하는 것은 T3 정확도가 모자랄 때 한다(T2 기록 참고).
- 꼭 넣을 것: `previous result:` 줄이 있는 경우와 없는 경우, 여러 `today:` 날짜·요일, intent `unknown`(범위 밖 질문),
  12시간제(6 pm → 18), 장소명 원문 그대로.
- 평가셋 문항과 겹치는 문장은 넣지 않는다. 합성 데이터만 쓰고 사용자 질문·주행 기록은 쓰지 않는다.
- 라벨 규칙은 영어 평가셋과 같게 둔다(아래).

| 칸 | 규칙 |
|---|---|
| hour·minute | 24시간제. 분을 말하지 않으면 minute 0 |
| period | 시간대 낱말(morning·afternoon·evening·night·commute)을 말했을 때만. am·pm·noon 만으로는 비운다 |
| 출퇴근 | drive to work·on my way to work → morningCommute, way home from work → eveningCommute. origin·destination 은 비운다 |
| daysAgo | today 0, yesterday 1, the day before yesterday 2, N days ago N. 요일 표현(last Friday)은 비운다 |
| origin·destination | 고유명사와 home 을 쓴 그대로. work 는 출퇴근 표현과 라벨이 엇갈려 학습 데이터에서 장소로 쓰지 않는다 |
| enum 칸 | period·event·reference 는 스키마상 null 을 못 쓴다 — 말하지 않았으면 any·any·none |
| event | accident·crash·collision·impact·near miss·hard braking·sudden stop·bump·hit → impact |
| reference | that·then·the above 로 직전 결과를 가리키면 previous |
| topic | 질문에 나온 설정·기능 명사구 그대로(관사·동사 제외) |

### 슬라이스 (단계마다 승인)

| # | 내용 | 검증 |
|---|---|---|
| T1 | 영어 평가셋 `HubDevTests/Fixtures/ai_chat_eval_en.json`(학습에 쓰지 않는 100문항 이상). `MLXQueryParserEvalTests` 가 평가셋을 골라 돌게 한다. S1 후보 2개의 영어 기준선 측정 | 실기 결과를 아래 표에 기록 |
| T2 | 데이터 생성 스크립트 → `train.jsonl`·`valid.jsonl` | intent·칸별 건수, 평가셋 중복 0건, Swift 스키마와 대조 |
| T3 | base 후보별 LoRA 학습 → fuse → 4bit. Mac 에서 영어 평가셋 정확도와 안내 답변 품질 | 통과 기준의 정확도 항목 |
| T4 | 모델 올리기, 검증 목록 첫 줄, 전용 지시문 연결. 실기 측정 | 통과 기준 전부. 실패 문항 유형은 T2 로 돌려 보강 |

- 순서: T1 은 S1(실기 빌드) 뒤. T2·T3 은 앱 코드와 무관해 S2–S4 와 함께 갈 수 있다. T4 는 S2·S3 뒤.
- 통과 기준(초기값): 영어 평가셋 intent 100% · 전체 85% 이상(기존 17/20 과 같은 비율) · 질문당 3초 이하 ·
  정확도가 T1 기준선 이상 · 총 크기가 범용 후보보다 작을 것.
- base 후보: Gemma 3 270M, Qwen3 0.6B. 정확한 repo, mlx-swift-lm 3.32.3 의 `model_type` 지원, 상용 배포 조건은 T3 전에 확인한다.

```shell
# mlx-lm LORA.md 기준. --data 폴더에 train.jsonl·valid.jsonl
mlx_lm.lora --model <base> --train --data <data_dir> --iters 600
mlx_lm.fuse --model <base>   # adapters/ → fused_model/
```

| 모델 | 평가셋 | 기기 | intent | 전체 | 첫 질문 | 평균 | 가이드 | 최대 메모리 | 크기 |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit (기준선) | en | | | | | | | | |
| gemma-3-1b-it-qat-4bit (기준선) | en | | | | | | | | |
| 전용 모델 (base 미정) | en | | | | | | | | |

### T1 기록 (2026-11-10)

- 영어 평가셋 `HubDevTests/Fixtures/ai_chat_eval_en.json` 112문항 — video 40 · drive 28 · settingsHelp 26 · unknown 18.
  형식·enum 값·장소명과 topic 이 질문 안에 있는지는 스크립트로 확인했다.
- `MLXQueryParserEvalTests` 가 후보마다 ko·en 을 차례로 돌고 `[EVAL][repo][en]` 로 출력한다.
  평가셋마다 모델을 내려 "첫 질문"에 로드 시간이 들어간다.
- "전체"는 topic 을 유무만 비교한다(11-10 결정) — topic 은 검색어로만 쓰여(`HubChatEngine`) 표현이 달라도 틀린 답이 아니다.
  FM 평가와 ko 평가셋(S1 의 17/20)에도 같은 비교를 쓴다(`AIChatEvalCase.matches`).
- 기준선은 지금 지시문(`HubQueryPrompt.instructions`, 한국어 예시) 그대로 잰 값이다(11-10 확인).
- last night·tonight 은 평가셋과 학습 데이터에 넣지 않는다(11-10 확인) — `.night` 는 0–6시라 말뜻(저녁~자정)과 어긋난다.
- 남은 것: 실기 빌드·실행 후 위 표 채우기(S1 표의 ko 값도 같은 실행에서 나온다).

### T2 기록 (2026-11-13)

- `Scripts/ai_chat_train/generate_dataset.py` (표준 라이브러리만 사용). 산출물 `Scripts/ai_chat_train/data/` 는 git 에 넣지 않는다.
- 기본 6,000건(train 5,700 · valid 300): video 2,193 · drive 1,707 · settingsHelp 1,200 · unknown 900.
  이 중 직전 결과를 가리키는 질문 420건, `previous result:` 줄이 붙은 것 1,479건, 서로 다른 질문 5,526개.
- 11-16 v2: 시각이 놓이는 자리 세 가지(뒤·앞·전치사 없이, 명사 앞 "the 4:45 pm clip")와
  this·it 이 있어도 칸을 채우지 않는 설정·범위 밖 문장을 더했다. 위 건수는 v2 기준이다.
- 실행할 때마다 확인하는 것: `KEYS`·enum 값이 `HubQueryPrompt.schemaFields`·`HubQuery.swift` 와 같은지,
  행마다 키 순서·값 범위·장소명과 topic 이 질문 안에 있는지, 영어 평가셋 문항과 겹치지 않는지(겹친 후보 327개 버림).
- 답 형식은 공백 없는 JSON 이다. 앱의 문법 강제(XGrammar)는 기본값 `any_whitespace = true` 로 컴파일되므로
  (`MLXCXGrammar/shim.cc` 의 `CompileJSONSchema(s)`) 이 형식을 그대로 낼 수 있다.
- 지시문(system)은 스크립트의 `SYSTEM_PROMPT` 한 문단이다. T4 에서 앱이 전용 모델에 같은 문자열을 보내야 한다.
- 한계: 평가셋과 생성기의 문형을 같은 작성자가 썼다 — 겹친 후보 295개가 그 증거다. 평가 점수가 실제보다
  높게 나올 수 있으므로, T3 결과를 볼 때 다른 사람이 쓴 문장 몇십 개로 한 번 더 확인한다.

```shell
python3 Scripts/ai_chat_train/generate_dataset.py            # --count 6000 --seed 7
```

### T3 기록 (2026-11-16)

환경: M2 Max 32GB · macOS 27.2.1 (26B131) · Python 3.14.5 · mlx 0.32.4 · mlx-lm 0.32.2.
아래 수치는 모두 Mac 에서 문법 강제 없이 잰 값이다(`Scripts/ai_chat_train/evaluate.py`). 기기 수치가 아니다.

**학습 설정** — LoRA rank 8 · scale 20 · 전 층 · `--mask-prompt` · adam lr 1e-4 · 배치 8 ·
2,000 스텝 · seed 7 · max-seq 512. base 는 bf16 로 받아 학습하고, 합친 뒤 양자화했다.
이번 실행은 `--num-layers -1` 이었다. 아래 명령은 같은 뜻의 28 로 적었다(이유는 아래 "결정" 참고).

```shell
cd Scripts/ai_chat_train && uv sync   # pyproject.toml: mlx-lm
# base: mlx-community/Qwen3-0.6B-bf16 을 runs/base/ 에 받는다
AGX_RELAX_CDM_CTXSTORE_TIMEOUT=1 uv run mlx_lm.lora --model runs/base/Qwen3-0.6B-bf16 --train --data data \
  --adapter-path runs/qwen3-0.6b/adapters-v2 --iters 2000 --batch-size 8 --num-layers 28 --mask-prompt \
  --learning-rate 1e-4 --steps-per-eval 500 --val-batches -1 --save-every 500 --max-seq-length 512 --seed 7
uv run mlx_lm.fuse --model runs/base/Qwen3-0.6B-bf16 --adapter-path runs/qwen3-0.6b/adapters-v2 \
  --save-path runs/qwen3-0.6b/fused-bf16
uv run mlx_lm.convert --hf-path runs/qwen3-0.6b/fused-bf16 --mlx-path runs/qwen3-0.6b/fused-4bit -q --q-bits 4
uv run python evaluate.py --model runs/qwen3-0.6b/fused-4bit [--eval eval_independent_en.json] [--guide]
```

- `AGX_RELAX_CDM_CTXSTORE_TIMEOUT=1` 이 없으면 화면이 켜진 Mac 에서 학습이 몇 스텝 만에
  `kIOGPUCommandBufferCallbackErrorImpactingInteractivity` 로 죽는다(mlx#3267, wontfix). 넣은 뒤로는 끝까지 돈다.
- 평가셋 두 개: 내 평가셋 112문항(`ai_chat_eval_en.json`)과 **독립 평가셋 80문항**(`Scripts/ai_chat_train/eval_independent_en.json`).
  독립셋은 생성기·내 평가셋을 보지 않은 다른 작성자가 라벨 규칙만 받고 썼다. 독립셋의 오답으로는 생성기를 고치지 않는다.

| 모델 | 데이터 | 내 평가셋 전체 | 독립셋 전체 | 독립셋 intent | 크기 |
|---|---|---|---|---|---|
| Gemma 3 270M, 미세조정 전 | — | 0/112 (JSON 형식 112건 깨짐) | — | — | 906MB (bf16) |
| Gemma 3 270M + LoRA | v1 | 103/112 | 68/80 | 75/80 | |
| Gemma 3 270M + LoRA | v2 | 109/112 | 69/80 | 75/80 | |
| Qwen3 0.6B + LoRA | v1 | 110/112 | 76/80 | 77/80 | |
| Qwen3 0.6B + LoRA | v2 | 112/112 | 76/80 | 77/80 | 1,160MB (bf16) |
| Qwen3 0.6B 합친 뒤 8bit | v2 | 112/112 | 76/80 | 77/80 | 630MB |
| Qwen3 0.6B 합친 뒤 6bit | v2 | 112/112 | 76/80 | 77/80 | 473MB |
| **Qwen3 0.6B 합친 뒤 4bit** | v2 | 112/112 | 77/80 | 77/80 | **331MB** |
| Qwen3 0.6B 4bit base + 어댑터(합치지 않음) | v2 | 112/112 | 76/80 | 77/80 | 331MB + 20MB |
| Qwen3 0.6B 합친 뒤 4bit, 5,000 스텝 (11-27) | v3 | 105/112 | 67/80 | 76/80 | |
| Qwen3 0.6B 합친 뒤 4bit, 2,500 스텝 (11-27) | v3 | 112/112 | 75/80 | 76/80 | |
| Qwen3 0.6B 합친 뒤 4bit, 2,000 스텝 (11-27) | v4 | 112/112 | 75/80 | 78/80 | |

확인한 것:
- **base 는 Qwen3 0.6B.** 독립셋에서 Gemma 270M 보다 8~9문항 더 맞는다.
- **4bit 로 충분하다.** 4bit 출력이 bf16 과 다른 문항은 192개 중 3개이고 정확도는 떨어지지 않았다. 8bit 는 전부 같다.
  양자화에서 빠진 Linear 층은 없다(4·6·8bit 모두 0개, 4.501 bpw).
- **template 일치.** 학습 토큰열이 앱 추론 프롬프트(`enable_thinking` false)로 시작한다 — 두 base 모두 토큰 ID 로 확인.
  Swift 쪽(swift-tokenizers)이 같은 토큰열을 만드는지는 T4 에서 실기로 확인한다.
- **v2 보강은 내 평가셋에만 효과가 있었다.** v1 → v2 로 내 평가셋은 올랐고(Qwen 110 → 112, Gemma 103 → 109)
  독립셋은 그대로다(Qwen 76 → 76, Gemma 68 → 69). 내 평가셋 점수는 실제보다 높게 나온다 — 독립셋을 기준으로 본다.
  v2 는 여러 변경(시각 위치, this·it 방지 문장, noon 비중)을 한 번에 넣어 어느 것이 효과였는지는 가르지 못한다.
- **독립셋에서 틀린 3문항은 모두 video 를 drive 로 읽은 것**이다: "I want to watch yesterday's drive to Costco",
  "Can you play back the trip from home to Brighton? I want the video, not the map."(Brighton 을 Brightwell 로 씀),
  "Show the sudden stop on the motorway at 8:05 am today". drive·trip 같은 낱말이 있는 영상 요청이 약하다.
- **v3(Claude 바꿔 쓰기, 11-27)는 독립셋을 올리지 못했다.** 5,000 스텝은 과학습이다 — val 이 0.000 → 0.007 로 오르고
  daysAgo 2 → 1, Brooklyn → "Broth" 같은 오답이 생겼다. val 이 가장 낮은 2,500 스텝을 골랐다(독립셋으로 고르지 않았다).
  video 를 drive 로 읽는 오답은 3 → 1 로 줄었고, unknown·settingsHelp 경계 오답 3건과 origin 에 "none" 글자 1건이 새로 생겼다.
- **v4(11-27) = v3 + unknown 경계 템플릿(앱 추천·폰 설정·차량 경고등) + 평가셋 세 개를 학습 문장에서 제외.** 첫 독립셋의
  오답을 보고 생성기를 고쳤으므로 첫 독립셋은 더 이상 독립이 아니다. 새 독립셋 80문항
  (`eval_independent_v2_en.json`, Sonnet 5.5 가 라벨 규칙만 받고 씀, "this afternoon" 1건만 daysAgo 0 으로 고침)을 기준으로 본다.

  | 새 독립셋 | 전체 | intent |
|---|---|---|
| v2 | 71/80 | 72/80 |
| v3 2,500 | 70/80 | 72/80 |
| **v4 2,000** | **75/80** | **78/80** |

  v2 의 오답 7건이 폰·차량 질문을 settingsHelp 로 읽은 것이었고 v4 는 3건이다. v4 의 새 오답: unknown 질문에 origin·period 를
  채움(intent 는 맞음), "dashcam Wi-Fi" 연결을 unknown 으로 읽음, Albany → "Albaney". 80문항에서 4문항 차이다.
- **합친 모델은 안내 답변을 못 한다.** `HubGuidePrompt` 로 물으면 문장 대신 깨진 JSON 을 낸다(5문항 중 5).
  미세조정 전 4bit base 는 guide 조각이 주어진 4문항에 쓸 만한 답을 했다.

통과 기준 대비: 크기(331MB, 범용 후보보다 작음)와 전체 85% 이상(독립셋 96%)은 충족. intent 100% 는 독립셋에서
77/80 으로 미충족. 질문당 3초와 T1 기준선 비교는 기기 측정이 필요하다(Mac 에서는 4bit 가 문항당 0.16초).

**T4 전에 정할 것 — 모델을 내보내는 형태**

| | A. 합친 4bit 한 개 | B. 4bit base + 어댑터 |
|---|---|---|
| 받는 크기 | 331MB | 331MB + 20MB |
| 질문 파싱 | 된다. Mac 에서 문항당 0.16초 | 된다. Mac 에서 0.52초(어댑터를 따로 계산) |
| 안내 답변 | 못 한다 — 검색된 guide 본문을 그대로 보여 준다 | 어댑터를 내리고 base 로 답한다 |
| 모델 갱신 | 331MB 를 다시 받는다 | 어댑터 20MB 만 다시 받는다 |
| 앱 코드 | 안내를 LLM 없이 보여 주는 분기 | `LoRAContainer` 의 load·unload (mlx-swift-lm 3.32.3 에 있다) |

`runs/` 는 git 에 넣지 않는다(5.1GB). 어댑터(`adapters-v2`, 20MB)가 원본이고 합친 모델은 다시 만들 수 있는 산출물이다.

**결정 (2026-11-16 사용자 확인): B — 4bit base + 어댑터.** 결정 뒤 확인한 것:

- **base 는 공개 repo 를 그대로 쓸 수 있다.** `mlx-community/Qwen3-0.6B-4bit`(351MB, apache-2.0, group 64·4bit,
  revision `73e3e38d981303bc594367cd910ea6eb48349da8`)에 어댑터를 얹어 내 평가셋 112/112, 독립셋 76/80(intent 77/80) —
  직접 양자화한 base 와 같다. 우리가 올릴 것은 어댑터 19MB 뿐이다. 받을 때는 `main` 이 아니라 위 revision 을 지정한다.
- **`adapter_config.json` 의 `num_layers` 는 실제 층 수(28)로 쓴다.** 학습을 `--num-layers -1` 로 하면 설정에 -1 이 남는데,
  Swift 로더는 `loraLayers.suffix(numLayers)` 를 부르므로(`LoRAContainer.swift`) 음수면 앱이 죽는다.
  앞으로는 `--num-layers 28` 로 학습한다. 지금 어댑터는 값을 28 로 고친 `runs/qwen3-0.6b/adapter-ship/` 를 만들어 다시 채점했다(76/80, 같음).
- **Swift 로더가 읽는 형식과 맞는다.** `LoRAContainer.from(directory:)` 는 `adapter_config.json`
  (`fine_tune_type`·`num_layers`·`lora_parameters.rank·scale`)과 `adapters.safetensors` 를 읽는다. 대상 모듈은 설정에
  `keys` 가 없으면 층 안의 모든 Linear 이고(`LoRAModel.swift`), 어댑터 가중치도 그 일곱 모듈(q·k·v·o_proj, gate·up·down_proj)이다.
  `scale` 은 Python 기본 20, Swift 기본 10 이라 설정 파일이 반드시 함께 가야 한다. 실제 로드는 실기에서 확인한다(T4).

**T4 에서 할 일 (B 기준)**

| # | 내용 |
|---|---|
| 1 | 검증 목록 항목에 base repo·revision, 어댑터 위치, 지시문 종류를 둔다 |
| 2 | `MLXChatBackend`: 파싱 전에 어댑터를 올리고(`load(adapter:)`) 전용 지시문(`SYSTEM_PROMPT`)을 쓴다. 안내 답변 전에 내린다(`unload(adapter:)`) |
| 3 | 실기 확인: 어댑터 로드 성공, Swift 가 만든 토큰열이 Python 과 같은지, 영어 평가셋 정확도·지연·메모리 |

### T4 기록 (2026-11-16) — 코드 완료 · 미빌드 · 실기 측정 대기

- **어댑터를 앱 번들에 넣었다.** `Hub/Resources/AIChat/ai_chat_parser_adapter.safetensors`(19MB, sha256 `8a653edac9471e82…`, 11-27 v4 로 교체)와
  `ai_chat_parser_adapter.json`(`num_layers` 28). `runs/qwen3-0.6b/adapter-ship-v4/` 의 사본이다(v2 는 `adapter-ship/`).
  공개 4bit base + 이 어댑터: 내 평가셋 112/112, 첫 독립셋 75/80, 새 독립셋 78/80(intent 79/80). 같은 조건의 v2 는 새 독립셋 71/80.
- **`MLXChatBackend`** — `init(modelDirectory:calendar:parserAdapter:)`. 어댑터를 주면 파싱 동안만 올리고
  (`LanguageModel.perform(with:)`, 실패해도 내린다) 전용 지시문을 쓴다. 안내 답변은 어댑터 없이 base 로 돈다.
  어댑터를 주지 않으면 전과 같다.
- **전용 지시문** `HubQueryPrompt.dedicatedInstructions`. 학습 데이터의 system 과 같은지 세 곳에서 본다:
  단위 테스트(`HubQueryPromptTests`), 생성기 실행 시 Swift 소스 대조, 실기 토큰열 대조(아래).
- **실기 테스트** `MLXQueryParserEvalTests`
  - `testCandidates` — 범용 후보 2개(ko·en)에 더해 `Qwen3-0.6B-4bit`(revision 고정) + 어댑터를 영어 평가셋으로 잰다.
    출력 태그는 `[EVAL][mlx-community/Qwen3-0.6B-4bit+adapter][en]`.
  - `testDedicatedParserPromptMatchesTraining` — 앱이 만든 파서 프롬프트 토큰열이 Python 이 만든 것과 같은지 단언한다.
    기대값 `HubDevTests/Fixtures/ai_chat_parser_prompt_tokens.json` 은 `evaluate.py --prompt-fixture` 로 만든다.
- 아직 연결하지 않은 것(S2·S4 가 먼저다): 검증 목록 항목(base repo·revision + 어댑터), `AIChatCoordinator` 의 백엔드 선택,
  영어가 아닌 언어의 미지원 안내(`AIChatAvailability` 에 MLX 분기를 넣을 때 기존 `.languageNotSupported` 로 처리).
- 빌드에서 확인할 것: `.safetensors` 가 앱 번들 리소스로 복사되는지 — `testCandidates` 의 "번들에 파싱 어댑터가 없다" 단언이 잡는다.

```shell
xcodebuild test -project Hub.xcodeproj -scheme Hub-Dev -destination 'platform=iOS,name=<기기 이름>' \
  -only-testing:HubDevTests/MLXQueryParserEvalTests
```

### 이 트랙의 열린 질문

1. ~~스크립트·학습 데이터를 둘 곳~~ → `Scripts/ai_chat_train/` (11-13 결정).
2. ~~데이터 생성에 쓸 큰 LLM~~ → Claude Opus 5.5 로 바꿔 쓴다(11-27, `paraphrase_dataset.py`, `claude -p`). 라벨은 원문 것을 쓰고
   라벨을 정하는 낱말이 원문과 같은 문장만 남긴다. v3 = 원문 6,000 + 바꿔 쓴 10,179줄.
3. ~~어댑터(19MB)를 둘 곳~~ → 앱 번들(11-16, 권장안으로 진행). 어댑터와 앱의 지시문·프롬프트 형식이 같은 릴리스로 묶인다.
   base 는 공개 repo 를 쓰므로 올릴 필요가 없다.
4. ~~영어가 아닌 질문이 오면~~ → 미지원 안내(11-16, 권장안으로 진행). S4 에서 `AIChatAvailability` 에 넣는다.
5. ~~지시문을 모델별로 고르는 방법~~ → 어댑터가 있으면 전용 지시문, 없으면 범용 지시문(`MLXChatBackend`, 11-16).
6. ~~안내 답변·내보내는 형태~~ → B, 4bit base + 어댑터 (11-16 결정).
9. ~~video 를 drive 로 읽는 오답을 생성기에 보강할지~~ → 독립셋을 새로 썼다(11-27, `eval_independent_v2_en.json`). 보강은 unknown 경계만 했다.
7. ~~"전체"를 topic 글자까지 볼지~~ → 유무만 비교 (11-10 결정).
8. ~~last night·tonight 의 라벨~~ → 평가셋·학습 데이터에서 뺀다 (11-10 확인).

## 열린 질문

1. 크기 제한 비율(× 0.25)은 S1 실측으로 정한다.
2. ~~셀룰러에서 받기~~ → 크기를 보여 주고 확인 (11-06 결정).
3. 검증 안 된 모델로 파싱이 계속 실패할 때 추천 모델로 바꾸라는 안내를 띄울지.

## S1 기록

- SPM: mlx-swift-lm 3.32.3(exact: MLXLLM·MLXLMCommon·MLXGuidedGeneration), swift-tokenizers 0.4.3(exact: Tokenizers),
  mlx-swift 0.32.3~(upToNextMinor: MLX — `import MLX` 를 쓰므로 명시). Hub 타깃에만 링크.
- `Hub.entitlements` 에 `com.apple.developer.kernel.increased-memory-limit` 추가 — **App ID capability 는 사용자가 켠다.**
  권한과 별개로 로드 직전 `os_proc_available_memory()` 가 (모델 크기 + 300MB) 보다 작으면 로드하지 않는다.
- `MLXChatBackend`(actor): guided JSON 파싱(`HubQueryPrompt.jsonSchema`, 속성 순서 intent 먼저), 가이드 답변
  (`HubGuidePrompt` — FM 과 공용), Qwen3 사고 모드 끔(`enable_thinking: false`), 생성 후 캐시 비움, `unload()`.
- 측정: `HubDevTests/MLXQueryParserEvalTests`(실기 전용) — 후보 2개를 Caches 에 받아 평가셋 정확도·첫 질문/평균 지연·
  가이드 답변 지연·최대 phys_footprint·모델 크기를 출력한다. 결과를 아래 표에 적는다.

| 모델 | 기기 | intent | 전체 | 첫 질문 | 평균 | 가이드 | 최대 메모리 | 크기 |
|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | | | | | | | | |
| gemma-3-1b-it-qat-4bit | | | | | | | | |

## S2 기록 (2026-11-16) — 코드 완료 · 단위 테스트 통과 · 프로젝트 빌드 미실행

| 파일 | 내용 |
|---|---|
| `Domain/Entities/AIChat/LocalModel.swift` | `ModelRepoID`·`ModelFilePath`(만들 때 검사), `ModelSource`, `LocalModel`, `ModelSizePolicy`, `ModelDownloadPlan` |
| `Domain/UseCases/AIChat/ModelCatalog.swift` | 추천 목록, 목록 합치기·정렬, 모델별 파서 방식 |
| `Data/AIChat/MLX/HuggingFaceClient.swift` | 검색·파일 목록·`model_type`·받기 |
| `Data/AIChat/MLX/LocalModelStore.swift` | 설치·목록·삭제·선택, 백업 제외 |

설계에서 구체화한 것:

- **원격에서 온 이름은 만들 때 검사한다.** 검색 응답의 저장소 이름과 파일 목록의 경로가 URL·폴더 경로에 쓰이므로,
  `ModelRepoID`·`ModelFilePath` 는 폴더를 벗어나는 문자열(`..`, 절대 경로, 빈 조각)로는 만들 수 없다.
  쓸 수 없는 경로가 하나라도 있으면 파일 목록 전체를 거부한다(`.malformedEntry`).
- **`ModelDownloadPlan` 이 있어야만 받고 설치할 수 있다.** 이 값은 지원 구조·크기 상한 검사를 통과해야 만들어진다
  (`ModelDownloadPlan.make`). 지원 구조 목록(`supportedModelTypes`)은 호출하는 쪽(S4)이 넘긴다.
- **받기** — `URLSession.download` + Task 취소. 파일마다 받은 크기를 목록의 크기와 대조하고, 다르면 저장하지 않는다.
  전송 오류만 다시 시도한다(이어받을 수 없는 실패 5회에서 중단, 이어받을 수 있으면 resume data 로 이어 받는다).
  HTTP 오류(401·404 등)와 크기 불일치는 바로 실패한다. 없는 저장소는 404 가 아니라 401 을 준다.
- **저장** — `<root>/<owner>/<name>/content` + `manifest.json`. 임시 폴더는 모델마다 고정된 위치라 중단된 받기를 이어 간다.
  같은 저장소의 다른 버전을 설치하면 이전 것은 지운다. 선택은 `<root>/selection.json`.
- **검증 여부·파서 방식은 저장하지 않는다.** 추천 목록(`ModelCatalog.verified`)에서 매번 찾는다 —
  목록이 앱 업데이트로 바뀌어도 기록과 어긋나지 않는다. 추천 목록의 revision 과 다른 버전은 범용으로 본다.
- **추천 목록** — 지금은 `mlx-community/Qwen3-0.6B-4bit`(revision 고정) + 번들 어댑터 한 줄. 실기 측정(T4)에서
  통과 기준을 못 넘으면 뺀다. 범용 후보 2개는 S1 측정 뒤에 넣는다.

검증:

- 단위 테스트 37개(`LocalModelTests` 12 · `ModelCatalogTests` 5 · `HuggingFaceClientTests` 10 · `LocalModelStoreTests` 10)를
  새 파일만 묶은 스크래치 Swift 패키지에서 macOS `swift test` 로 통과시켰다. 네트워크는 `URLProtocol` 로 대신했다.
  `HubDevTests`(스킴 `Hub-Dev`)로는 아직 돌리지 않았다.
- 실제 서버로 한 번 확인했다(스크래치 전용, 11-16): 검색, 파일 목록(11개), `model_type` = `qwen3`,
  작은 파일 9개 받기(4.5MB, 진행 보고 27회), 설치·선택·삭제.
- `MLXQueryParserEvalTests` 의 모델 받기를 `HuggingFaceClient` 로 바꿨다 — 실기 측정이 이 코드도 함께 탄다.

S4 로 넘긴 것: 셀룰러에서 크기 확인, 블랙박스 AP 연결 중 받기 막기(`Current.isConnect`), 지원 구조 목록을 넘기는 자리,
영어가 아닌 언어의 미지원 안내, `AIChatCoordinator` 의 백엔드 선택.
