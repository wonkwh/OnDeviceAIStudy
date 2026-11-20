# Hub AI 채팅 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**브랜치:** 별도 브랜치에서 구현한다(이 문서는 `feature/home_sync_nas` 에서 미커밋 상태로 작성, 2026-11-06).

**Goal:** 자연어 질문("어제 출근길 9시 30분 영상", "판교→인천 퇴근길에 사고날 뻔한 경로", "위 경우의 비디오",
"주차 녹화를 줄이려면")을 기기 내 LLM 으로 검색 조건으로 바꾸고, 앱이 단말 파일 목록·history/GPS DB·설정
가이드를 조회해 채팅 안에 영상 카드·지도 카드·설정 바로가기로 보여준다.

**Architecture:** LLM 은 질문을 `HubQuery`(의도 + 날짜·시각·시간대·지명·이벤트·직전 참조) 로 옮기는 일만 한다.
조회·매칭·결과 구성은 순수 Swift `HubChatEngine` 이 하고, 사용법 질문만 LLM 이 가이드 본문을 근거로 짧게 답한다.
화면은 SwiftUI Reducer 패턴(`swiftui_architecture.md`), 진입은 More 탭 행(기능 플래그 뒤).
LLM 백엔드는 `HubQueryParsing` · `HubGuideAnswering` 프로토콜 뒤에 두고 1차는 iOS 26 Foundation Models,
2차(Task 11)에 iOS 18–25 용 MLX 를 붙인다.

**Tech Stack:** Swift 5 모드 · SwiftUI(`Map`, iOS 17+) · FoundationModels(iOS 26) · MapKit `MKLocalSearch` ·
GRDB(기존 `SqlQuery`) · XCTest(`HubDevTests`, 스킴 `Hub-Dev`) · (Task 11) mlx-swift-lm

## 전체 흐름

```
사용자 입력
  │  AIChatReducer.sendTapped → Effect.ask(id, text, context)
  ▼
AIChatEffectRunner ── HubChatEngine.respond(to:context:)
                         │ 1. parser.parse → HubQueryDTO → HubQueryMapper → HubQuery   (LLM)
                         │ 2. HubQueryResolver.window → 검색 구간·시간대·기준 시각      (순수)
                         │ 3. 의도별 실행
                         │    video        : 파일 목록(연결 중=단말, 아니면 DOWNLOADED) → RecordingPicker
                         │    drive        : history DB → (지명) MKLocalSearch + DriveMatcher → 이벤트 파일 → GPS
                         │    settingsHelp : SettingsGuide.search → 현재 설정값 → answerer (LLM)
                         ▼
                      HubChatAnswer(reply, cards, context)
  ◄── Action.answered(id, answer) ── 카드 탭 → Effect.open(card) → Coordinator(VOD·설정·지도 시트)
```

## 결정 사항 (2026-11-06 사용자 확인)

| 항목 | 결정 |
|---|---|
| LLM | iOS 26 이상은 Foundation Models, 그 미만(iOS 18–25)은 MLX. 1차 출시는 FM 만, MLX 는 Task 11 |
| 영상 범위 | 블랙박스 연결 중이면 SD카드 목록(getfilelist), 아니면 폰에 내려받은 파일(`Documents/DOWNLOADED`) |
| "사고날 뻔" | 이벤트 녹화 파일(getfilelist type=1, 파일명 `EVT`) 기준. 위치는 그 시각의 GPS |
| 지명 | `MKLocalSearch` 로 좌표·반경 변환, 실패하면 지명은 버리고 날짜·시간대로만 검색 |
| 사용법 | 앱 번들 가이드 검색 + 연결 중이면 현재 설정값 + 설정 화면 해당 행 바로가기. 값은 바꾸지 않는다 |
| LLM 역할 | 의도·조건 추출만(방식 B). 조회 결과 문장은 앱이 로컬라이즈 문자열로 만든다 |

> **정정:** 브레인스토밍 중 "앱 최소 버전 iOS 15.6 이라 MLX(iOS 17+) 링크 불가"라고 했으나, 실제 Hub 타겟의
> `IPHONEOS_DEPLOYMENT_TARGET` 은 **18.0** 이다(15.6 은 프로젝트 기본값, CLAUDE.md 의 iOS 15 표기는 낡음).
> MLX 를 막는 버전 제약은 없다. 1차를 FM 만으로 가는 이유는 범위·모델 다운로드(약 1GB) 부담이다.

## 두 참조 앱에서 가져온 것 / 피한 것

| 출처 | 가져온 것 | 피한 것 |
|---|---|---|
| FlowDown | 백엔드를 프로토콜 뒤로(`ChatService`), 모델 하나만 캐시하는 coordinator, 출력 스트림을 UI 와 분리 | async 안 `DispatchSemaphore.wait()`, 매 토큰 전체 재 decode, GPTEncoder 로 토큰 추정 |
| PhoneClaw | 작은 모델은 "툴 선택"보다 "빈칸 채우기"가 안정적이라는 점, 직전 결과를 앱이 들고 있다가 후속 질문에 넘기는 방식 | 언어별 키워드 휴리스틱 하드코딩, 텍스트 `<tool_call>` 정규식 파싱, MainActor 위 거대 엔진, 메모리 경고 무대응 |

## Global Constraints

- Hub 타겟 iOS 18.0. FM 코드는 `#if canImport(FoundationModels)` + `@available(iOS 26.0, *)` 로 감싼다. Xcode 26 SDK 로 빌드한다(기존 `#available(iOS 26.0, *)` 코드가 있음).
- Swift 5 언어 모드(Hub 타겟 `SWIFT_VERSION = 5.0`), strict concurrency 설정 없음. 새 코드에서 `@unchecked Sendable` 을 쓰지 않는다.
- 새 bool 파라미터 금지(enum 사용). force unwrap·`try!` 금지, `try?` 로 에러를 삼키지 않는다(`general.md`).
- Alamofire 금지. 새 SPM 의존성은 Task 11(mlx-swift-lm) 외에는 추가하지 않는다.
- SwiftUI 화면은 Reducer·Store·Effect(`swiftui_architecture.md`): `reduce` 는 순수·동기, UUID·시간·로그 호출 금지.
- 주석 한국어 1~2줄, 함수 헤더는 swift-docc. AOS 근거 금지. 2 space · 100 col · `swift-format`
  (`Scripts/ncn.swift-format.config.json`).
- 로그는 `aiLogger`(Task 1 에서 추가), 태그 `[AICHAT][PARSE]` `[AICHAT][QUERY]` `[AICHAT][GUIDE]`. 질문 원문은 `.private` 로 남긴다.
- 문구는 로컬 키(`Localizable.swift` 의 "원격 시트 등록 전 로컬 키" MARK, `Localizable.xcstrings` ko·en, `extractionState: manual`). 원격 시트 등록은 범위 밖.
- 진입은 기능 플래그 `aiChat`(디버그 메뉴, 기본 off) 뒤 More 행 하나.
- 빌드·테스트는 사용자가 직접 돌린다. 커밋은 지시받았을 때만, gitmoji, `Co-Authored-By` 없음.
- 테스트 모듈 import 는 최근 테스트와 같이 `@testable import Hub_Dev`.

## 파일 구조

| 구분 | 경로 | 책임 |
|---|---|---|
| Modify | `Hub/Utilities/Log/HubLogger.swift` | `aiLogger` 추가 |
| Create | `Hub/Domain/Entities/AIChat/HubQuery.swift` | `HubQuery` 와 의도·날짜·시간대·이벤트·참조 enum |
| Create | `Hub/Domain/Entities/AIChat/HubQueryDTO.swift` | LLM 공통 출력 `HubQueryDTO` + 검증 `HubQueryMapper` |
| Create | `Hub/Domain/Entities/AIChat/RecordingFile.swift` | `RecordingKind` · `RecordingFile` · `RecordingFileName.parse` |
| Create | `Hub/Domain/Entities/AIChat/HubChatAnswer.swift` | 답변·카드·주행 요약·좌표·직전 결과(context) |
| Create | `Hub/Domain/UseCases/AIChat/HubQueryResolver.swift` | `HubQuery` → 검색 구간(`HubQueryWindow`) |
| Create | `Hub/Domain/UseCases/AIChat/RecordingPicker.swift` | 기준 시각을 담는 파일 선택 |
| Create | `Hub/Domain/UseCases/AIChat/DriveMatcher.swift` | 출발·도착 반경 매칭 |
| Create | `Hub/Domain/UseCases/AIChat/SettingsGuide.swift` | 가이드 모델·로드·키워드 검색 |
| Create | `Hub/Domain/UseCases/AIChat/HubQueryPrompt.swift` | 파서 지시문·사용자 프롬프트(백엔드 공용) |
| Create | `Hub/Domain/UseCases/AIChat/HubChatEngine.swift` | 오케스트레이션 |
| Create | `Hub/Domain/Interface/Repository/AIChat/HubChatDependencies.swift` | 엔진이 의존하는 프로토콜 7개 |
| Create | `Hub/Data/AIChat/DeviceRecordingFileSource.swift` | getfilelist → `RecordingFile` |
| Create | `Hub/Data/AIChat/LocalRecordingFileSource.swift` | `Documents/DOWNLOADED` → `RecordingFile` |
| Create | `Hub/Data/AIChat/SqlDriveHistorySource.swift` | `SqlQuery` 래핑 |
| Create | `Hub/Data/AIChat/MapKitPlaceGeocoder.swift` | `MKLocalSearch` |
| Create | `Hub/Data/AIChat/CachedDeviceSettingSource.swift` | 현재 설정값 |
| Create | `Hub/Data/AIChat/FoundationModels/FMQueryParser.swift` | FM `@Generable` 파서 |
| Create | `Hub/Data/AIChat/FoundationModels/FMGuideAnswerer.swift` | FM 가이드 답변 |
| Create | `Hub/Data/AIChat/AIChatAvailability.swift` | 백엔드 선택·불가 사유 |
| Create | `Hub/Resources/AIChat/settings_guide.json` | 설정 가이드 본문(ko·en) |
| Create | `Hub/Presentation/AIChatScene/Reducer/AIChatReducer.swift` | 화면 상태 |
| Create | `Hub/Presentation/AIChatScene/AIChatEffectRunner.swift` | Effect 실행 |
| Create | `Hub/Presentation/AIChatScene/AIChatCoordinator.swift` | Store 조립·push·카드 열기 |
| Create | `Hub/Presentation/AIChatScene/View/AIChatView.swift` | 메시지 목록·입력창·추천 질문 |
| Create | `Hub/Presentation/AIChatScene/View/AIChatCardViews.swift` | 영상·주행·설정 카드, 지도 시트 |
| Modify | `Hub/Presentation/SettingScene/Coordinator/SettingCoordinator.swift` | `SettingSteps.showSettingFocused(key:)` |
| Modify | `Hub/Presentation/SettingScene/ViewModel/SettingWifiViewModel.swift:751` | `selectRow(key:)` 일반화 |
| Modify | `Hub/Presentation/SettingScene/ViewController/SettingViewController.swift:448` | 포커스 키 스크롤 |
| Modify | `Hub/Application/FeatureFlag/*` · `MoreViewController.swift` · `DefaultMoreCoordinator.swift` | 플래그·More 행·push |
| Modify | `Hub/Localizable.swift` · `Hub/Resources/Localizable.xcstrings` | 문구 |
| Test | `HubDevTests/HubQueryMapperTests.swift` 외 7개 | 아래 Task 별 |

---

### Task 0: Spike — FM 한국어 파싱 품질 확인 (게이트)

코드를 쌓기 전에 FM 이 이 질문들을 구조화할 수 있는지 실기로 본다. 결과가 나쁘면 Task 7 지시문을 고치거나 MLX 를 앞당긴다.

**Files:**
- Create: `HubDevTests/Fixtures/ai_chat_eval_ko.json` (Task 7 의 평가 테스트가 재사용)

- [ ] **Step 1: 평가셋 작성** — 질문 20개와 기대 DTO. 아래 4개는 필수, 나머지는 변형(날짜 표현 "그저께"·"11월 3일", 시간 표현 "6시쯤"·"오후 2시", 지명 없는 "사고 영상", 설정 질문 "충격 감도 낮추는 법"·"방전 막으려면")

```json
[
  {"q": "어제 아침 출근길중 9시 30분경 비디오를 보여줘",
   "expect": {"intent": "video", "daysAgo": 1, "hour": 9, "minute": 30, "period": "morningCommute"}},
  {"q": "판교에서 인천가는 퇴근길에 사고날뻔한 적이 있었어 그때 경로와 위치를 보여줘",
   "expect": {"intent": "drive", "period": "eveningCommute", "origin": "판교", "destination": "인천", "event": "impact"}},
  {"q": "위 경우의 비디오를 보여줘",
   "expect": {"intent": "video", "reference": "previous"}},
  {"q": "설정에서 뭘 바꿔야 주차녹화가 줄어들지",
   "expect": {"intent": "settingsHelp", "topic": "주차 녹화"}}
]
```

- [ ] **Step 2: 실기(Apple Intelligence 켠 iOS 26 기기)에서 평가셋을 돌린다.** Task 1(전체), Task 5, Task 7(Step 1·3·4·5)을 먼저 구현한다 —
  이 파일들은 Task 2·3·4·6 에 의존하지 않는다. 나머지 Task 는 이 게이트를 통과한 뒤 순서대로 진행한다.
  확인할 것: ① `@Guide(.range(...))` 가 옵셔널 `Int?` 에 붙는지(컴파일) ② `.anyOf` 문자열 제약 ③ 질문당 지연(목표 1.5 s 이하)
  ④ 정확도(intent 100%, 나머지 필드 85% 이상) ⑤ `SystemLanguageModel.default.supportsLocale(Locale(identifier: "ko_KR"))`.
- [ ] **Step 3: fakeApiServer 로 파일명 형식 확인** — `cd fakeApiServer && swift run fakeApiServer --model S1-4K` 후 getfilelist type 0·1·2·4 응답의
  `filename` 을 기록해 Task 1 의 `RecordingKind` raw 값(INF/EVT/PRK/PVT/USR)과 대조한다. 다른 토큰이 있으면 Task 1 enum 에 추가한다.
- [ ] **Step 4: 결과를 이 문서 Task 0 아래에 `> 결과:` 블록으로 적는다.**

---

### Task 1: 도메인 타입 · DTO 검증 · 파일명 파서

**Files:**
- Modify: `Hub/Utilities/Log/HubLogger.swift`
- Create: `Hub/Domain/Entities/AIChat/HubQuery.swift`
- Create: `Hub/Domain/Entities/AIChat/HubQueryDTO.swift`
- Create: `Hub/Domain/Entities/AIChat/RecordingFile.swift`
- Create: `Hub/Domain/Entities/AIChat/HubChatAnswer.swift`
- Test: `HubDevTests/HubQueryMapperTests.swift`, `HubDevTests/RecordingFileNameTests.swift`

**Interfaces:**
- Produces: `HubQuery`, `HubQueryIntent`, `HubQueryDay`, `HubClockTime`, `HubDayPeriod`(`hours: Range<Int>?`),
  `HubEventFilter`, `HubQueryReference`, `HubQueryDTO`, `HubQueryMapper.map(_:) -> HubQuery`,
  `RecordingKind`, `RecordingLocation`, `RecordingFile`, `RecordingFileName.parse(_:timeZone:) -> (startedAt: Date, kind: RecordingKind)?`,
  `HubCoordinate`, `HubDriveRecord`, `HubDriveEvent`, `HubDriveSummary`, `HubChatCard`, `HubChatReply`,
  `HubNoResultReason`, `HubPlaceMatch`, `HubChatContext`, `HubChatAnswer`, 전역 `aiLogger`

- [ ] **Step 1: 실패하는 테스트 작성** — `HubDevTests/HubQueryMapperTests.swift`

```swift
//
//  HubQueryMapperTests.swift
//  HubDevTests
//
//  LLM 출력(DTO) 검증 — 범위 밖 값 제거, 오후 시간대 24시간제 보정, 빈 문자열 정리
//

import XCTest

@testable import Hub_Dev

final class HubQueryMapperTests: XCTestCase {
  private func dto(_ intent: String = "video") -> HubQueryDTO {
    HubQueryDTO(intent: intent)
  }

  func testUnknownIntentStringBecomesUnknown() {
    XCTAssertEqual(HubQueryMapper.map(dto("play")).intent, .unknown)
  }

  func testDaysAgoMapsToDay() {
    var input = dto()
    input.daysAgo = 1
    XCTAssertEqual(HubQueryMapper.map(input).day, .daysAgo(1))
  }

  func testMonthAndDayWinOverDaysAgo() {
    var input = dto()
    input.daysAgo = 1
    input.month = 11
    input.dayOfMonth = 3
    XCTAssertEqual(HubQueryMapper.map(input).day, .date(month: 11, day: 3))
  }

  func testOutOfRangeValuesAreDropped() {
    var input = dto()
    input.daysAgo = 999
    input.month = 13
    input.dayOfMonth = 3
    input.hour = 25
    XCTAssertEqual(HubQueryMapper.map(input).day, .unspecified)
    XCTAssertNil(HubQueryMapper.map(input).clock)
  }

  func testEveningCommuteHourBelowTwelveIsShiftedToPM() {
    var input = dto()
    input.hour = 6
    input.minute = 10
    input.period = "eveningCommute"
    XCTAssertEqual(HubQueryMapper.map(input).clock, HubClockTime(hour: 18, minute: 10))
  }

  func testMorningHourIsKept() {
    var input = dto()
    input.hour = 9
    input.minute = 30
    input.period = "morningCommute"
    XCTAssertEqual(HubQueryMapper.map(input).clock, HubClockTime(hour: 9, minute: 30))
  }

  func testMissingMinuteDefaultsToZero() {
    var input = dto()
    input.hour = 14
    XCTAssertEqual(HubQueryMapper.map(input).clock, HubClockTime(hour: 14, minute: 0))
  }

  func testBlankPlacesBecomeNil() {
    var input = dto("drive")
    input.origin = "  "
    input.destination = " 인천 "
    let query = HubQueryMapper.map(input)
    XCTAssertNil(query.origin)
    XCTAssertEqual(query.destination, "인천")
  }

  func testEventAndReferenceStrings() {
    var input = dto()
    input.event = "impact"
    input.reference = "previous"
    let query = HubQueryMapper.map(input)
    XCTAssertEqual(query.event, .impact)
    XCTAssertEqual(query.reference, .previous)
  }
}
```

`HubDevTests/RecordingFileNameTests.swift`

```swift
//
//  RecordingFileNameTests.swift
//  HubDevTests
//
//  단말 파일명(날짜_시각_종류_...) 에서 시작 시각·녹화 종류를 읽는다
//

import XCTest

@testable import Hub_Dev

final class RecordingFileNameTests: XCTestCase {
  private let seoul = TimeZone(identifier: "Asia/Seoul")!

  private func date(_ text: String) -> Date {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = seoul
    formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
    return formatter.date(from: text)!
  }

  func testLegacyAviName() {
    let parsed = RecordingFileName.parse("20220517_092615_INF_2.avi", timeZone: seoul)
    XCTAssertEqual(parsed?.startedAt, date("2022-05-17 09:26:15"))
    XCTAssertEqual(parsed?.kind, .drive)
  }

  func testCurrentMp4NameWithChannelSuffix() {
    let parsed = RecordingFileName.parse("20250701_120710_EVT_F_N.mp4", timeZone: seoul)
    XCTAssertEqual(parsed?.startedAt, date("2025-07-01 12:07:10"))
    XCTAssertEqual(parsed?.kind, .event)
  }

  func testKindWithoutChannel() {
    XCTAssertEqual(RecordingFileName.parse("20250701_120710_PRK.mp4", timeZone: seoul)?.kind, .parking)
  }

  func testUnknownKindReturnsNil() {
    XCTAssertNil(RecordingFileName.parse("20250701_120710_XYZ_F.mp4", timeZone: seoul))
  }

  func testMalformedReturnsNil() {
    XCTAssertNil(RecordingFileName.parse("IMG_0001.jpg", timeZone: seoul))
    XCTAssertNil(RecordingFileName.parse("2025070_120710_INF.mp4", timeZone: seoul))
  }
}
```

(테스트 코드의 `!` 는 테스트 타겟이라 허용한다.)

- [ ] **Step 2: 실행해 컴파일 실패를 확인한다 (사용자 실행)**

```bash
xcodebuild test -project Hub.xcodeproj -scheme Hub-Dev \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  -only-testing:HubDevTests/HubQueryMapperTests -only-testing:HubDevTests/RecordingFileNameTests
```
Expected: `cannot find 'HubQueryDTO' in scope`

- [ ] **Step 3: 구현**

`Hub/Utilities/Log/HubLogger.swift` 의 logger 목록 끝에 한 줄:

```swift
let aiLogger = Logger(subsystem: "hub", category: "aichat")
```

`Hub/Domain/Entities/AIChat/HubQuery.swift`

```swift
//
//  HubQuery.swift
//  Hub
//

import Foundation

/// 채팅 질문을 앱이 실행할 수 있게 옮긴 값. LLM 은 이 값만 만든다.
struct HubQuery: Equatable {
  var intent: HubQueryIntent
  var day: HubQueryDay = .unspecified
  var clock: HubClockTime?
  var period: HubDayPeriod = .any
  var origin: String?
  var destination: String?
  var event: HubEventFilter = .any
  var reference: HubQueryReference = .none
  var topic: String?
}

enum HubQueryIntent: String, CaseIterable {
  case video
  case drive
  case settingsHelp
  case unknown
}

/// 오늘은 `.daysAgo(0)`, 어제는 `.daysAgo(1)`. 연도 없이 말한 날짜는 가장 최근의 그 날로 푼다.
enum HubQueryDay: Equatable {
  case unspecified
  case daysAgo(Int)
  case date(month: Int, day: Int)
}

struct HubClockTime: Equatable {
  let hour: Int
  let minute: Int
}

enum HubDayPeriod: String, CaseIterable {
  case any
  case morningCommute
  case eveningCommute
  case morning
  case afternoon
  case evening
  case night

  /// 주행 시작 시각(시)이 들어가야 하는 범위. `.any` 는 제한 없음.
  var hours: Range<Int>? {
    switch self {
    case .any: nil
    case .morningCommute: 6..<10
    case .eveningCommute: 17..<21
    case .morning: 6..<12
    case .afternoon: 12..<18
    case .evening: 18..<24
    case .night: 0..<6
    }
  }
}

enum HubEventFilter: String, CaseIterable {
  case any
  case impact
}

enum HubQueryReference: String, CaseIterable {
  case none
  case previous
}
```

`Hub/Domain/Entities/AIChat/HubQueryDTO.swift`

```swift
//
//  HubQueryDTO.swift
//  Hub
//

import Foundation

/// LLM 출력의 공통 형태. FM·MLX 는 이 값으로 옮기고 검증은 `HubQueryMapper` 한 곳에서 한다.
struct HubQueryDTO: Codable, Equatable {
  var intent: String
  var daysAgo: Int?
  var month: Int?
  var dayOfMonth: Int?
  var hour: Int?
  var minute: Int?
  var period: String?
  var origin: String?
  var destination: String?
  var event: String?
  var reference: String?
  var topic: String?
}

enum HubQueryMapper {
  /// 범위 밖 값은 버리고 문자열 enum 은 모르는 값이면 기본값으로 둔다.
  static func map(_ dto: HubQueryDTO) -> HubQuery {
    let period = dto.period.flatMap(HubDayPeriod.init(rawValue:)) ?? .any
    return HubQuery(
      intent: HubQueryIntent(rawValue: dto.intent) ?? .unknown,
      day: day(dto),
      clock: clock(dto, period: period),
      period: period,
      origin: nonEmpty(dto.origin),
      destination: nonEmpty(dto.destination),
      event: dto.event.flatMap(HubEventFilter.init(rawValue:)) ?? .any,
      reference: dto.reference.flatMap(HubQueryReference.init(rawValue:)) ?? .none,
      topic: nonEmpty(dto.topic))
  }

  private static func day(_ dto: HubQueryDTO) -> HubQueryDay {
    if let month = dto.month, let day = dto.dayOfMonth,
      (1...12).contains(month), (1...31).contains(day)
    {
      return .date(month: month, day: day)
    }
    if let daysAgo = dto.daysAgo, (0...365).contains(daysAgo) {
      return .daysAgo(daysAgo)
    }
    return .unspecified
  }

  /// 오후 시간대인데 12 미만으로 오면 24시간제로 올린다 ("퇴근길 6시" → 18시).
  private static func clock(_ dto: HubQueryDTO, period: HubDayPeriod) -> HubClockTime? {
    guard let hour = dto.hour, (0...23).contains(hour) else { return nil }
    let minute = dto.minute.flatMap { (0...59).contains($0) ? $0 : nil } ?? 0
    let pmPeriods: Set<HubDayPeriod> = [.eveningCommute, .afternoon, .evening]
    let adjusted = pmPeriods.contains(period) && hour < 12 ? hour + 12 : hour
    return HubClockTime(hour: adjusted, minute: minute)
  }

  private static func nonEmpty(_ value: String?) -> String? {
    guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty
    else { return nil }
    return trimmed
  }
}
```

`HubQueryDTO(intent: "video")` 처럼 나머지를 생략해 만들 수 있도록 Swift 가 만드는 memberwise init 의 기본값이
필요하다 — 옵셔널 `var` 는 기본값 `nil` 이 자동으로 붙으므로 추가 코드는 없다.

`Hub/Domain/Entities/AIChat/RecordingFile.swift`

```swift
//
//  RecordingFile.swift
//  Hub
//

import Foundation

/// 파일명 세 번째 토큰. getfilelist type 과 1:1 (0 INF · 1 EVT · 2 PRK · 3 USR · 4 PVT).
enum RecordingKind: String, CaseIterable {
  case drive = "INF"
  case event = "EVT"
  case parking = "PRK"
  case manual = "USR"
  case parkingEvent = "PVT"

  var fileListType: Int {
    switch self {
    case .drive: 0
    case .event: 1
    case .parking: 2
    case .manual: 3
    case .parkingEvent: 4
    }
  }
}

/// 재생에 필요한 위치. 단말 파일은 getfilelist 응답 값을, 로컬 파일은 경로를 그대로 들고 있는다.
enum RecordingLocation: Equatable {
  case device(streamPath: String?, downloadUrl: String?, channelbits: Int)
  case local(URL)
}

struct RecordingFile: Equatable {
  let fileName: String
  let startedAt: Date
  let kind: RecordingKind
  let location: RecordingLocation
}

enum RecordingFileName {
  /// `20220517_092615_INF_2.avi`, `20250701_120710_EVT_F_N.mp4` 처럼 날짜_시각_종류 로 시작하는 이름을 읽는다.
  /// - Returns: 형식이 다르거나 종류 토큰을 모르면 `nil`.
  static func parse(_ fileName: String, timeZone: TimeZone = .current)
    -> (startedAt: Date, kind: RecordingKind)?
  {
    let parts = fileName.split(separator: "_", maxSplits: 3, omittingEmptySubsequences: false)
    guard parts.count >= 3, parts[0].count == 8, parts[1].count == 6,
      let kind = RecordingKind(rawValue: String(parts[2].prefix(3)))
    else { return nil }
    // ponytail: 호출마다 formatter 생성 — 공유 인스턴스의 timeZone 을 바꾸면 동시 호출에 안전하지 않다. 수천 건에서 느리면 timeZone 별 캐시
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = timeZone
    formatter.dateFormat = "yyyyMMdd_HHmmss"
    guard let date = formatter.date(from: "\(parts[0])_\(parts[1])") else { return nil }
    return (date, kind)
  }
}
```

`Hub/Domain/Entities/AIChat/HubChatAnswer.swift`

```swift
//
//  HubChatAnswer.swift
//  Hub
//

import CoreLocation
import Foundation

struct HubCoordinate: Equatable {
  let latitude: Double
  let longitude: Double

  /// 두 좌표 사이 거리(m).
  func distance(to other: HubCoordinate) -> Double {
    CLLocation(latitude: latitude, longitude: longitude)
      .distance(from: CLLocation(latitude: other.latitude, longitude: other.longitude))
  }
}

/// history DB 의 주행(TYPE 1) 한 건. 여러 단말을 한 번에 다루려고 mac 을 함께 든다.
struct HubDriveRecord: Equatable {
  let start: Date
  let end: Date
  let distance: Int
  let eventCount: Int
  let macAddress: String
}

struct HubDriveEvent: Equatable {
  let time: Date
  let file: RecordingFile?
  let coordinate: HubCoordinate?
}

struct HubDriveSummary: Equatable {
  let drive: HubDriveRecord
  let route: [HubCoordinate]
  let events: [HubDriveEvent]
}

enum HubChatCard: Equatable {
  case video(RecordingFile)
  case drive(HubDriveSummary)
  case setting(key: String, title: String)
}

enum HubNoResultReason: Equatable {
  case notFound
  case needsConnection
}

/// 지명을 좌표로 바꿔 매칭했는지, 못 바꿔 시간대로만 찾았는지.
enum HubPlaceMatch: Equatable {
  case matched
  case timeOnly
}

/// 화면이 로컬라이즈해 문장으로 만든다. LLM 이 쓴 문장은 `.guide` 뿐이다.
enum HubChatReply: Equatable {
  case videos(count: Int)
  case noVideo(HubNoResultReason)
  case drive(HubPlaceMatch)
  case noDrive(HubNoResultReason)
  case guide(text: String)
  case noGuide
  case notUnderstood
}

/// 후속 질문("위 경우")이 가리킬 직전 결과.
struct HubChatContext: Equatable {
  var lastDrive: HubDriveSummary?
  var lastEvent: HubDriveEvent?
  var lastVideo: RecordingFile?
}

struct HubChatAnswer: Equatable {
  let reply: HubChatReply
  let cards: [HubChatCard]
  let context: HubChatContext
}
```

- [ ] **Step 4: 테스트 통과 확인 (사용자 실행, Step 2 와 같은 명령)** — Expected: 14 tests PASS
- [ ] **Step 5: `swift-format --configuration Scripts/ncn.swift-format.config.json --in-place` 를 새 파일에 적용**

---

### Task 2: 검색 구간 계산 · 파일 선택 · 지명 매칭

**Files:**
- Create: `Hub/Domain/UseCases/AIChat/HubQueryResolver.swift`
- Create: `Hub/Domain/UseCases/AIChat/RecordingPicker.swift`
- Create: `Hub/Domain/UseCases/AIChat/DriveMatcher.swift`
- Test: `HubDevTests/HubQueryResolverTests.swift`, `HubDevTests/RecordingPickerTests.swift`, `HubDevTests/DriveMatcherTests.swift`

**Interfaces:**
- Consumes: Task 1 의 `HubQuery`, `HubQueryDay`, `HubClockTime`, `HubDayPeriod.hours`, `RecordingFile`, `HubCoordinate`
- Produces:
  - `struct HubQueryWindow: Equatable { let interval: DateInterval; let hours: Range<Int>?; let anchor: Date?; func contains(_ date: Date, calendar: Calendar) -> Bool }`
  - `enum HubQueryResolver { static let lookbackDays: Int; static let anchorTolerance: TimeInterval; static func window(for: HubQuery, now: Date, calendar: Calendar) -> HubQueryWindow }`
  - `enum RecordingPicker { static func file(at anchor: Date, in files: [RecordingFile], tolerance: TimeInterval) -> RecordingFile? }`
  - `struct HubPlace: Equatable { let center: HubCoordinate; let radiusMeters: Double }`
  - `enum DriveMatcher { static func matches(route: [HubCoordinate], origin: HubPlace?, destination: HubPlace?) -> Bool }`

- [ ] **Step 1: 실패하는 테스트 작성**

`HubDevTests/HubQueryResolverTests.swift`

```swift
//
//  HubQueryResolverTests.swift
//  HubDevTests
//
//  질문 → 검색 구간. 기준 시각은 2026-11-06(금) 10:00 KST
//

import XCTest

@testable import Hub_Dev

final class HubQueryResolverTests: XCTestCase {
  private var calendar: Calendar = {
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = TimeZone(identifier: "Asia/Seoul")!
    return calendar
  }()

  private func at(_ y: Int, _ m: Int, _ d: Int, _ h: Int = 0, _ min: Int = 0) -> Date {
    calendar.date(from: DateComponents(year: y, month: m, day: d, hour: h, minute: min))!
  }

  private var now: Date { at(2026, 11, 6, 10, 0) }

  func testYesterdayClockGivesAnchorWithTolerance() {
    let query = HubQuery(
      intent: .video, day: .daysAgo(1), clock: HubClockTime(hour: 9, minute: 30),
      period: .morningCommute)
    let window = HubQueryResolver.window(for: query, now: now, calendar: calendar)
    XCTAssertEqual(window.anchor, at(2026, 11, 5, 9, 30))
    XCTAssertEqual(window.interval.start, at(2026, 11, 5, 9, 25))
    XCTAssertEqual(window.interval.end, at(2026, 11, 5, 9, 35))
    XCTAssertNil(window.hours)
  }

  func testClockWithoutDayThatAlreadyPassedIsToday() {
    let query = HubQuery(intent: .video, clock: HubClockTime(hour: 9, minute: 0))
    XCTAssertEqual(
      HubQueryResolver.window(for: query, now: now, calendar: calendar).anchor,
      at(2026, 11, 6, 9, 0))
  }

  func testClockWithoutDayStillAheadIsYesterday() {
    let query = HubQuery(intent: .video, clock: HubClockTime(hour: 18, minute: 0))
    XCTAssertEqual(
      HubQueryResolver.window(for: query, now: now, calendar: calendar).anchor,
      at(2026, 11, 5, 18, 0))
  }

  func testDayWithoutClockCoversThatDayAndKeepsPeriodHours() {
    let query = HubQuery(intent: .drive, day: .daysAgo(1), period: .eveningCommute)
    let window = HubQueryResolver.window(for: query, now: now, calendar: calendar)
    XCTAssertEqual(window.interval, DateInterval(start: at(2026, 11, 5), end: at(2026, 11, 6)))
    XCTAssertEqual(window.hours, 17..<21)
  }

  func testTodayEndsAtNow() {
    let query = HubQuery(intent: .drive, day: .daysAgo(0))
    XCTAssertEqual(
      HubQueryResolver.window(for: query, now: now, calendar: calendar).interval.end, now)
  }

  func testNoDayLooksBackThirtyDays() {
    let query = HubQuery(intent: .drive, period: .eveningCommute)
    let window = HubQueryResolver.window(for: query, now: now, calendar: calendar)
    XCTAssertEqual(window.interval.start, at(2026, 10, 7))
    XCTAssertEqual(window.interval.end, now)
    XCTAssertEqual(window.hours, 17..<21)
  }

  func testMonthDayInFutureFallsBackToLastYear() {
    let query = HubQuery(intent: .drive, day: .date(month: 12, day: 24))
    XCTAssertEqual(
      HubQueryResolver.window(for: query, now: now, calendar: calendar).interval.start,
      at(2025, 12, 24))
  }

  func testContainsChecksHours() {
    let window = HubQueryWindow(
      interval: DateInterval(start: at(2026, 11, 1), end: now), hours: 17..<21, anchor: nil)
    XCTAssertTrue(window.contains(at(2026, 11, 3, 18, 10), calendar: calendar))
    XCTAssertFalse(window.contains(at(2026, 11, 3, 8, 10), calendar: calendar))
    XCTAssertFalse(window.contains(at(2026, 10, 3, 18, 10), calendar: calendar))
  }
}
```

`HubDevTests/RecordingPickerTests.swift`

```swift
//
//  RecordingPickerTests.swift
//  HubDevTests
//

import XCTest

@testable import Hub_Dev

final class RecordingPickerTests: XCTestCase {
  private let base = Date(timeIntervalSince1970: 1_800_000_000)

  private func file(_ offset: TimeInterval, _ name: String) -> RecordingFile {
    RecordingFile(
      fileName: name, startedAt: base.addingTimeInterval(offset), kind: .drive,
      location: .local(URL(fileURLWithPath: "/tmp/\(name)")))
  }

  func testPicksLatestFileStartingBeforeAnchor() {
    let files = [file(-120, "a"), file(-60, "b"), file(30, "c")]
    XCTAssertEqual(RecordingPicker.file(at: base, in: files, tolerance: 300)?.fileName, "b")
  }

  func testFallsBackToNearestAfterAnchor() {
    let files = [file(40, "c"), file(200, "d")]
    XCTAssertEqual(RecordingPicker.file(at: base, in: files, tolerance: 300)?.fileName, "c")
  }

  func testOutsideToleranceReturnsNil() {
    XCTAssertNil(RecordingPicker.file(at: base, in: [file(-900, "a")], tolerance: 300))
  }
}
```

`HubDevTests/DriveMatcherTests.swift`

```swift
//
//  DriveMatcherTests.swift
//  HubDevTests
//
//  판교(37.3947, 127.1112) → 인천 시청(37.4563, 126.7052)
//

import XCTest

@testable import Hub_Dev

final class DriveMatcherTests: XCTestCase {
  private let pangyo = HubCoordinate(latitude: 37.3947, longitude: 127.1112)
  private let incheon = HubCoordinate(latitude: 37.4563, longitude: 126.7052)
  private let gangnam = HubCoordinate(latitude: 37.4979, longitude: 127.0276)

  private func place(_ center: HubCoordinate, _ radius: Double = 5_000) -> HubPlace {
    HubPlace(center: center, radiusMeters: radius)
  }

  func testRouteFromOriginToDestinationMatches() {
    XCTAssertTrue(
      DriveMatcher.matches(
        route: [pangyo, gangnam, incheon], origin: place(pangyo), destination: place(incheon)))
  }

  func testReverseDirectionDoesNotMatch() {
    XCTAssertFalse(
      DriveMatcher.matches(
        route: [incheon, pangyo], origin: place(pangyo), destination: place(incheon)))
  }

  func testOnlyOriginGiven() {
    XCTAssertTrue(DriveMatcher.matches(route: [pangyo, gangnam], origin: place(pangyo), destination: nil))
  }

  func testEmptyRouteNeverMatchesWhenPlaceGiven() {
    XCTAssertFalse(DriveMatcher.matches(route: [], origin: place(pangyo), destination: nil))
  }

  func testNoPlacesAlwaysMatches() {
    XCTAssertTrue(DriveMatcher.matches(route: [], origin: nil, destination: nil))
  }
}
```

- [ ] **Step 2: 실행해 실패 확인 (사용자 실행)** — `-only-testing:HubDevTests/HubQueryResolverTests -only-testing:HubDevTests/RecordingPickerTests -only-testing:HubDevTests/DriveMatcherTests`. Expected: 타입 없음 컴파일 오류
- [ ] **Step 3: 구현**

`Hub/Domain/UseCases/AIChat/HubQueryResolver.swift`

```swift
//
//  HubQueryResolver.swift
//  Hub
//

import Foundation

/// 검색할 시간 범위. 특정 시각을 물었으면 `anchor` 주변 ±tolerance, 아니면 하루 또는 최근 N일 + 시간대.
struct HubQueryWindow: Equatable {
  let interval: DateInterval
  let hours: Range<Int>?
  let anchor: Date?

  func contains(_ date: Date, calendar: Calendar) -> Bool {
    guard interval.contains(date) else { return false }
    guard let hours else { return true }
    return hours.contains(calendar.component(.hour, from: date))
  }
}

enum HubQueryResolver {
  static let lookbackDays = 30
  static let anchorTolerance: TimeInterval = 5 * 60

  static func window(for query: HubQuery, now: Date, calendar: Calendar) -> HubQueryWindow {
    let dayStart = dayStart(query.day, clock: query.clock, now: now, calendar: calendar)
    if let clock = query.clock, let dayStart,
      let anchor = calendar.date(
        bySettingHour: clock.hour, minute: clock.minute, second: 0, of: dayStart)
    {
      let interval = DateInterval(
        start: anchor.addingTimeInterval(-anchorTolerance),
        end: anchor.addingTimeInterval(anchorTolerance))
      return HubQueryWindow(interval: interval, hours: nil, anchor: anchor)
    }
    if let dayStart, let next = calendar.date(byAdding: .day, value: 1, to: dayStart) {
      let interval = DateInterval(start: dayStart, end: max(dayStart, min(next, now)))
      return HubQueryWindow(interval: interval, hours: query.period.hours, anchor: nil)
    }
    let today = calendar.startOfDay(for: now)
    let start = calendar.date(byAdding: .day, value: -lookbackDays, to: today) ?? today
    return HubQueryWindow(
      interval: DateInterval(start: start, end: now), hours: query.period.hours, anchor: nil)
  }

  private static func dayStart(
    _ day: HubQueryDay, clock: HubClockTime?, now: Date, calendar: Calendar
  ) -> Date? {
    let today = calendar.startOfDay(for: now)
    switch day {
    case .daysAgo(let count):
      return calendar.date(byAdding: .day, value: -count, to: today)
    case .date(let month, let day):
      return mostRecent(month: month, day: day, now: now, calendar: calendar)
    case .unspecified:
      // 시각만 말하면 오늘, 아직 오지 않은 시각이면 어제
      guard let clock,
        let todayAnchor = calendar.date(
          bySettingHour: clock.hour, minute: clock.minute, second: 0, of: today)
      else { return nil }
      return todayAnchor <= now ? today : calendar.date(byAdding: .day, value: -1, to: today)
    }
  }

  private static func mostRecent(month: Int, day: Int, now: Date, calendar: Calendar) -> Date? {
    let year = calendar.component(.year, from: now)
    for candidate in [year, year - 1] {
      if let date = calendar.date(from: DateComponents(year: candidate, month: month, day: day)),
        date <= now
      {
        return date
      }
    }
    return nil
  }
}
```

`Hub/Domain/UseCases/AIChat/RecordingPicker.swift`

```swift
//
//  RecordingPicker.swift
//  Hub
//

import Foundation

enum RecordingPicker {
  /// 기준 시각을 담는 파일 — 시작이 기준 이하인 것 중 가장 늦은 것, 없으면 허용 범위 안에서 가장 가까운 것.
  static func file(at anchor: Date, in files: [RecordingFile], tolerance: TimeInterval)
    -> RecordingFile?
  {
    let near = files.filter { abs($0.startedAt.timeIntervalSince(anchor)) <= tolerance }
    if let containing = near.filter({ $0.startedAt <= anchor }).max(by: {
      $0.startedAt < $1.startedAt
    }) {
      return containing
    }
    return near.min {
      abs($0.startedAt.timeIntervalSince(anchor)) < abs($1.startedAt.timeIntervalSince(anchor))
    }
  }
}
```

`Hub/Domain/UseCases/AIChat/DriveMatcher.swift`

```swift
//
//  DriveMatcher.swift
//  Hub
//

import Foundation

/// 지명 검색 결과. 반경은 검색 영역 크기(도시면 넓다)와 최소 5km 중 큰 값.
struct HubPlace: Equatable {
  let center: HubCoordinate
  let radiusMeters: Double
}

enum DriveMatcher {
  /// 경로 첫 점이 출발지 반경 안, 마지막 점이 도착지 반경 안이면 같은 주행으로 본다. 주어지지 않은 쪽은 검사하지 않는다.
  static func matches(route: [HubCoordinate], origin: HubPlace?, destination: HubPlace?) -> Bool {
    if let origin {
      guard let first = route.first, first.distance(to: origin.center) <= origin.radiusMeters
      else { return false }
    }
    if let destination {
      guard let last = route.last, last.distance(to: destination.center) <= destination.radiusMeters
      else { return false }
    }
    return true
  }
}
```

- [ ] **Step 4: 테스트 통과 확인 (사용자 실행)** — Expected: 16 tests PASS

---

### Task 3: 설정 가이드 데이터와 검색

**Files:**
- Create: `Hub/Resources/AIChat/settings_guide.json` (Hub 타겟 Copy Bundle Resources 에 추가)
- Create: `Hub/Domain/UseCases/AIChat/SettingsGuide.swift`
- Test: `HubDevTests/SettingsGuideTests.swift`

**Interfaces:**
- Produces:
  - `struct SettingsGuideSection: Codable, Equatable { let id: String; let keywords: [String]; let title: [String: String]; let body: [String: String]; let configKey: String?; let settingKey: String?; func title(language: String) -> String; func body(language: String) -> String }`
  - `struct SettingsGuide: Equatable { let sections: [SettingsGuideSection]; static func load(from url: URL) throws -> SettingsGuide; func search(_ text: String, limit: Int) -> [SettingsGuideSection] }`

`configKey` 는 getconfiguration 키(현재 값 읽기), `settingKey` 는 설정 화면 행 key(바로가기). 두 값이 같은 경우가 많지만
따로 둔다. **본문은 초안이다 — 기획 검수 후 확정한다.** 설정 행 key 는 Step 3 에서 `ConfigurationDTO.swift` 의
행 key 와 대조해 맞춘다.

- [ ] **Step 1: 실패하는 테스트 작성** — `HubDevTests/SettingsGuideTests.swift`

```swift
//
//  SettingsGuideTests.swift
//  HubDevTests
//
//  키워드 검색 순위 · 번들 JSON 로드
//

import XCTest

@testable import Hub_Dev

final class SettingsGuideTests: XCTestCase {
  private func section(_ id: String, _ keywords: [String]) -> SettingsGuideSection {
    SettingsGuideSection(
      id: id, keywords: keywords, title: ["ko": id, "en": id], body: ["ko": "본문", "en": "body"],
      configKey: id, settingKey: id)
  }

  func testRanksByMatchedKeywordCount() {
    let guide = SettingsGuide(sections: [
      section("a", ["주차"]),
      section("b", ["주차", "충격"]),
      section("c", ["녹화 화질"]),
    ])
    XCTAssertEqual(guide.search("주차 충격 녹화를 줄이려면", limit: 3).map(\.id), ["b", "a"])
  }

  func testTieKeepsFileOrder() {
    let guide = SettingsGuide(sections: [section("a", ["주차"]), section("b", ["주차"])])
    XCTAssertEqual(guide.search("주차", limit: 3).map(\.id), ["a", "b"])
  }

  func testCaseInsensitiveEnglish() {
    let guide = SettingsGuide(sections: [section("a", ["parking"])])
    XCTAssertEqual(guide.search("Reduce PARKING recordings", limit: 3).map(\.id), ["a"])
  }

  func testLanguageFallsBackToEnglish() {
    XCTAssertEqual(section("a", []).body(language: "ja"), "body")
  }

  func testBundledGuideLoadsAndHasParkingSections() throws {
    let url = try XCTUnwrap(Bundle.main.url(forResource: "settings_guide", withExtension: "json"))
    let guide = try SettingsGuide.load(from: url)
    XCTAssertFalse(guide.search("주차 녹화", limit: 3).isEmpty)
    XCTAssertFalse(guide.search("parking", limit: 3).isEmpty)
  }
}
```

- [ ] **Step 2: 실행해 실패 확인 (사용자 실행)** — `-only-testing:HubDevTests/SettingsGuideTests`
- [ ] **Step 3: 행 key 확인** — `ConfigurationDTO.swift` 에서 아래 6개 설정의 행 `key` 를 찾아 JSON 의 `settingKey` 와 맞춘다.
  `SettingViewController.isParkingSectionSetting(key:)`(`SettingViewController.swift:412`)가 쓰는 key(`parkmode` `parkrectime`
  `voltagelimit` `timelapse` `sleepmode` 등)가 기준이다. 충격·모션 감도의 행 key 는 이 함수에 없으므로 `ConfigurationDTO.swift` 에서 직접 찾는다.
- [ ] **Step 4: 구현**

`Hub/Resources/AIChat/settings_guide.json` (초안 — 기획 검수 대상)

```json
{
  "sections": [
    {
      "id": "parking_impact_sensitivity",
      "keywords": ["주차", "충격", "감도", "이벤트", "주차 녹화", "parking", "impact", "sensitivity"],
      "title": {"ko": "주차 충격 감도", "en": "Parking impact sensitivity"},
      "body": {
        "ko": "주차 중 충격을 얼마나 민감하게 감지할지 정합니다. 감도를 낮추면 문 닫는 소리나 지나가는 차량 진동으로 생기는 주차 이벤트 녹화가 줄어듭니다.",
        "en": "Sets how sensitive impact detection is while parked. Lowering it reduces parking event recordings caused by door slams or passing vehicles."
      },
      "configKey": "parksensorsen",
      "settingKey": "parksensorsen"
    },
    {
      "id": "motion_sensitivity",
      "keywords": ["주차", "모션", "움직임", "감도", "주차 녹화", "motion", "parking"],
      "title": {"ko": "모션 감도", "en": "Motion sensitivity"},
      "body": {
        "ko": "주차 중 화면 속 움직임을 감지해 녹화를 시작하는 감도입니다. 사람이나 차가 자주 지나가는 곳이라면 감도를 낮추거나 끄면 녹화가 줄어듭니다.",
        "en": "Sensitivity for starting a recording when motion is seen while parked. In busy places, lowering or turning it off reduces recordings."
      },
      "configKey": "frontmotionsensoren",
      "settingKey": "frontmotionsensoren"
    },
    {
      "id": "parking_recording_type",
      "keywords": ["주차", "타임랩스", "저전력", "녹화 방식", "주차 녹화", "timelapse", "low power", "parking"],
      "title": {"ko": "주차 녹화 방식", "en": "Parking recording type"},
      "body": {
        "ko": "타임랩스는 주차 시간 내내 낮은 프레임으로 이어 녹화하고, 저전력 모드는 충격이 있을 때만 녹화합니다. 녹화 파일을 줄이려면 저전력 모드를 고르세요.",
        "en": "Time-lapse records continuously at a low frame rate; low-power mode records only on impact. Choose low-power mode for fewer files."
      },
      "configKey": "timelapse",
      "settingKey": "timelapse"
    },
    {
      "id": "parking_mode",
      "keywords": ["주차", "주차 모드", "자동 주차", "주차 녹화", "parking mode"],
      "title": {"ko": "주차 녹화 모드", "en": "Parking mode"},
      "body": {
        "ko": "시동이 꺼졌을 때 주차 녹화로 들어갈지 정합니다. 끄면 주차 중에는 녹화하지 않습니다.",
        "en": "Sets whether the dashcam switches to parking recording when the engine is off. Turning it off stops recording while parked."
      },
      "configKey": "parkmode",
      "settingKey": "parkmode"
    },
    {
      "id": "parking_recording_time",
      "keywords": ["주차", "녹화 시간", "주차 시간", "주차 녹화", "parking time"],
      "title": {"ko": "주차 녹화 시간", "en": "Parking recording time"},
      "body": {
        "ko": "주차 녹화를 이어갈 최대 시간입니다. 짧게 하면 장시간 주차 시 녹화량과 배터리 소모가 줄어듭니다.",
        "en": "Maximum time to keep parking recording. Shorter values reduce recordings and battery use during long parking."
      },
      "configKey": "parkrectime",
      "settingKey": "parkrectime"
    },
    {
      "id": "cutoff_voltage",
      "keywords": ["방전", "배터리", "전압", "차단", "battery", "voltage", "cutoff"],
      "title": {"ko": "방전 차단 전압", "en": "Low voltage cutoff"},
      "body": {
        "ko": "차량 배터리 전압이 이 값 아래로 내려가면 녹화를 멈춰 방전을 막습니다. 값을 높이면 더 일찍 꺼집니다.",
        "en": "Stops recording when the car battery drops below this voltage to prevent drain. A higher value turns off sooner."
      },
      "configKey": "voltagelimit",
      "settingKey": "voltagelimit"
    }
  ]
}
```

`Hub/Domain/UseCases/AIChat/SettingsGuide.swift`

```swift
//
//  SettingsGuide.swift
//  Hub
//

import Foundation

struct SettingsGuideSection: Codable, Equatable {
  let id: String
  let keywords: [String]
  let title: [String: String]
  let body: [String: String]
  /// getconfiguration 키 — 현재 값을 읽을 때 쓴다.
  let configKey: String?
  /// 설정 화면 행 key — 바로가기 포커스에 쓴다.
  let settingKey: String?

  func title(language: String) -> String { title[language] ?? title["en"] ?? id }
  func body(language: String) -> String { body[language] ?? body["en"] ?? "" }
}

struct SettingsGuide: Equatable {
  let sections: [SettingsGuideSection]

  private struct File: Codable { let sections: [SettingsGuideSection] }

  static func load(from url: URL) throws -> SettingsGuide {
    let data = try Data(contentsOf: url)
    return SettingsGuide(sections: try JSONDecoder().decode(File.self, from: data).sections)
  }

  /// 질문에 들어간 키워드 수가 많은 순. 같으면 파일 순서. 하나도 안 걸리면 제외한다.
  func search(_ text: String, limit: Int) -> [SettingsGuideSection] {
    let lowered = text.lowercased()
    return sections.enumerated()
      .map { index, section in
        (index, section, section.keywords.filter { lowered.contains($0.lowercased()) }.count)
      }
      .filter { $0.2 > 0 }
      .sorted { $0.2 != $1.2 ? $0.2 > $1.2 : $0.0 < $1.0 }
      .prefix(limit)
      .map(\.1)
  }
}
```

- [ ] **Step 5: 테스트 통과 확인 (사용자 실행)** — Expected: 5 tests PASS

---

### Task 4: 엔진 의존성 프로토콜과 Data 구현

**Files:**
- Create: `Hub/Domain/Interface/Repository/AIChat/HubChatDependencies.swift`
- Create: `Hub/Data/AIChat/DeviceRecordingFileSource.swift`
- Create: `Hub/Data/AIChat/LocalRecordingFileSource.swift`
- Create: `Hub/Data/AIChat/SqlDriveHistorySource.swift`
- Create: `Hub/Data/AIChat/MapKitPlaceGeocoder.swift`
- Create: `Hub/Data/AIChat/CachedDeviceSettingSource.swift`

**Interfaces:**
- Consumes: Task 1·2 타입, 기존 `InformationService.getFileList(type:thumb:url:) async throws -> ResponseFileListModel`
  (`VueroidKit/.../Http/InformationService.swift:168`), `SqlQuery.selectHistoryFromMain(startDate:endDate:macAddress:range:)`(`SqlQuery.swift:50`),
  `SqlQuery.selectGpsFromMain(startDate:endDate:macAddress:)`(`:123`), `SqlQuery.getValidGPSNearTime(targetTime:macAddress:toleranceMinutes:)`(`:197`),
  `SqlQuery.getDeviceList()`(`:274`), `UrlList.downloadedPath()`(`UrlList.swift:129`), `FileManager.loadFileAtFolder(path:)`(`FileManager.swift:189`),
  `Current.isConnect`(`AppEnvironment.swift:288`), `AppManager.shared.deviceInfo?.macaddress`
- Produces (프로토콜, 엔진과 테스트 fake 가 쓴다):

```swift
//
//  HubChatDependencies.swift
//  Hub
//

import Foundation

/// 질문 → 검색 조건. 실패하면 throw 하고 엔진이 "이해하지 못함"으로 답한다.
protocol HubQueryParsing {
  func parse(_ text: String, context: HubChatContext, now: Date) async throws -> HubQuery
}

/// 가이드 본문과 현재 설정값만 근거로 짧은 안내문을 쓴다.
protocol HubGuideAnswering {
  func answer(
    question: String, sections: [SettingsGuideSection], currentValues: [String: String],
    language: String
  ) async throws -> String
}

protocol RecordingFileSource {
  func files(kinds: Set<RecordingKind>) async throws -> [RecordingFile]
}

protocol DriveHistorySource {
  /// 구간 안에 시작한 주행(TYPE 1). 최신 순.
  func drives(in interval: DateInterval) -> [HubDriveRecord]
  func route(of drive: HubDriveRecord) -> [HubCoordinate]
  func coordinate(near date: Date, macAddress: String) -> HubCoordinate?
}

protocol PlaceGeocoding {
  /// 못 찾거나 네트워크가 없으면 nil.
  func place(named name: String) async -> HubPlace?
}

protocol DeviceSettingSource {
  /// 연결 중일 때 키별 표시 문자열. 연결이 없거나 키가 없으면 빈 사전.
  func currentValues(keys: [String]) async -> [String: String]
}

protocol DeviceConnectionChecking {
  var isDeviceConnected: Bool { get }
}
```

- [ ] **Step 1: 프로토콜 파일 작성** (위 코드 그대로)

- [ ] **Step 2: `DeviceRecordingFileSource`** — 연결 세대(HTTP/WS)에 따라 목록 경로가 갈린다. **`FileListWifiViewModel.swift:410` 이 쓰는 경로를
  그대로 따른다**: 그 함수를 읽고 HTTP 세대면 `InformationService.getFileList`, WS 세대면 `Composers.fileCommandUseCase.send(to:completion:)`
  를 `withCheckedThrowingContinuation` 으로 감싼다. 판별 조건은 그 파일이 쓰는 것과 같은 것을 쓴다(새 조건을 만들지 않는다).

```swift
//
//  DeviceRecordingFileSource.swift
//  Hub
//

import Foundation
import VueroidKit

/// 연결된 단말 SD 카드 목록. 종류별로 getfilelist 를 한 번씩 부른다(썸네일 없이).
struct DeviceRecordingFileSource: RecordingFileSource {
  /// 종류(type) 하나의 목록을 가져온다. FileListWifiViewModel 과 같은 HTTP/WS 분기를 쓴다.
  let fetchList: (Int) async throws -> ResponseFileListModel

  func files(kinds: Set<RecordingKind>) async throws -> [RecordingFile] {
    var result: [RecordingFile] = []
    for kind in kinds.sorted(by: { $0.fileListType < $1.fileListType }) {
      let response = try await fetchList(kind.fileListType)
      result += response.list.compactMap { item in
        guard let parsed = RecordingFileName.parse(item.filename) else { return nil }
        return RecordingFile(
          fileName: item.filename, startedAt: parsed.startedAt, kind: parsed.kind,
          location: .device(
            streamPath: response.path, downloadUrl: item.url, channelbits: item.channelbits ?? 1))
      }
    }
    aiLogger.info("[AICHAT][QUERY] device files \(result.count) kinds=\(kinds.count)")
    return result
  }
}
```

  `fetchList` 의 실제 클로저는 Task 9 의 코디네이터가 `FileListWifiViewModel` 과 같은 분기로 만들어 넣는다.
  `ListModel.channelbits` 가 `Int?` 가 아니면 타입에 맞춰 고친다.

- [ ] **Step 3: `LocalRecordingFileSource`**

```swift
//
//  LocalRecordingFileSource.swift
//  Hub
//

import Foundation

/// 폰에 내려받은 영상(`Documents/DOWNLOADED`). 이름을 읽을 수 없는 파일은 건너뛴다.
struct LocalRecordingFileSource: RecordingFileSource {
  func files(kinds: Set<RecordingKind>) async throws -> [RecordingFile] {
    guard let folder = UrlList.downloadedPath() else { return [] }
    return FileManager.loadFileAtFolder(path: folder)
      .filter { $0.pathExtension.lowercased() == "mp4" }
      .compactMap { url in
        guard let parsed = RecordingFileName.parse(url.lastPathComponent),
          kinds.contains(parsed.kind)
        else { return nil }
        return RecordingFile(
          fileName: url.lastPathComponent, startedAt: parsed.startedAt, kind: parsed.kind,
          location: .local(url))
      }
  }
}
```

  내려받은 파일 이름이 `HubFileNameGenerator` 형식(`20250701_120710_INF_F_N.mp4`)이라 같은 파서로 읽힌다. 실제 DOWNLOADED 폴더의
  파일명을 시뮬레이터에서 한 번 확인하고, 다른 형식이 있으면 Task 1 테스트에 케이스를 추가한다.

- [ ] **Step 4: `SqlDriveHistorySource`** — 연결 단말이 있으면 그 mac, 없으면 DB 에 기록된 모든 단말을 합친다.

```swift
//
//  SqlDriveHistorySource.swift
//  Hub
//

import Foundation

struct SqlDriveHistorySource: DriveHistorySource {
  /// GPS 정수 좌표 → 도(°). TravelMapWifiViewModel 과 같은 배율.
  private static let gpsScale = 100_000.0

  func drives(in interval: DateInterval) -> [HubDriveRecord] {
    macAddresses().flatMap { mac in
      SqlQuery.selectHistoryFromMain(startDate: interval.start, endDate: interval.end, macAddress: mac)
        .filter { $0.TYPE == 1 }
        .map {
          HubDriveRecord(
            start: Date(timeIntervalSince1970: TimeInterval($0.START)),
            end: Date(timeIntervalSince1970: TimeInterval($0.END)),
            distance: $0.DISTANCE, eventCount: $0.EVTNUM, macAddress: mac)
        }
    }
    .sorted { $0.start > $1.start }
  }

  func route(of drive: HubDriveRecord) -> [HubCoordinate] {
    SqlQuery.selectGpsFromMain(startDate: drive.start, endDate: drive.end, macAddress: drive.macAddress)
      .compactMap(Self.coordinate)
  }

  func coordinate(near date: Date, macAddress: String) -> HubCoordinate? {
    SqlQuery.getValidGPSNearTime(
      targetTime: Int(date.timeIntervalSince1970), macAddress: macAddress, toleranceMinutes: 2
    ).flatMap(Self.coordinate)
  }

  private static func coordinate(_ gps: GPS) -> HubCoordinate? {
    guard gps.LATITUDE != 0, gps.LONGITUDE != 0 else { return nil }
    return HubCoordinate(
      latitude: Double(gps.LATITUDE) / gpsScale, longitude: Double(gps.LONGITUDE) / gpsScale)
  }

  private func macAddresses() -> [String] {
    if let mac = AppManager.shared.deviceInfo?.macaddress, !mac.isEmpty { return [mac] }
    return SqlQuery.getDeviceList().map(\.macAdr)
  }
}
```

  확인할 것: `TravelMapWifiViewModel.swift:172` 의 배율이 100000 인지, `HISTORY.TYPE == 1` 이 주행인지(`HISTORY.toDomain` 의 `sumTime1`
  기준), `selectHistoryFromMain` 이 mac 의 콜론을 스스로 제거하는지(`getValidGPSNearTime` 은 제거한다).

- [ ] **Step 5: `MapKitPlaceGeocoder`** — `CLGeocoder` 는 iOS 26 에서 deprecated 라 `MKLocalSearch` 를 쓴다. 5초 제한.

```swift
//
//  MapKitPlaceGeocoder.swift
//  Hub
//

import MapKit

struct MapKitPlaceGeocoder: PlaceGeocoding {
  private static let minimumRadius = 5_000.0
  private static let metersPerDegree = 111_000.0
  /// 국내 검색 힌트 — 대한민국 중심 ±5°.
  private static let koreaRegion = MKCoordinateRegion(
    center: CLLocationCoordinate2D(latitude: 36.5, longitude: 127.8),
    span: MKCoordinateSpan(latitudeDelta: 5, longitudeDelta: 5))

  func place(named name: String) async -> HubPlace? {
    let request = MKLocalSearch.Request()
    request.naturalLanguageQuery = name
    request.region = Self.koreaRegion
    request.resultTypes = [.address, .pointOfInterest]
    do {
      let response = try await withTimeout(seconds: 5) {
        try await MKLocalSearch(request: request).start()
      }
      let region = response.boundingRegion
      let radius = max(Self.minimumRadius, region.span.latitudeDelta * Self.metersPerDegree / 2)
      return HubPlace(
        center: HubCoordinate(latitude: region.center.latitude, longitude: region.center.longitude),
        radiusMeters: radius)
    } catch {
      aiLogger.error("[AICHAT][QUERY] geocode failed: \(error.localizedDescription)")
      return nil
    }
  }
}

/// 작업이 제한 시간을 넘기면 취소하고 `CancellationError` 를 던진다.
private func withTimeout<T>(seconds: Double, _ work: @escaping () async throws -> T) async throws -> T {
  try await withThrowingTaskGroup(of: T.self) { group in
    group.addTask { try await work() }
    group.addTask {
      try await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
      throw CancellationError()
    }
    guard let first = try await group.next() else { throw CancellationError() }
    group.cancelAll()
    return first
  }
}
```

  `T` 가 `Sendable` 이 아니라는 경고가 나오면 반환을 `HubPlace?` 로 좁혀 `withTimeout` 안에서 변환까지 끝낸다.

- [ ] **Step 6: `CachedDeviceSettingSource`** — 설정 화면이 이미 받아 둔 `AppManager.shared.dashcamWifiConfig` 를 먼저 쓰고, 없으면 설정 화면과
  같은 getconfiguration 경로(`SettingWifiViewModel` 의 호출부)를 한 번 부른다. 표시 문자열은 `ConfigurationDTO.swift` 의 `ConfigValues` 로 만든다.
  이 클래스는 `fetchConfig` 클로저(코디네이터가 주입)와 `display` 클로저를 받는다 — 둘 다 기존 코드 호출만 한다.

```swift
//
//  CachedDeviceSettingSource.swift
//  Hub
//

import Foundation

struct CachedDeviceSettingSource: DeviceSettingSource {
  let connection: DeviceConnectionChecking
  /// 키 → 원시 값. 캐시가 있으면 캐시, 없으면 getconfiguration 1회.
  let fetchConfig: () async throws -> [String: String]
  /// (키, 원시 값) → 화면 표기. ConfigValues 를 쓴다.
  let display: (String, String) -> String

  func currentValues(keys: [String]) async -> [String: String] {
    guard connection.isDeviceConnected else { return [:] }
    do {
      let config = try await fetchConfig()
      var result: [String: String] = [:]
      for key in keys {
        if let raw = config[key] { result[key] = display(key, raw) }
      }
      return result
    } catch {
      aiLogger.error("[AICHAT][GUIDE] config fetch failed: \(error.localizedDescription)")
      return [:]
    }
  }
}
```

  `ConfigurationModel` 을 `[String: String]` 으로 바꾸는 작은 변환은 코디네이터(Task 9)에서 `ConfigurationModel` 의 프로퍼티를
  키 이름 그대로 옮긴다(가이드에 쓰는 6개 키만).

- [ ] **Step 7: `Current` 어댑터** — 엔진이 전역을 직접 읽지 않도록 한 줄짜리 어댑터를 같은 파일(`CachedDeviceSettingSource.swift`) 아래에 둔다.

```swift
/// 엔진이 `Current` 를 직접 보지 않게 하는 어댑터.
struct CurrentConnection: DeviceConnectionChecking {
  var isDeviceConnected: Bool { Current.isConnect }
}
```

- [ ] **Step 8: 컴파일 확인 (사용자 실행)** — `xcodebuild -project Hub.xcodeproj -scheme Hub -configuration Debug build`.
  Data 구현은 DB·네트워크 의존이라 단위 테스트 대신 Task 6 엔진 테스트(fake)와 Task 10 실기 매트릭스로 검증한다.

---

### Task 5: 파서 프롬프트 (백엔드 공용)

**Files:**
- Create: `Hub/Domain/UseCases/AIChat/HubQueryPrompt.swift`
- Test: `HubDevTests/HubQueryPromptTests.swift`

**Interfaces:**
- Consumes: `HubChatContext`, `HubDriveSummary`, `HubDriveEvent`
- Produces: `enum HubQueryPrompt { static let instructions: String; static func userPrompt(text: String, context: HubChatContext, now: Date, calendar: Calendar) -> String }`

FM·MLX 모두 같은 지시문을 쓴다. 날짜 계산은 LLM 에 맡기지 않는다 — 오늘 날짜만 알려 주고 `daysAgo` 같은 상대값을 받는다.

- [ ] **Step 1: 실패하는 테스트**

```swift
//
//  HubQueryPromptTests.swift
//  HubDevTests
//

import XCTest

@testable import Hub_Dev

final class HubQueryPromptTests: XCTestCase {
  private var calendar: Calendar = {
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = TimeZone(identifier: "Asia/Seoul")!
    return calendar
  }()

  private func at(_ d: Int, _ h: Int, _ m: Int) -> Date {
    calendar.date(from: DateComponents(year: 2026, month: 11, day: d, hour: h, minute: m))!
  }

  func testIncludesTodayAndQuestion() {
    let prompt = HubQueryPrompt.userPrompt(
      text: "어제 영상", context: HubChatContext(), now: at(6, 10, 0), calendar: calendar)
    XCTAssertTrue(prompt.contains("2026-11-06"))
    XCTAssertTrue(prompt.contains("어제 영상"))
    XCTAssertFalse(prompt.contains("previous result"))
  }

  func testDescribesPreviousDriveAndEvent() {
    let drive = HubDriveRecord(
      start: at(5, 18, 12), end: at(5, 19, 5), distance: 31_000, eventCount: 1, macAddress: "m")
    let event = HubDriveEvent(time: at(5, 18, 40), file: nil, coordinate: nil)
    var context = HubChatContext()
    context.lastDrive = HubDriveSummary(drive: drive, route: [], events: [event])
    context.lastEvent = event
    let prompt = HubQueryPrompt.userPrompt(
      text: "위 경우의 비디오", context: context, now: at(6, 10, 0), calendar: calendar)
    XCTAssertTrue(prompt.contains("previous result: drive 2026-11-05 18:12-19:05"))
    XCTAssertTrue(prompt.contains("event 18:40"))
  }

  func testInstructionsListAllIntents() {
    for intent in HubQueryIntent.allCases {
      XCTAssertTrue(HubQueryPrompt.instructions.contains(intent.rawValue))
    }
  }
}
```

- [ ] **Step 2: 실패 확인 (사용자 실행)** — `-only-testing:HubDevTests/HubQueryPromptTests`
- [ ] **Step 3: 구현**

```swift
//
//  HubQueryPrompt.swift
//  Hub
//

import Foundation

/// 질문 파서 지시문. FM·MLX 공용이며 필드 이름은 `HubQueryDTO` 와 같다.
enum HubQueryPrompt {
  static let instructions = """
    You convert a question about a dashcam app (Hub) into search fields. Do not answer the question.
    Questions are usually Korean. Fill only what the user said; leave other fields empty.
    intent: video (show a recording), drive (show a drive route or location), \
    settingsHelp (how to change settings or use the app), unknown (anything else).
    daysAgo: 0 today, 1 yesterday (어제), 2 the day before (그저께). month/dayOfMonth only for an explicit date.
    hour/minute: 24-hour clock. "아침 9시 30분" -> 9, 30. "저녁 6시" -> 18, 0.
    period: morningCommute (출근길), eveningCommute (퇴근길), morning, afternoon, evening, night, any.
    origin/destination: place names exactly as written ("판교에서 인천" -> 판교, 인천).
    event: impact for accidents, impacts, near misses (사고, 충격, 사고날 뻔, 급정거); otherwise any.
    reference: previous when the user points at the last result (위 경우, 그때, 그 영상); otherwise none.
    topic: for settingsHelp, the key subject in the user's words ("주차 녹화").
    Examples:
    "어제 아침 출근길중 9시 30분경 비디오를 보여줘" -> intent video, daysAgo 1, hour 9, minute 30, period morningCommute
    "판교에서 인천가는 퇴근길에 사고날뻔한 적이 있었어 그때 경로와 위치를 보여줘" -> intent drive, period eveningCommute, origin 판교, destination 인천, event impact
    "위 경우의 비디오를 보여줘" -> intent video, reference previous
    "설정에서 뭘 바꿔야 주차녹화가 줄어들지" -> intent settingsHelp, topic 주차 녹화
    """

  /// 오늘 날짜·요일과 직전 결과 요약을 붙인다. 날짜 계산은 앱이 하므로 LLM 에는 기준만 준다.
  static func userPrompt(text: String, context: HubChatContext, now: Date, calendar: Calendar)
    -> String
  {
    let day = format(now, "yyyy-MM-dd (EEE) HH:mm", calendar)
    var lines = ["today: \(day)"]
    if let drive = context.lastDrive?.drive {
      var line =
        "previous result: drive \(format(drive.start, "yyyy-MM-dd HH:mm", calendar))"
        + "-\(format(drive.end, "HH:mm", calendar))"
      if let event = context.lastEvent {
        line += ", event \(format(event.time, "HH:mm", calendar))"
      }
      lines.append(line)
    } else if let video = context.lastVideo {
      lines.append("previous result: video \(format(video.startedAt, "yyyy-MM-dd HH:mm", calendar))")
    }
    lines.append("question: \(text)")
    return lines.joined(separator: "\n")
  }

  private static func format(_ date: Date, _ pattern: String, _ calendar: Calendar) -> String {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = calendar.timeZone
    formatter.dateFormat = pattern
    return formatter.string(from: date)
  }
}
```

- [ ] **Step 4: 통과 확인 (사용자 실행)** — Expected: 3 tests PASS

---

### Task 6: HubChatEngine

**Files:**
- Create: `Hub/Domain/UseCases/AIChat/HubChatEngine.swift`
- Test: `HubDevTests/HubChatEngineTests.swift`

**Interfaces:**
- Consumes: Task 1–5 전부
- Produces:
  - `final class HubChatEngine { struct Dependencies {…}; init(_ dependencies: Dependencies); func respond(to text: String, context: HubChatContext) async -> HubChatAnswer }`
  - 상수 `HubChatEngine.maxVideoCards = 5`, `HubChatEngine.maxDrivesToMatch = 20`

동작 규칙:

| 의도 | 처리 |
|---|---|
| video + `reference: .previous` | 직전 이벤트의 파일 → 없으면 직전 주행 구간의 이벤트 파일 → 없으면 직전 영상. 모두 없으면 `.noVideo(.notFound)` |
| video | 연결 중이면 단말, 아니면 로컬 파일. 종류는 `event == .impact` 면 `[.event]`, 아니면 `[.drive, .event, .manual]`. 기준 시각이 있으면 `RecordingPicker` 1개, 없으면 구간·시간대 안 최신 5개. 비연결 + 결과 없음이면 `.noVideo(.needsConnection)` |
| drive | 구간·시간대 안 주행(최신 20개) → 지명이 있으면 두 지명을 동시에 검색해 `DriveMatcher`, 지명 검색이 하나라도 실패하면 그 지명은 빼고 `.timeOnly` → `event == .impact` 면 이벤트 파일(파일을 못 얻으면 `eventCount > 0`)이 있는 주행만 → 가장 최근 1건을 요약(경로 + 이벤트별 GPS) |
| settingsHelp | `guide.search(topic + 질문, 3)` → 현재 값 → answerer. answerer 실패 시 첫 섹션 본문. 섹션이 없으면 `.noGuide` |
| unknown / 파싱 실패 | `.notUnderstood` |

- [ ] **Step 1: 실패하는 테스트** — `HubDevTests/HubChatEngineTests.swift`. 4개 예시 질문 시나리오를 fake 로 재현한다.

```swift
//
//  HubChatEngineTests.swift
//  HubDevTests
//
//  예시 질문 4개 + 비연결·지명 실패·파싱 실패 경로. 기준 2026-11-06 10:00 KST
//

import XCTest

@testable import Hub_Dev

private struct FakeParser: HubQueryParsing {
  let query: HubQuery?
  func parse(_ text: String, context: HubChatContext, now: Date) async throws -> HubQuery {
    guard let query else { throw URLError(.cannotParseResponse) }
    return query
  }
}

private struct FakeAnswerer: HubGuideAnswering {
  let text: String?
  func answer(
    question: String, sections: [SettingsGuideSection], currentValues: [String: String],
    language: String
  ) async throws -> String {
    guard let text else { throw URLError(.timedOut) }
    return text + "|" + currentValues.keys.sorted().joined(separator: ",")
  }
}

private struct FakeFiles: RecordingFileSource {
  let files: [RecordingFile]
  func files(kinds: Set<RecordingKind>) async throws -> [RecordingFile] {
    files.filter { kinds.contains($0.kind) }
  }
}

private struct FakeHistory: DriveHistorySource {
  let records: [HubDriveRecord]
  let routes: [Date: [HubCoordinate]]
  let point: HubCoordinate
  func drives(in interval: DateInterval) -> [HubDriveRecord] {
    records.filter { interval.contains($0.start) }.sorted { $0.start > $1.start }
  }
  func route(of drive: HubDriveRecord) -> [HubCoordinate] { routes[drive.start] ?? [] }
  func coordinate(near date: Date, macAddress: String) -> HubCoordinate? { point }
}

private struct FakeGeocoder: PlaceGeocoding {
  let places: [String: HubPlace]
  func place(named name: String) async -> HubPlace? { places[name] }
}

private struct FakeSettings: DeviceSettingSource {
  func currentValues(keys: [String]) async -> [String: String] {
    Dictionary(uniqueKeysWithValues: keys.map { ($0, "high") })
  }
}

private struct FakeConnection: DeviceConnectionChecking {
  let isDeviceConnected: Bool
}

final class HubChatEngineTests: XCTestCase {
  private var calendar: Calendar = {
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = TimeZone(identifier: "Asia/Seoul")!
    return calendar
  }()

  private func at(_ d: Int, _ h: Int, _ m: Int, _ s: Int = 0) -> Date {
    calendar.date(from: DateComponents(year: 2026, month: 11, day: d, hour: h, minute: m, second: s))!
  }

  private let pangyo = HubCoordinate(latitude: 37.3947, longitude: 127.1112)
  private let incheon = HubCoordinate(latitude: 37.4563, longitude: 126.7052)

  private func file(_ date: Date, _ kind: RecordingKind) -> RecordingFile {
    RecordingFile(
      fileName: "\(date.timeIntervalSince1970)_\(kind.rawValue)", startedAt: date, kind: kind,
      location: .device(streamPath: "/sd", downloadUrl: nil, channelbits: 1))
  }

  private let guide = SettingsGuide(sections: [
    SettingsGuideSection(
      id: "parking_impact_sensitivity", keywords: ["주차", "충격"],
      title: ["ko": "주차 충격 감도", "en": "Parking impact"], body: ["ko": "감도를 낮추세요", "en": "Lower it"],
      configKey: "parksensorsen", settingKey: "parksensorsen")
  ])

  private func engine(
    query: HubQuery?, files: [RecordingFile] = [], connected: Bool = true,
    records: [HubDriveRecord] = [], routes: [Date: [HubCoordinate]] = [:],
    places: [String: HubPlace] = [:], answer: String? = "답"
  ) -> HubChatEngine {
    HubChatEngine(
      HubChatEngine.Dependencies(
        parser: FakeParser(query: query), answerer: FakeAnswerer(text: answer), guide: guide,
        deviceFiles: FakeFiles(files: files), localFiles: FakeFiles(files: []),
        history: FakeHistory(records: records, routes: routes, point: pangyo),
        geocoder: FakeGeocoder(places: places), settings: FakeSettings(),
        connection: FakeConnection(isDeviceConnected: connected),
        now: { self.at(6, 10, 0) }, calendar: calendar, language: "ko"))
  }

  // 예시 1: 어제 아침 출근길중 9시 30분경 비디오
  func testVideoAtClockPicksContainingFile() async {
    let target = file(at(5, 9, 29, 40), .drive)
    let query = HubQuery(
      intent: .video, day: .daysAgo(1), clock: HubClockTime(hour: 9, minute: 30),
      period: .morningCommute)
    let answer = await engine(
      query: query, files: [file(at(5, 9, 28, 40), .drive), target, file(at(5, 9, 31, 0), .drive)]
    ).respond(to: "q", context: HubChatContext())
    XCTAssertEqual(answer.reply, .videos(count: 1))
    XCTAssertEqual(answer.cards, [.video(target)])
    XCTAssertEqual(answer.context.lastVideo, target)
  }

  // 예시 2: 판교→인천 퇴근길 사고날 뻔
  func testDriveWithPlacesAndImpactReturnsEventLocation() async {
    let matched = HubDriveRecord(
      start: at(3, 18, 0), end: at(3, 19, 0), distance: 40_000, eventCount: 1, macAddress: "m")
    let reverse = HubDriveRecord(
      start: at(4, 18, 0), end: at(4, 19, 0), distance: 40_000, eventCount: 1, macAddress: "m")
    let event = file(at(3, 18, 40), .event)
    let query = HubQuery(
      intent: .drive, period: .eveningCommute, origin: "판교", destination: "인천", event: .impact)
    let answer = await engine(
      query: query, files: [event, file(at(4, 18, 30), .event)],
      records: [matched, reverse],
      routes: [matched.start: [pangyo, incheon], reverse.start: [incheon, pangyo]],
      places: [
        "판교": HubPlace(center: pangyo, radiusMeters: 5_000),
        "인천": HubPlace(center: incheon, radiusMeters: 5_000),
      ]
    ).respond(to: "q", context: HubChatContext())
    XCTAssertEqual(answer.reply, .drive(.matched))
    guard case .drive(let summary) = answer.cards.first else { return XCTFail("drive card 없음") }
    XCTAssertEqual(summary.drive, matched)
    XCTAssertEqual(summary.events.map(\.file), [event])
    XCTAssertEqual(summary.events.first?.coordinate, pangyo)
    XCTAssertEqual(answer.context.lastEvent?.file, event)
  }

  // 예시 3: 위 경우의 비디오
  func testPreviousReferenceUsesLastEventFile() async {
    let event = file(at(3, 18, 40), .event)
    var context = HubChatContext()
    context.lastEvent = HubDriveEvent(time: event.startedAt, file: event, coordinate: pangyo)
    let answer = await engine(query: HubQuery(intent: .video, reference: .previous))
      .respond(to: "q", context: context)
    XCTAssertEqual(answer.cards, [.video(event)])
  }

  // 예시 4: 주차 녹화 줄이기
  func testSettingsHelpUsesGuideAndCurrentValues() async {
    let answer = await engine(query: HubQuery(intent: .settingsHelp, topic: "주차 녹화"))
      .respond(to: "설정에서 뭘 바꿔야 주차녹화가 줄어들지", context: HubChatContext())
    XCTAssertEqual(answer.reply, .guide(text: "답|parksensorsen"))
    XCTAssertEqual(answer.cards, [.setting(key: "parksensorsen", title: "주차 충격 감도")])
  }

  func testSettingsHelpFallsBackToBodyWhenAnswererFails() async {
    let answer = await engine(query: HubQuery(intent: .settingsHelp, topic: "주차"), answer: nil)
      .respond(to: "q", context: HubChatContext())
    XCTAssertEqual(answer.reply, .guide(text: "감도를 낮추세요"))
  }

  func testGeocodeFailureFallsBackToTimeOnly() async {
    let drive = HubDriveRecord(
      start: at(3, 18, 0), end: at(3, 19, 0), distance: 1, eventCount: 0, macAddress: "m")
    let query = HubQuery(intent: .drive, period: .eveningCommute, origin: "없는곳")
    let answer = await engine(query: query, records: [drive], routes: [drive.start: [pangyo]])
      .respond(to: "q", context: HubChatContext())
    XCTAssertEqual(answer.reply, .drive(.timeOnly))
  }

  func testDisconnectedWithoutLocalFilesAsksForConnection() async {
    let query = HubQuery(intent: .video, day: .daysAgo(1))
    let answer = await engine(query: query, connected: false)
      .respond(to: "q", context: HubChatContext())
    XCTAssertEqual(answer.reply, .noVideo(.needsConnection))
  }

  func testParseFailureIsNotUnderstoodAndKeepsContext() async {
    var context = HubChatContext()
    context.lastVideo = file(at(5, 9, 0), .drive)
    let answer = await engine(query: nil).respond(to: "q", context: context)
    XCTAssertEqual(answer.reply, .notUnderstood)
    XCTAssertEqual(answer.context, context)
  }
}
```

- [ ] **Step 2: 실패 확인 (사용자 실행)** — `-only-testing:HubDevTests/HubChatEngineTests`
- [ ] **Step 3: 구현** — `Hub/Domain/UseCases/AIChat/HubChatEngine.swift`

```swift
//
//  HubChatEngine.swift
//  Hub
//

import Foundation

/// 질문 하나를 답변 하나로. LLM 은 파싱·가이드 문장에만 쓰고 조회·매칭은 여기서 결정적으로 한다.
final class HubChatEngine {
  static let maxVideoCards = 5
  static let maxDrivesToMatch = 20

  struct Dependencies {
    let parser: HubQueryParsing
    let answerer: HubGuideAnswering
    let guide: SettingsGuide
    let deviceFiles: RecordingFileSource
    let localFiles: RecordingFileSource
    let history: DriveHistorySource
    let geocoder: PlaceGeocoding
    let settings: DeviceSettingSource
    let connection: DeviceConnectionChecking
    let now: () -> Date
    let calendar: Calendar
    let language: String
  }

  private let deps: Dependencies

  init(_ dependencies: Dependencies) {
    deps = dependencies
  }

  /// 실패해도 throw 하지 않고 답변 종류로 돌려준다. 실패 시 context 는 그대로 둔다.
  func respond(to text: String, context: HubChatContext) async -> HubChatAnswer {
    let now = deps.now()
    let query: HubQuery
    do {
      query = try await deps.parser.parse(text, context: context, now: now)
    } catch {
      aiLogger.error("[AICHAT][PARSE] failed: \(error.localizedDescription)")
      return HubChatAnswer(reply: .notUnderstood, cards: [], context: context)
    }
    aiLogger.info("[AICHAT][PARSE] intent=\(query.intent.rawValue) ref=\(query.reference.rawValue)")
    switch query.intent {
    case .video:
      return await videos(for: query, context: context, now: now)
    case .drive:
      return await drive(for: query, context: context, now: now)
    case .settingsHelp:
      return await guideAnswer(for: query, question: text, context: context)
    case .unknown:
      return HubChatAnswer(reply: .notUnderstood, cards: [], context: context)
    }
  }

  // MARK: - video

  private func videos(for query: HubQuery, context: HubChatContext, now: Date) async
    -> HubChatAnswer
  {
    if query.reference == .previous {
      return await previousVideo(context: context)
    }
    let kinds: Set<RecordingKind> = query.event == .impact ? [.event] : [.drive, .event, .manual]
    let window = HubQueryResolver.window(for: query, now: now, calendar: deps.calendar)
    let all = await files(kinds: kinds)
    let picked: [RecordingFile]
    if let anchor = window.anchor {
      picked = RecordingPicker.file(
        at: anchor, in: all, tolerance: HubQueryResolver.anchorTolerance
      ).map { [$0] } ?? []
    } else {
      picked = Array(
        all.filter { window.contains($0.startedAt, calendar: deps.calendar) }
          .sorted { $0.startedAt > $1.startedAt }
          .prefix(Self.maxVideoCards))
    }
    guard let first = picked.first else {
      return HubChatAnswer(reply: .noVideo(noResultReason()), cards: [], context: context)
    }
    var next = context
    next.lastVideo = first
    return HubChatAnswer(
      reply: .videos(count: picked.count), cards: picked.map(HubChatCard.video), context: next)
  }

  private func previousVideo(context: HubChatContext) async -> HubChatAnswer {
    if let file = context.lastEvent?.file {
      return videoAnswer(file, context: context)
    }
    if let drive = context.lastDrive?.drive {
      let inDrive = await files(kinds: [.event, .drive])
        .filter { $0.startedAt >= drive.start && $0.startedAt <= drive.end }
        .sorted { ($0.kind == .event ? 0 : 1, $0.startedAt) < ($1.kind == .event ? 0 : 1, $1.startedAt) }
      if let file = inDrive.first { return videoAnswer(file, context: context) }
    }
    if let file = context.lastVideo {
      return videoAnswer(file, context: context)
    }
    return HubChatAnswer(reply: .noVideo(.notFound), cards: [], context: context)
  }

  private func videoAnswer(_ file: RecordingFile, context: HubChatContext) -> HubChatAnswer {
    var next = context
    next.lastVideo = file
    return HubChatAnswer(reply: .videos(count: 1), cards: [.video(file)], context: next)
  }

  // MARK: - drive

  private func drive(for query: HubQuery, context: HubChatContext, now: Date) async
    -> HubChatAnswer
  {
    let window = HubQueryResolver.window(for: query, now: now, calendar: deps.calendar)
    let candidates = deps.history.drives(in: window.interval)
      .filter { window.contains($0.start, calendar: deps.calendar) }
      .prefix(Self.maxDrivesToMatch)

    async let originPlace = place(query.origin)
    async let destinationPlace = place(query.destination)
    let (origin, destination) = await (originPlace, destinationPlace)
    let placeMatch: HubPlaceMatch =
      (query.origin != nil && origin == nil) || (query.destination != nil && destination == nil)
      ? .timeOnly : .matched

    let eventFiles = query.event == .impact ? await files(kinds: [.event]) : []
    for drive in candidates {
      let route = deps.history.route(of: drive)
      guard DriveMatcher.matches(route: route, origin: origin, destination: destination) else {
        continue
      }
      let events = eventFiles.filter { $0.startedAt >= drive.start && $0.startedAt <= drive.end }
      if query.event == .impact, events.isEmpty, eventFiles.isEmpty == false || drive.eventCount == 0 {
        continue
      }
      let driveEvents = events.map {
        HubDriveEvent(
          time: $0.startedAt, file: $0,
          coordinate: deps.history.coordinate(near: $0.startedAt, macAddress: drive.macAddress))
      }
      let summary = HubDriveSummary(drive: drive, route: route, events: driveEvents)
      var next = context
      next.lastDrive = summary
      next.lastEvent = driveEvents.first
      return HubChatAnswer(reply: .drive(placeMatch), cards: [.drive(summary)], context: next)
    }
    return HubChatAnswer(reply: .noDrive(.notFound), cards: [], context: context)
  }

  private func place(_ name: String?) async -> HubPlace? {
    guard let name else { return nil }
    return await deps.geocoder.place(named: name)
  }

  // MARK: - settings help

  private func guideAnswer(for query: HubQuery, question: String, context: HubChatContext) async
    -> HubChatAnswer
  {
    let sections = deps.guide.search([query.topic, question].compactMap { $0 }.joined(separator: " "), limit: 3)
    guard let first = sections.first else {
      return HubChatAnswer(reply: .noGuide, cards: [], context: context)
    }
    let values = await deps.settings.currentValues(keys: sections.compactMap(\.configKey))
    let text: String
    do {
      text = try await deps.answerer.answer(
        question: question, sections: sections, currentValues: values, language: deps.language)
    } catch {
      aiLogger.error("[AICHAT][GUIDE] answer failed: \(error.localizedDescription)")
      text = first.body(language: deps.language)
    }
    let cards = sections.compactMap { section -> HubChatCard? in
      guard let key = section.settingKey else { return nil }
      return .setting(key: key, title: section.title(language: deps.language))
    }
    return HubChatAnswer(reply: .guide(text: text), cards: cards, context: context)
  }

  // MARK: - helpers

  /// 연결 중이면 단말, 아니면 내려받은 파일. 목록 실패는 빈 목록으로 보고 로그를 남긴다.
  private func files(kinds: Set<RecordingKind>) async -> [RecordingFile] {
    let source = deps.connection.isDeviceConnected ? deps.deviceFiles : deps.localFiles
    do {
      return try await source.files(kinds: kinds)
    } catch {
      aiLogger.error("[AICHAT][QUERY] file list failed: \(error.localizedDescription)")
      return []
    }
  }

  private func noResultReason() -> HubNoResultReason {
    deps.connection.isDeviceConnected ? .notFound : .needsConnection
  }
}
```

  `drive(for:)` 의 이벤트 필터 조건을 풀어 쓰면: impact 를 찾는데 이 주행에 이벤트 파일이 없을 때,
  ① 파일 목록 자체는 받아 왔다면(덮어써져 없는 것) 건너뛰고 ② 목록을 못 받았는데 DB 상 이벤트도 0건이면 건너뛴다.
  목록을 못 받았지만 DB 에 이벤트가 있으면 카드에 이벤트 없이 경로만 보여 준다. 이 조건이 읽기 어려우면 `private func
  skipsForMissingEvent(...)` 로 빼고 같은 테스트로 검증한다.

- [ ] **Step 4: 통과 확인 (사용자 실행)** — Expected: 8 tests PASS

---

### Task 7: Foundation Models 백엔드

**Files:**
- Create: `Hub/Data/AIChat/FoundationModels/FMQueryParser.swift`
- Create: `Hub/Data/AIChat/FoundationModels/FMGuideAnswerer.swift`
- Create: `Hub/Data/AIChat/AIChatAvailability.swift`
- Test: `HubDevTests/FMQueryParserEvalTests.swift` (실기 전용, 조건 안 맞으면 skip)

**Interfaces:**
- Consumes: `HubQueryParsing`, `HubGuideAnswering`, `HubQueryPrompt`, `HubQueryDTO`, `HubQueryMapper`
- Produces:
  - `@available(iOS 26.0, *) struct FMQueryParser: HubQueryParsing`
  - `@available(iOS 26.0, *) struct FMGuideAnswerer: HubGuideAnswering`
  - `enum AIChatUnavailableReason: Equatable { case osTooOld, appleIntelligenceOff, deviceNotEligible, modelNotReady, languageNotSupported }`
  - `enum AIChatBackend: Equatable { case foundationModels; case unavailable(AIChatUnavailableReason) }`
  - `enum AIChatAvailability { static func current() -> AIChatBackend }`

- [ ] **Step 1: `FMQueryParser`**

```swift
//
//  FMQueryParser.swift
//  Hub
//

#if canImport(FoundationModels)
  import Foundation
  import FoundationModels

  /// FM 구조화 출력. 필드는 `HubQueryDTO` 와 1:1 이고 검증은 `HubQueryMapper` 가 한다.
  @available(iOS 26.0, *)
  @Generable
  struct FMHubQuery {
    @Guide(description: "video, drive, settingsHelp, unknown 중 하나", .anyOf(["video", "drive", "settingsHelp", "unknown"]))
    var intent: String
    @Guide(description: "며칠 전인지. 오늘 0, 어제 1. 날짜를 말하지 않았으면 비운다", .range(0...365))
    var daysAgo: Int?
    @Guide(description: "명시한 날짜의 월", .range(1...12))
    var month: Int?
    @Guide(description: "명시한 날짜의 일", .range(1...31))
    var dayOfMonth: Int?
    @Guide(description: "24시간제 시", .range(0...23))
    var hour: Int?
    @Guide(description: "분", .range(0...59))
    var minute: Int?
    @Guide(
      description: "시간대",
      .anyOf(["any", "morningCommute", "eveningCommute", "morning", "afternoon", "evening", "night"]))
    var period: String
    @Guide(description: "출발지 지명, 말하지 않았으면 비운다")
    var origin: String?
    @Guide(description: "도착지 지명, 말하지 않았으면 비운다")
    var destination: String?
    @Guide(description: "사고·충격·사고날 뻔이면 impact", .anyOf(["any", "impact"]))
    var event: String
    @Guide(description: "직전 결과를 가리키면 previous", .anyOf(["none", "previous"]))
    var reference: String
    @Guide(description: "settingsHelp 일 때 핵심 주제어")
    var topic: String?

    var dto: HubQueryDTO {
      HubQueryDTO(
        intent: intent, daysAgo: daysAgo, month: month, dayOfMonth: dayOfMonth, hour: hour,
        minute: minute, period: period, origin: origin, destination: destination, event: event,
        reference: reference, topic: topic)
    }
  }

  @available(iOS 26.0, *)
  struct FMQueryParser: HubQueryParsing {
    let calendar: Calendar

    /// 턴마다 새 세션 — 직전 결과는 프롬프트로 넘기므로 세션 기록이 필요 없다.
    func parse(_ text: String, context: HubChatContext, now: Date) async throws -> HubQuery {
      let session = LanguageModelSession(instructions: HubQueryPrompt.instructions)
      let prompt = HubQueryPrompt.userPrompt(text: text, context: context, now: now, calendar: calendar)
      let response = try await session.respond(
        to: prompt, generating: FMHubQuery.self, options: GenerationOptions(temperature: 0))
      return HubQueryMapper.map(response.content.dto)
    }
  }
#endif
```

  Task 0 에서 옵셔널 `Int?` 에 `.range` 가 안 붙으면 `.range` 를 빼고 description 만 남긴다(범위는 `HubQueryMapper` 가 이미 거른다).

- [ ] **Step 2: `FMGuideAnswerer`**

```swift
//
//  FMGuideAnswerer.swift
//  Hub
//

#if canImport(FoundationModels)
  import Foundation
  import FoundationModels

  @available(iOS 26.0, *)
  struct FMGuideAnswerer: HubGuideAnswering {
    private static let instructions = """
      You are the settings helper of a dashcam app. Answer only from the guide and current values given.
      Reply in the user's language in at most 3 short sentences. Do not mention settings that are not in the guide.
      Never say you will change a setting; tell the user which setting to change.
      """

    func answer(
      question: String, sections: [SettingsGuideSection], currentValues: [String: String],
      language: String
    ) async throws -> String {
      let guide = sections.map { section in
        var line = "- \(section.title(language: language)): \(section.body(language: language))"
        if let key = section.configKey, let value = currentValues[key] {
          line += " (current: \(value))"
        }
        return line
      }.joined(separator: "\n")
      let session = LanguageModelSession(instructions: Self.instructions)
      let response = try await session.respond(
        to: "guide:\n\(guide)\n\nquestion: \(question)",
        options: GenerationOptions(temperature: 0.3, maximumResponseTokens: 200))
      return response.content.trimmingCharacters(in: .whitespacesAndNewlines)
    }
  }
#endif
```

- [ ] **Step 3: `AIChatAvailability`**

```swift
//
//  AIChatAvailability.swift
//  Hub
//

import Foundation

#if canImport(FoundationModels)
  import FoundationModels
#endif

enum AIChatUnavailableReason: Equatable {
  case osTooOld
  case appleIntelligenceOff
  case deviceNotEligible
  case modelNotReady
  case languageNotSupported
}

enum AIChatBackend: Equatable {
  case foundationModels
  case unavailable(AIChatUnavailableReason)
}

enum AIChatAvailability {
  /// 지금 쓸 백엔드. MLX(Task 11)가 붙으면 iOS 18–25 분기가 여기에 추가된다.
  static func current() -> AIChatBackend {
    #if canImport(FoundationModels)
      if #available(iOS 26.0, *) {
        let model = SystemLanguageModel.default
        switch model.availability {
        case .available:
          return model.supportsLocale(Locale.current) ? .foundationModels : .unavailable(.languageNotSupported)
        case .unavailable(.appleIntelligenceNotEnabled):
          return .unavailable(.appleIntelligenceOff)
        case .unavailable(.deviceNotEligible):
          return .unavailable(.deviceNotEligible)
        case .unavailable:
          return .unavailable(.modelNotReady)
        }
      }
    #endif
    return .unavailable(.osTooOld)
  }
}
```

- [ ] **Step 4: 실기 평가 테스트** — `HubDevTests/FMQueryParserEvalTests.swift`. Task 0 의 평가셋을 돌려 필드별 정확도를 출력한다.
  평가셋 JSON 은 HubDevTests 타겟 리소스로 추가한다.

```swift
//
//  FMQueryParserEvalTests.swift
//  HubDevTests
//
//  실기 전용 — Apple Intelligence 가 켜진 iOS 26 기기에서만 돈다. 정확도를 출력하고 intent 는 전부 맞아야 한다.
//

import XCTest

@testable import Hub_Dev

private struct EvalCase: Decodable {
  let q: String
  let expect: HubQueryDTO
}

final class FMQueryParserEvalTests: XCTestCase {
  func testEvalSet() async throws {
    #if !canImport(FoundationModels)
      throw XCTSkip("FoundationModels SDK 없음")
    #else
    guard AIChatAvailability.current() == .foundationModels else {
      throw XCTSkip("Foundation Models 사용 불가")
    }
    guard #available(iOS 26.0, *) else { throw XCTSkip("iOS 26 미만") }
    let url = try XCTUnwrap(
      Bundle(for: Self.self).url(forResource: "ai_chat_eval_ko", withExtension: "json"))
    let cases = try JSONDecoder().decode([EvalCase].self, from: Data(contentsOf: url))
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = TimeZone(identifier: "Asia/Seoul")!
    let parser = FMQueryParser(calendar: calendar)
    let now = Date()
    var intentHits = 0
    var fullHits = 0
    for item in cases {
      let started = Date()
      let got = try await parser.parse(item.q, context: HubChatContext(), now: now)
      let want = HubQueryMapper.map(item.expect)
      if got.intent == want.intent { intentHits += 1 }
      if got == want { fullHits += 1 } else { print("[EVAL] MISS \(item.q)\n  got=\(got)\n  want=\(want)") }
      print("[EVAL] \(String(format: "%.2f", Date().timeIntervalSince(started)))s \(item.q)")
    }
    print("[EVAL] intent \(intentHits)/\(cases.count), full \(fullHits)/\(cases.count)")
    XCTAssertEqual(intentHits, cases.count)
    #endif
  }
}
```

  평가셋의 `expect` 는 `HubQueryDTO` 형태이며 `intent` 외 필드는 생략 가능하다(Task 1 DTO 의 옵셔널).

- [ ] **Step 5: 실기 실행 (사용자 실행)** — 기기 destination 으로 `-only-testing:HubDevTests/FMQueryParserEvalTests`.
  Expected: intent 20/20, full 17/20 이상. 미달이면 `HubQueryPrompt.instructions` 의 예시를 늘리고 다시 돌린다.

---

### Task 8: 화면 리듀서

**Files:**
- Create: `Hub/Presentation/AIChatScene/Reducer/AIChatReducer.swift`
- Test: `HubDevTests/AIChatReducerTests.swift`

**Interfaces:**
- Consumes: `HubChatAnswer`, `HubChatCard`, `HubChatContext`, `AIChatBackend`, 기존 `Reducer` 프로토콜(`Hub/Presentation/Common/Reducer/Reducer.swift`)
- Produces:
  - `enum AIChatRole: Equatable { case user, assistant }`
  - `enum AIChatContent: Equatable { case text(String); case pending; case answer(HubChatAnswer) }`
  - `struct AIChatMessage: Equatable, Identifiable { let id: Int; let role: AIChatRole; var content: AIChatContent }`
  - `struct AIChatReducer: Reducer` — `State`, `Action`, `Effect` 아래 코드 그대로

- [ ] **Step 1: 실패하는 테스트**

```swift
//
//  AIChatReducerTests.swift
//  HubDevTests
//
//  전송 → 대기 말풍선 → 답변 반영, 중복 전송 차단, stale 답변 무시, 카드 탭
//

import XCTest

@testable import Hub_Dev

final class AIChatReducerTests: XCTestCase {
  private typealias R = AIChatReducer

  private let reducer = R()
  private var state: R.State!

  override func setUp() {
    super.setUp()
    state = R.State(backend: .foundationModels)
  }

  private func send(_ action: R.Action) -> [R.Effect] {
    reducer.reduce(into: &state, action: action)
  }

  private let answer = HubChatAnswer(reply: .noGuide, cards: [], context: HubChatContext())

  func testSendAppendsUserAndPendingAndAsks() {
    _ = send(.draftChanged("  어제 영상  "))
    XCTAssertEqual(send(.sendTapped), [.ask(id: 1, text: "어제 영상", context: HubChatContext())])
    XCTAssertEqual(state.messages.map(\.content), [.text("어제 영상"), .pending])
    XCTAssertEqual(state.draft, "")
    XCTAssertEqual(state.pendingID, 1)
  }

  func testBlankDraftDoesNothing() {
    _ = send(.draftChanged("   "))
    XCTAssertEqual(send(.sendTapped), [])
    XCTAssertTrue(state.messages.isEmpty)
  }

  func testSecondSendWhilePendingIsIgnored() {
    _ = send(.suggestionTapped("a"))
    XCTAssertEqual(send(.suggestionTapped("b")), [])
    XCTAssertEqual(state.messages.count, 2)
  }

  func testAnswerReplacesPendingAndStoresContext() {
    _ = send(.suggestionTapped("a"))
    var context = HubChatContext()
    context.lastVideo = RecordingFile(
      fileName: "f", startedAt: Date(timeIntervalSince1970: 0), kind: .drive,
      location: .local(URL(fileURLWithPath: "/tmp/f")))
    let reply = HubChatAnswer(reply: .videos(count: 0), cards: [], context: context)
    XCTAssertEqual(send(.answered(id: 1, reply)), [])
    XCTAssertEqual(state.messages.last?.content, .answer(reply))
    XCTAssertEqual(state.context, context)
    XCTAssertNil(state.pendingID)
  }

  func testStaleAnswerIsIgnored() {
    _ = send(.suggestionTapped("a"))
    XCTAssertEqual(send(.answered(id: 99, answer)), [])
    XCTAssertEqual(state.messages.last?.content, .pending)
  }

  func testUnavailableBackendBlocksSend() {
    state = R.State(backend: .unavailable(.appleIntelligenceOff))
    XCTAssertEqual(send(.suggestionTapped("a")), [])
  }

  func testCardTapOpens() {
    let card = HubChatCard.setting(key: "parkmode", title: "주차")
    XCTAssertEqual(send(.cardTapped(card)), [.open(card)])
  }
}
```

- [ ] **Step 2: 실패 확인 (사용자 실행)** — `-only-testing:HubDevTests/AIChatReducerTests`
- [ ] **Step 3: 구현**

```swift
//
//  AIChatReducer.swift
//  Hub
//

import Foundation

enum AIChatRole: Equatable {
  case user
  case assistant
}

enum AIChatContent: Equatable {
  case text(String)
  case pending
  case answer(HubChatAnswer)
}

struct AIChatMessage: Equatable, Identifiable {
  let id: Int
  let role: AIChatRole
  var content: AIChatContent
}

struct AIChatReducer: Reducer {
  struct State: Equatable {
    let backend: AIChatBackend
    var messages: [AIChatMessage] = []
    var draft = ""
    /// 답을 기다리는 assistant 메시지 id. 있으면 새 전송을 막는다.
    var pendingID: Int?
    var nextID = 0
    var context = HubChatContext()
  }

  enum Action: Equatable {
    case draftChanged(String)
    case sendTapped
    case suggestionTapped(String)
    case answered(id: Int, HubChatAnswer)
    case cardTapped(HubChatCard)
  }

  enum Effect: Equatable {
    case ask(id: Int, text: String, context: HubChatContext)
    case open(HubChatCard)
  }

  func reduce(into state: inout State, action: Action) -> [Effect] {
    switch action {
    case .draftChanged(let text):
      state.draft = text
      return []
    case .sendTapped:
      return submit(state.draft, into: &state)
    case .suggestionTapped(let text):
      return submit(text, into: &state)
    case .answered(let id, let answer):
      guard state.pendingID == id,
        let index = state.messages.firstIndex(where: { $0.id == id })
      else { return [] }
      state.messages[index].content = .answer(answer)
      state.context = answer.context
      state.pendingID = nil
      return []
    case .cardTapped(let card):
      return [.open(card)]
    }
  }

  private func submit(_ raw: String, into state: inout State) -> [Effect] {
    let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !text.isEmpty, state.pendingID == nil, state.backend == .foundationModels else {
      return []
    }
    let replyID = state.nextID + 1
    state.messages.append(AIChatMessage(id: state.nextID, role: .user, content: .text(text)))
    state.messages.append(AIChatMessage(id: replyID, role: .assistant, content: .pending))
    state.nextID += 2
    state.pendingID = replyID
    state.draft = ""
    return [.ask(id: replyID, text: text, context: state.context)]
  }
}
```

  Task 11 에서 `AIChatBackend.mlx` 가 생기면 `state.backend == .foundationModels` 를 `state.backend.isReady`(enum 계산 프로퍼티)로 바꾼다.

- [ ] **Step 4: 통과 확인 (사용자 실행)** — Expected: 7 tests PASS

---

### Task 9: 실행기 · 코디네이터 · 화면 · 설정 포커스

**Files:**
- Create: `Hub/Presentation/AIChatScene/AIChatEffectRunner.swift`
- Create: `Hub/Presentation/AIChatScene/AIChatCoordinator.swift`
- Create: `Hub/Presentation/AIChatScene/View/AIChatView.swift`
- Create: `Hub/Presentation/AIChatScene/View/AIChatCardViews.swift`
- Modify: `Hub/Presentation/SettingScene/Coordinator/SettingCoordinator.swift:19-27`
- Modify: `Hub/Presentation/SettingScene/ViewModel/SettingWifiViewModel.swift:751-763`
- Modify: `Hub/Presentation/SettingScene/ViewController/SettingViewController.swift:448-452`
- Modify: `Hub/Localizable.swift`, `Hub/Resources/Localizable.xcstrings`
- Test: `HubDevTests/AIChatEffectRunnerTests.swift`

**Interfaces:**
- Consumes: Task 4·6·7·8 전부, 기존 `Store`(`Hub/Presentation/Common/Reducer/Store.swift`), `DefaultVodCoordinator.start(with: .showStreamVod(model:type:delegate:))` ·
  `.showLocalVod(...)`(`VodCoordinator.swift:20-21`), `VodStreamModel(storageType:selectedIndex:items:path:)`, `VodLocalModel(selectedIndex:items:)`,
  `FileListCellModel(type:fileName:path:filePath:channelbits:downloadUrl:)`, `DefaultSettingCoordinator`, NAS 씬 코디네이터(`DefaultNasStorageCoordinator`) 구조
- Produces: `final class AIChatEffectRunner`, `protocol AIChatCoordinator`, `final class DefaultAIChatCoordinator`, `SettingSteps.showSettingFocused(key: String)`

- [ ] **Step 1: 실행기 테스트(실패)** — 엔진은 fake 의존성으로 만든 실제 `HubChatEngine` 을 쓴다.

```swift
//
//  AIChatEffectRunnerTests.swift
//  HubDevTests
//

import XCTest

@testable import Hub_Dev

private struct UnknownParser: HubQueryParsing {
  func parse(_ text: String, context: HubChatContext, now: Date) async throws -> HubQuery {
    HubQuery(intent: .unknown)
  }
}

private struct NoAnswer: HubGuideAnswering {
  func answer(
    question: String, sections: [SettingsGuideSection], currentValues: [String: String],
    language: String
  ) async throws -> String { "" }
}

private struct NoFiles: RecordingFileSource {
  func files(kinds: Set<RecordingKind>) async throws -> [RecordingFile] { [] }
}

private struct NoHistory: DriveHistorySource {
  func drives(in interval: DateInterval) -> [HubDriveRecord] { [] }
  func route(of drive: HubDriveRecord) -> [HubCoordinate] { [] }
  func coordinate(near date: Date, macAddress: String) -> HubCoordinate? { nil }
}

private struct NoPlace: PlaceGeocoding {
  func place(named name: String) async -> HubPlace? { nil }
}

private struct NoSettings: DeviceSettingSource {
  func currentValues(keys: [String]) async -> [String: String] { [:] }
}

private struct Offline: DeviceConnectionChecking {
  var isDeviceConnected: Bool { false }
}

final class AIChatEffectRunnerTests: XCTestCase {
  private func makeEngine() -> HubChatEngine {
    HubChatEngine(
      HubChatEngine.Dependencies(
        parser: UnknownParser(), answerer: NoAnswer(), guide: SettingsGuide(sections: []),
        deviceFiles: NoFiles(), localFiles: NoFiles(), history: NoHistory(), geocoder: NoPlace(),
        settings: NoSettings(), connection: Offline(), now: Date.init, calendar: .current,
        language: "ko"))
  }

  func testAskSendsAnsweredOnMain() {
    let done = expectation(description: "answered")
    let runner = AIChatEffectRunner(engine: makeEngine(), open: { _ in })
    runner.run(.ask(id: 3, text: "q", context: HubChatContext())) { action in
      XCTAssertTrue(Thread.isMainThread)
      XCTAssertEqual(
        action,
        .answered(id: 3, HubChatAnswer(reply: .notUnderstood, cards: [], context: HubChatContext())))
      done.fulfill()
    }
    wait(for: [done], timeout: 2)
  }

  func testOpenForwardsCard() {
    var opened: [HubChatCard] = []
    let runner = AIChatEffectRunner(engine: makeEngine(), open: { opened.append($0) })
    let card = HubChatCard.setting(key: "parkmode", title: "t")
    runner.run(.open(card)) { _ in }
    XCTAssertEqual(opened, [card])
  }
}
```

- [ ] **Step 2: 실행기 구현**

```swift
//
//  AIChatEffectRunner.swift
//  Hub
//

import Foundation

/// Effect 를 실행하고 결과를 main 큐에서 action 으로 되돌린다. 화면이 사라지면 진행 중인 질문을 취소한다.
final class AIChatEffectRunner {
  private let engine: HubChatEngine
  private let open: (HubChatCard) -> Void
  private var tasks: [Int: Task<Void, Never>] = [:]

  init(engine: HubChatEngine, open: @escaping (HubChatCard) -> Void) {
    self.engine = engine
    self.open = open
  }

  deinit {
    tasks.values.forEach { $0.cancel() }
  }

  func run(_ effect: AIChatReducer.Effect, send: @escaping (AIChatReducer.Action) -> Void) {
    switch effect {
    case .ask(let id, let text, let context):
      let engine = engine
      tasks[id] = Task {
        let answer = await engine.respond(to: text, context: context)
        guard !Task.isCancelled else { return }
        await MainActor.run { send(.answered(id: id, answer)) }
      }
    case .open(let card):
      open(card)
    }
  }
}
```

- [ ] **Step 3: 실행기 테스트 통과 확인 (사용자 실행)** — `-only-testing:HubDevTests/AIChatEffectRunnerTests`, Expected: 2 PASS

- [ ] **Step 4: 설정 포커스 — `SettingSteps` 에 case 추가**

```swift
public enum SettingSteps: Step {
  case showSetting
  /// AI 채팅 바로가기 — 목록을 그린 뒤 해당 key 행으로 스크롤한다.
  case showSettingFocused(key: String)
  // 기존 case 유지
}
```

  `DefaultSettingCoordinator.start(with:)` 의 `.showSetting` 처리 코드를 같은 함수로 묶고, 포커스 key 를 `SettingViewController` 의
  새 프로퍼티 `pendingFocusKey: String?` 에 넣는다. `SettingWifiViewModel.selectMemoryAssignRow()`(`:751`)를 key 인자 버전으로 일반화한다.

```swift
  /// key 로 행을 찾는다. 시스템 성격 섹션이 여러 개라 sectionType 이 아니라 key 로 찾는다.
  func selectRow(key: String) -> (indexPath: IndexPath, model: SettingCellModel)? {
    guard let sections = try? listItem.value() else { return nil }
    for (section, sectionModel) in sections.enumerated() {
      guard let row = sectionModel.items.firstIndex(where: { $0.key == key }),
        let model = sectionModel.items[row] as? SettingCellModel
      else { continue }
      let indexPath = IndexPath(row: row, section: section)
      selectedIndexPath = indexPath
      return (indexPath, model)
    }
    return nil
  }

  func selectMemoryAssignRow() -> (indexPath: IndexPath, model: SettingCellModel)? {
    selectRow(key: "memoryassign")
  }
```

  (`try? listItem.value()` 는 기존 함수의 코드를 그대로 옮긴 것이다. 새 코드에서 늘리지 않는다.)
  `SettingViewController` 는 `listItem` 이 처음 비어 있지 않게 갱신되는 지점(목록 바인딩 subscribe)에서 `pendingFocusKey` 가 있으면
  `wifiViewModel?.selectRow(key:)` 로 찾아 `tableView.scrollToRow(at:at: .middle, animated: true)` 하고 `pendingFocusKey = nil`.
  접힌 섹션(`isFold`)이면 먼저 펼친다 — 펼치는 기존 코드 경로를 찾아 같은 것을 부른다. 시트는 열지 않는다.

- [ ] **Step 5: 코디네이터** — NAS 씬 코디네이터(`DefaultNasStorageCoordinator`)와 같은 모양으로 만든다.

```swift
//
//  AIChatCoordinator.swift
//  Hub
//

import SwiftUI
import UIKit
import VueroidKit

protocol AIChatCoordinator: AnyObject {
  func start()
}

final class DefaultAIChatCoordinator: AIChatCoordinator {
  private let navigationController: UINavigationController
  private var childCoordinators: [AnyObject] = []
  private var runner: AIChatEffectRunner?

  init(navigationController: UINavigationController) {
    self.navigationController = navigationController
  }

  deinit {
    aiLogger.info("deinit DefaultAIChatCoordinator")
  }

  func start() {
    let backend = AIChatAvailability.current()
    let runner = AIChatEffectRunner(engine: makeEngine(), open: { [weak self] in self?.open($0) })
    self.runner = runner
    let store = Store(
      initialState: AIChatReducer.State(backend: backend), reducer: AIChatReducer(),
      run: { effect, send in runner.run(effect, send: send) })
    let controller = UIHostingController(rootView: AIChatView(store: store))
    controller.title = L.ai_chat_title.localized
    navigationController.pushViewController(controller, animated: true)
  }
}
```

  `makeEngine()` 은 Task 4 구현들을 조립한다:
  - `parser`/`answerer`: `#if canImport(FoundationModels)` + `if #available(iOS 26.0, *)` 면 `FMQueryParser(calendar: .current)` ·
    `FMGuideAnswerer()`, 아니면 항상 throw 하는 `UnavailableParser`/`UnavailableAnswerer`(같은 파일 private struct). 화면은 backend 가
    `.unavailable` 이면 전송을 막으므로 실제로 불리지 않는다.
  - `guide`: `Bundle.main.url(forResource: "settings_guide", withExtension: "json")` → `SettingsGuide.load(from:)`. 실패하면
    `aiLogger.error` 후 `SettingsGuide(sections: [])`.
  - `deviceFiles`: `DeviceRecordingFileSource(fetchList:)` — `FileListWifiViewModel.swift:410` 부근과 같은 HTTP/WS 분기로 `GetFileListModel(type:thumb: 0, url: 1)` 요청.
  - `localFiles`: `LocalRecordingFileSource()`, `history`: `SqlDriveHistorySource()`, `geocoder`: `MapKitPlaceGeocoder()`
  - `settings`: `CachedDeviceSettingSource(connection: CurrentConnection(), fetchConfig: …, display: …)` — Task 4 Step 6
  - `connection`: `CurrentConnection()`, `now`: `Date.init`, `calendar`: `.current`, `language`: `Locale.current.language.languageCode?.identifier ?? "en"`

  `open(_ card:)`:

| 카드 | 동작 |
|---|---|
| `.video` + `.device` | `FileListCellModel(type: .wifi, fileName:, path: streamPath, channelbits:, downloadUrl:)` 1개로 `VodStreamModel(storageType: .WifiDashCam, selectedIndex: 0, items: [cell], path: streamPath)` → `DefaultVodCoordinator(navigationController:)` 를 `childCoordinators` 에 넣고 `.start(with: .showStreamVod(model:type: .vod, delegate: self))`. **`FileListViewModel.pushVod(model:)`(`FileListViewModel.swift:290`)가 해상도 선택을 먼저 띄우므로 같은 선행 단계를 따른다** — 그 함수를 읽고 필요한 호출을 그대로 한다. 비연결이면 열지 않고 토스트 `L.ai_chat_needs_connection` |
| `.video` + `.local(url)` | `FileListCellModel(type: .file, fileName: url.lastPathComponent, filePath: url)` → `VodLocalModel(selectedIndex: 0, items: [cell])` → `.showLocalVod(model:type: .vod, delegate: self)`. `NCUtil.videoFileSectionDict` 가 로컬 셀을 만드는 방식과 필드를 맞춘다 |
| `.drive(summary)` | `AIChatRouteMapView(summary:)` 를 `UIHostingController` 로 전체 화면 present(닫기 버튼) |
| `.setting(key, _)` | 연결 중이면 `DefaultSettingCoordinator(navigationController:)` → `.start(with: .showSettingFocused(key:))`, 아니면 토스트 `L.ai_chat_needs_connection` |

  VOD 코디네이터 delegate 의 종료 콜백에서 `childCoordinators` 에서 제거한다(누수 확인: deinit 로그).

- [ ] **Step 6: 화면** — `AIChatView.swift`

```swift
//
//  AIChatView.swift
//  Hub
//

import SwiftUI

struct AIChatView: View {
  @ObservedObject var store: Store<AIChatReducer>

  private let suggestions = [
    L.ai_chat_suggestion_video, L.ai_chat_suggestion_event, L.ai_chat_suggestion_parking,
  ]

  var body: some View {
    VStack(spacing: 0) {
      if case .unavailable(let reason) = store.state.backend {
        Text(reason.message).font(.footnote).padding().frame(maxWidth: .infinity)
          .background(Color(.secondarySystemBackground))
      }
      ScrollViewReader { proxy in
        ScrollView {
          LazyVStack(alignment: .leading, spacing: 12) {
            if store.state.messages.isEmpty {
              ForEach(suggestions, id: \.self) { key in
                Button(key.localized) { store.send(.suggestionTapped(key.localized)) }
                  .buttonStyle(.bordered)
              }
            }
            ForEach(store.state.messages) { message in
              AIChatMessageRow(message: message) { store.send(.cardTapped($0)) }
                .id(message.id)
            }
          }
          .padding(16)
        }
        .onChange(of: store.state.messages.count) { _, _ in
          if let last = store.state.messages.last { proxy.scrollTo(last.id, anchor: .bottom) }
        }
      }
      HStack {
        TextField(
          L.ai_chat_placeholder.localized,
          text: Binding(get: { store.state.draft }, set: { store.send(.draftChanged($0)) }),
          axis: .vertical
        )
        .textFieldStyle(.roundedBorder)
        .onSubmit { store.send(.sendTapped) }
        Button { store.send(.sendTapped) } label: { Image(systemName: "arrow.up.circle.fill") }
          .disabled(store.state.pendingID != nil)
          .accessibilityLabel(L.ai_chat_send.localized)
      }
      .padding(12)
    }
  }
}

extension AIChatUnavailableReason {
  var message: String {
    switch self {
    case .osTooOld: L.ai_chat_unavailable_os.localized
    case .appleIntelligenceOff: L.ai_chat_unavailable_ai_off.localized
    case .deviceNotEligible: L.ai_chat_unavailable_device.localized
    case .modelNotReady: L.ai_chat_unavailable_model.localized
    case .languageNotSupported: L.ai_chat_unavailable_language.localized
    }
  }
}
```

  `AIChatCardViews.swift` — 로직이 있는 부분(메시지 행·주행 카드)의 코드:

```swift
//
//  AIChatCardViews.swift
//  Hub
//

import MapKit
import SwiftUI

struct AIChatMessageRow: View {
  let message: AIChatMessage
  let onCard: (HubChatCard) -> Void

  var body: some View {
    switch (message.role, message.content) {
    case (.user, .text(let text)):
      Text(text).padding(10).background(Color.accentColor.opacity(0.15)).cornerRadius(12)
        .frame(maxWidth: .infinity, alignment: .trailing)
    case (_, .pending):
      ProgressView().frame(maxWidth: .infinity, alignment: .leading)
    case (_, .answer(let answer)):
      VStack(alignment: .leading, spacing: 8) {
        Text(answer.reply.text)
        ForEach(Array(answer.cards.enumerated()), id: \.offset) { _, card in
          Button { onCard(card) } label: { AIChatCardView(card: card) }.buttonStyle(.plain)
        }
      }
    case (.assistant, .text(let text)):
      Text(text)
    }
  }
}

struct AIChatCardView: View {
  let card: HubChatCard

  var body: some View {
    switch card {
    case .video(let file): AIChatVideoCard(file: file)
    case .drive(let summary): AIChatDriveCard(summary: summary)
    case .setting(_, let title): AIChatSettingCard(title: title)
    }
  }
}

struct AIChatDriveCard: View {
  let summary: HubDriveSummary

  private var route: [CLLocationCoordinate2D] {
    summary.route.map { CLLocationCoordinate2D(latitude: $0.latitude, longitude: $0.longitude) }
  }

  var body: some View {
    VStack(alignment: .leading, spacing: 6) {
      Map(interactionModes: []) {
        MapPolyline(coordinates: route).stroke(.blue, lineWidth: 4)
        ForEach(Array(summary.events.enumerated()), id: \.offset) { _, event in
          if let point = event.coordinate {
            Marker("", coordinate: CLLocationCoordinate2D(latitude: point.latitude, longitude: point.longitude))
              .tint(.red)
          }
        }
      }
      .frame(height: 180)
      .cornerRadius(12)
      Text(
        "\(summary.drive.start.formatted(date: .abbreviated, time: .shortened)) – "
          + "\(summary.drive.end.formatted(date: .omitted, time: .shortened)) · "
          + String(format: "%.1f km", Double(summary.drive.distance) / 1000)
      )
      .font(.footnote)
    }
  }
}

extension HubChatReply {
  var text: String {
    switch self {
    case .videos(let count):
      count == 1 ? L.ai_chat_reply_video_one.localized
        : String(format: L.ai_chat_reply_video_many.localized, count)
    case .noVideo(.notFound): L.ai_chat_reply_video_none.localized
    case .noVideo(.needsConnection), .noDrive(.needsConnection): L.ai_chat_reply_needs_connection.localized
    case .drive(.matched): L.ai_chat_reply_drive.localized
    case .drive(.timeOnly): L.ai_chat_reply_drive_time_only.localized
    case .noDrive(.notFound): L.ai_chat_reply_drive_none.localized
    case .guide(let text): text
    case .noGuide: L.ai_chat_reply_guide_none.localized
    case .notUnderstood: L.ai_chat_reply_not_understood.localized
    }
  }
}
```

  `HISTORY.DISTANCE` 단위(m 인지)는 `TravelLog` 화면의 거리 표기 코드로 확인하고 위 `/ 1000` 을 맞춘다. 나머지 View(값만 받아 그린다):
  - `AIChatVideoCard(file:)` — 썸네일은 `ThumbnailDatabaseManager.fetchThumbnail(fileName:)`(`ThumbnailDatabaseManager.swift:83`, throw 는 로그 후 placeholder),
    시작 시각 `yyyy.MM.dd HH:mm:ss`, 종류 배지(상시·이벤트·수동), 재생 아이콘.
  - `AIChatRouteMapView(summary:)` — 같은 지도를 전체 화면·상호작용 켬, 이벤트 마커 탭 시 해당 영상 카드 탭과 같은 `open(.video)` 를 부르도록
    코디네이터가 넘긴 클로저 호출.
  - `AIChatSettingCard(title:)` — 제목 + "설정에서 보기" chevron.
  `HubChatReply.text` 가 쓰는 문구(ko):

| reply | 키 | ko |
|---|---|---|
| `.videos(1)` | `ai_chat_reply_video_one` | 요청한 시각의 영상이에요. |
| `.videos(n)` | `ai_chat_reply_video_many` | 조건에 맞는 영상 %d개를 찾았어요. |
| `.noVideo(.notFound)` | `ai_chat_reply_video_none` | 그 시간대의 영상을 찾지 못했어요. 덮어쓰기로 지워졌을 수 있어요. |
| `.noVideo(.needsConnection)` | `ai_chat_reply_needs_connection` | 블랙박스에 연결하면 SD 카드 영상도 찾아볼게요. |
| `.drive(.matched)` | `ai_chat_reply_drive` | 해당 주행의 경로예요. 빨간 점이 이벤트가 녹화된 위치예요. |
| `.drive(.timeOnly)` | `ai_chat_reply_drive_time_only` | 장소를 찾지 못해 시간대로만 찾은 주행이에요. |
| `.noDrive(.notFound)` | `ai_chat_reply_drive_none` | 조건에 맞는 주행 기록이 없어요. |
| `.noDrive(.needsConnection)` | `ai_chat_reply_needs_connection` | (위와 같음) |
| `.guide(text)` | — | LLM 문장 그대로 |
| `.noGuide` | `ai_chat_reply_guide_none` | 그 질문에 맞는 설정 안내가 아직 없어요. |
| `.notUnderstood` | `ai_chat_reply_not_understood` | 질문을 이해하지 못했어요. 날짜·시간·장소를 넣어 다시 물어봐 주세요. |

- [ ] **Step 7: 문구 키 추가** — `Localizable.swift` 의 "원격 시트 등록 전 로컬 키" MARK 아래, 위 표의 키와 다음 키를 ko·en 으로:
  `ai_chat_title`(AI 도우미 / AI Assistant), `ai_chat_placeholder`(무엇이든 물어보세요 / Ask anything), `ai_chat_send`(보내기 / Send),
  `ai_chat_needs_connection`(블랙박스에 연결해 주세요 / Connect to your dashcam),
  `ai_chat_suggestion_video`(어제 아침 9시 30분 영상 보여줘 / Show yesterday's 9:30 AM video),
  `ai_chat_suggestion_event`(최근 퇴근길 이벤트 경로 보여줘 / Show my recent evening commute events),
  `ai_chat_suggestion_parking`(주차 녹화를 줄이려면? / How do I reduce parking recordings?),
  `ai_chat_unavailable_os`(iOS 26 이상에서 사용할 수 있어요 / Requires iOS 26 or later),
  `ai_chat_unavailable_ai_off`(설정에서 Apple Intelligence 를 켜 주세요 / Turn on Apple Intelligence in Settings),
  `ai_chat_unavailable_device`(이 기기에서는 지원하지 않아요 / Not supported on this device),
  `ai_chat_unavailable_model`(모델을 준비하는 중이에요. 잠시 후 다시 열어 주세요 / The model is getting ready. Try again shortly),
  `ai_chat_unavailable_language`(현재 언어는 아직 지원하지 않아요 / Your language isn't supported yet).
  `Localizable.xcstrings` 에 같은 키를 `"extractionState": "manual"` 로 추가한다.

- [ ] **Step 8: 빌드 (사용자 실행)** — `xcodebuild -project Hub.xcodeproj -scheme Hub -configuration Debug build`

---

### Task 10: 진입점 · 기능 플래그 · 실기 매트릭스

**Files:**
- Modify: `Hub/Application/FeatureFlag/` 의 `HubAppConfig` · `ConfigOption.swift:119`(`FeatureFlagOption`) · `AppConfigController.swift:203`
- Modify: `Hub/Presentation/MoreScene/MoreViewController.swift`(`syncNasStorageRow()` `:110` 옆)
- Modify: `Hub/Presentation/MoreScene/DefaultMoreCoordinator.swift:146` 부근(`MoreSteps`)

- [ ] **Step 1: 플래그** — NAS 의 `nasStorage` 를 그대로 따라 `aiChat` 필드·`FeatureFlagOption.aiChat` case·디버그 메뉴 토글을 추가한다(기본 off).
- [ ] **Step 2: More 행** — `syncAIChatRow()` 를 `syncNasStorageRow()` 와 같은 방식으로 만들어 플래그가 켜지면 행 추가, 꺼지면 제거.
  행 제목 `L.ai_chat_title`. More 행은 현지화 제목 문자열로 분기하므로(`MoreViewController.swift:163` 부근) 같은 switch 에 케이스를 추가한다.
- [ ] **Step 3: 이동** — `MoreSteps.pushAIChatScene` → `DefaultAIChatCoordinator(navigationController:)` 를 child 로 보관하고 `start()`.
  pop 시 child 제거(NAS 의 `onPop` 처리와 같은 방식).
- [ ] **Step 4: 실기 매트릭스 (사용자 실행)** — 결과를 이 문서 아래에 기록한다.

| # | 조건 | 질문 | 기대 |
|---|---|---|---|
| 1 | S1-4K 연결, 어제 09:30 주행 영상 있음 | 어제 아침 출근길중 9시 30분경 비디오를 보여줘 | 영상 카드 1개 → 탭 시 VOD 재생 |
| 2 | 연결, 최근 30일 내 판교→인천 저녁 주행 + 이벤트 | 판교에서 인천가는 퇴근길에 사고날뻔한 적이 있었어 그때 경로와 위치를 보여줘 | 지도 카드, 이벤트 빨간 점 |
| 3 | 2 직후 | 위 경우의 비디오를 보여줘 | 2의 이벤트 영상 카드 |
| 4 | 연결 | 설정에서 뭘 바꿔야 주차녹화가 줄어들지 | 안내 문장 + 현재 값 언급 + 설정 바로가기 → 해당 행 스크롤 |
| 5 | 비연결, DOWNLOADED 에 해당 영상 있음 | 1과 같은 질문 | 로컬 영상 카드 → 로컬 재생 |
| 6 | 비연결, 내려받은 영상 없음 | 1과 같은 질문 | "블랙박스에 연결하면…" |
| 7 | 블랙박스 AP(셀룰러 끔) | 2와 같은 질문 | 지명 검색 실패 → "시간대로만 찾은 주행" |
| 8 | Apple Intelligence 끔 | — | 상단 안내, 전송 막힘 |
| 9 | D22-4K 연결 | 4 | 설정 행 key 가 D22 에도 있는지(없으면 스크롤 없이 설정 화면만) |
| 10 | 질문 중 뒤로가기 | 아무 질문 | 크래시 없음, `deinit DefaultAIChatCoordinator` 로그 |

  확인 로그: `[AICHAT][PARSE] intent=… ref=…`, `[AICHAT][QUERY] device files N kinds=K`, 지명 실패 시 `[AICHAT][QUERY] geocode failed`.
  주행 중 Wi-Fi 경로 변화가 연결 해제로 읽히지 않는지 relaylog MCP 로 앱 로그를 확인한다(`MKLocalSearch` 셀룰러 트래픽 —
  AI 서비스와 같은 `markTransferActivity()` 가 필요한지 판단).

---

### Task 11: MLX 백엔드 (iOS 18–25, 2차)

1차(FM) 출시 후 진행한다. FlowDown 분석에서 확인한 문제를 처음부터 피한다.

**Files:**
- Modify: `Hub.xcodeproj` — SPM `https://github.com/ml-explore/mlx-swift-lm` 를 **태그로 고정**(branch 금지), products `MLXLLM`, `MLXLMCommon`
- Modify: `Hub/Resources/Hub.entitlements`(실제 entitlements 파일) — `com.apple.developer.kernel.increased-memory-limit`
- Create: `Hub/Data/AIChat/MLX/MLXModelStore.swift` — 모델 다운로드·위치·삭제
- Create: `Hub/Data/AIChat/MLX/MLXQueryParser.swift` — `HubQueryParsing`, `HubGuideAnswering` 둘 다 구현하는 actor
- Create: `Hub/Data/AIChat/MLX/JSONObjectExtractor.swift` + `HubDevTests/JSONObjectExtractorTests.swift`
- Modify: `AIChatAvailability.swift` — `AIChatBackend.mlx`, `AIChatUnavailableReason.modelNotDownloaded`
- Modify: `AIChatReducer.swift` — `state.backend.isReady`

- [ ] **Step 1: 모델 선정 spike** — 후보 `mlx-community/Qwen3-1.7B-4bit`, `mlx-community/gemma-3-1b-it-4bit`. Task 7 의 평가셋을 MLX 파서로 돌려
  intent 20/20·full 17/20·질문당 3 s 이하(iPhone 15 기준)·피크 메모리를 기록하고 하나를 고른다.
- [ ] **Step 2: `JSONObjectExtractor`(TDD)** — 출력에서 첫 번째 균형 잡힌 `{…}` 를 꺼낸다(코드펜스·앞뒤 설명문 제거). 테스트: 펜스 포함, 앞 설명문,
  중첩 객체, 문자열 안의 `}`, 객체 없음(nil).
- [ ] **Step 3: `MLXModelStore`** — `Application Support/AIChat/Models/<repo>` 에 저장, `isExcludedFromBackup = true`.
  다운로드는 사용자가 채팅 화면의 "모델 받기(약 1GB)" 버튼을 눌렀을 때만, 블랙박스 AP 연결 중이면 막는다(인터넷 없음).
  기존 `DownloadSupport.swift` 의 진행률 리포터를 쓴다. 파일 목록은 HF `api/models/{repo}/tree/main` 으로 받고 크기를 검증한다.
- [ ] **Step 4: `MLXQueryParser`(actor)** — 원칙:
  - 모델 컨테이너는 actor 안에 하나만 보관하고 질문마다 재사용한다. 동시 질문은 리듀서가 이미 막는다 — `DispatchSemaphore` 를 쓰지 않는다.
  - 파싱: `HubQueryPrompt.instructions` + "JSON 한 개만 출력, 키는 HubQueryDTO 와 같음" + `userPrompt` → 온도 0, `maxTokens` 200 →
    `JSONObjectExtractor` → `JSONDecoder().decode(HubQueryDTO.self, …)` → `HubQueryMapper.map`. 실패 시 1회 재시도 후 throw.
  - 가이드 답변: FM 과 같은 지시문, `maxTokens` 200.
  - 스트리밍 decode 가 필요 없으므로 전체 생성 후 한 번만 decode 한다(FlowDown 의 매 토큰 전체 재 decode 문제 회피).
  - `MLX.Memory.cacheLimit` 를 64MB 로 두고, `UIApplication.didReceiveMemoryWarningNotification` · 백그라운드 진입 시 컨테이너를 해제하고
    `MLX.Memory.clearCache()`. (FlowDown·PhoneClaw 둘 다 메모리 경고 대응이 없었다.)
  - mlx-swift-lm 의 로딩·생성 API 이름은 고정한 태그의 README 와 `Libraries/MLXLMCommon/Evaluate.swift` 로 확인한다(버전마다 바뀐다).
- [ ] **Step 5: 가용성** — iOS 26+ 이고 FM 사용 가능 → `.foundationModels`, 아니면 모델이 받아져 있으면 `.mlx`, 없으면 `.unavailable(.modelNotDownloaded)`
  (채팅 화면이 다운로드 버튼을 보인다). 코디네이터 `makeEngine()` 의 parser/answerer 분기를 같은 값으로 고른다.
- [ ] **Step 6: 실기** — Task 10 매트릭스를 iOS 18 기기에서 반복하고, 질문 10회 연속 후 메모리 피크·jetsam 여부를 Instruments 로 기록한다.

---

## 범위 밖 (이번 계획에 넣지 않는다)

- 채팅에서 설정값을 직접 바꾸기(사용자 결정: 바로가기만).
- 대화 기록 저장·iCloud 동기화. 화면을 닫으면 대화는 사라진다.
- 클라우드 LLM, ADAS 경고 이력, GPS 기반 급감속 추정.
- 음성 입력(기존 `VoiceDonationScene`·SpeechAnalyzer 와의 연결은 별도 기획).
- 홈 화면 진입점·위젯.

## 검증 요약

| 층 | 방법 |
|---|---|
| 도메인(Task 1–3, 5, 6, 8) | `HubDevTests` 동기·async 단위 테스트, fake 의존성. 예시 질문 4개를 엔진 테스트로 재현 |
| LLM 품질(Task 0, 7, 11) | 평가셋 20문항 실기 테스트, intent 100%·전체 85% 이상, 지연 기록 |
| Data(Task 4) | 컴파일 + 실기 매트릭스. 파일명 형식은 fakeApiServer 응답으로 대조 |
| 화면·이동(Task 9, 10) | 실기 매트릭스 10항목, coordinator deinit 로그, relaylog 로 연결 해제 오탐 확인 |

## 구현 메모 (2026-11-06, feature/ai_chat · 미빌드)

Task 1–10 코드·테스트 작성 완료. Task 0(실기 게이트)·Task 11(MLX)은 미착수. 계획과 달라진 점:

| 항목 | 계획 | 구현 | 근거 |
|---|---|---|---|
| `RecordingKind.fileListType` | PVT=4 | PRK·PVT=2, USR=3 | HTTP v2.26 getfilelist type 4 는 마이폴더. fakeApiServer 는 type 2 에 PVT |
| 녹화 방식 `settingKey` | `timelapse` | `sleepmode` | `ConfigurationDTO.toDashcamDomain` 행 key (subKey 가 timelapse) |
| 녹화 정지 | — | 채팅 진입만으로는 recstop 하지 않고, 단말 getfilelist 직전에만 recstop(응답 대기 상한 2 s). 목록 조회나 단말 VOD 가 있었으면 채팅 pop 시 recstart | 사용자 결정(11-06): recstop 은 그것이 필요한 API(getfilelist §8, VOD `startrecordvod` 거부 시 재시도)와 함께 보낸다 |
| HTTP/WS 분기 | 클로저로 주입 | `Composers.fileCommandUseCase` 그대로 | `HttpCommandRepository` 가 프로브 결과로 이미 분기 |
| 현재 설정값 표기 | `ConfigValues` 로 변환 | `toDashcamDomain()` 행의 `value` | 설정 화면과 같은 문자열 |
| `HubDriveRecord.distance` | m | `distanceMiles` (mile) | History 화면이 `NCUtil.mileToKilo` 로 변환 |
| `aiLogger` | 새로 추가 | 기존 것 재사용(category `ai`) | `HubLogger.swift:30` |
| 코디네이터 | `protocol AIChatCoordinator` | `NavigationCoordinator` + finish delegate | 구현 하나뿐인 protocol 금지, VoiceDonation 과 같은 모양 |
| FM `@Guide(.range)` | 옵셔널 Int 에 부착 | 빼고 description 만 | 컴파일 불확실 — 범위는 `HubQueryMapper` 가 거름 |
| 영상 카드 썸네일 | `ThumbnailDatabaseManager` | 아이콘 | 단말·로컬 썸네일 출처 분리, 후속 |
| VOD 해상도 선행 단계 | `resolutionSelection` 따름 | 생략 | getInformation 응답을 쓰지 않고 저장값을 그대로 씀 |

### 프로토콜 문서 RAG (2026-11-06 사용자 결정: 설정 질문 범위 확장 · 검색 후 주입)

- `VueroidKit/Docs/HTTP_Protocol_v2.26.md` 를 `Hub/Resources/AIChat/dashcam_protocol.md` 로 번들에 복사.
  원본과 다르면 `ProtocolDocIndexTests.testBundledCopyMatchesVueroidKitDoc` 가 실패한다(원본 버전이 올라가도 실패).
- `ProtocolDocIndex`(Domain): 표 필드 행(같은 key 는 Get/Set 등 여러 절을 한 조각으로 합침) + 본문 문단,
  변경 이력·목차·코드 블록·응답 코드 행 제외 → 459 조각, 색인 20 ms(macOS 측정).
  검색은 어절 안 bigram + IDF / √(길이+10). 공백을 지우고 bigram 을 만들면 "후방 전용"→"방전" 오탐.
- 엔진: 가이드 JSON(질문+주제어) + 문서 조각 4개(파서 주제어로 검색, "~려면" 같은 어미가 엉뚱한 행을 끌어옴).
  카드는 가이드 행 + 이 단말 설정 화면에 실제로 있는 문서 키(제목은 설정 행 제목), 최대 3개.
  답변기가 실패하면 가이드 본문, 가이드가 없으면 `.noGuide`(문서 원문은 개발용 표기라 보여 주지 않음).
- 영어 번역 `dashcam_protocol_en.md`(전체 3,182줄, 원문과 줄 1:1·코드 블록 원문 그대로·필드 key 동일, 사용자 표현 동의어를
  괄호로 병기). `ProtocolDocLibrary` 가 질문에 한글이 있으면 한국어, 없으면 영어 색인을 쓴다(폰 언어가 아니라 질문 언어).
  `testEnglishDocHasSameFieldKeysAndNoHangul` 이 번역본 key 목록·한글 잔류를 확인한다 — 원문이 바뀌면 번역도 다시 해야 한다.
  영어 질문 예: battery drain→voltagelimit, impact sensitivity→infeventsense/parksensorsen, Wi-Fi band→wifibandwidth.
- 한계: 한국어·영어 외 언어(앱 지원 14개 중 12개) 질문은 문서가 걸리지 않는다. "와이파이"↔"Wi-Fi" 같은 표기 차이는 못 잇는다.
- 번역 확인 필요: "두코"→Duco, "폰터스"→Pontus, "OBD 추정"→OBD estimation 등 고유명은 추정 번역.
- 주의: 내부 프로토콜 문서가 앱 번들(IPA)에 그대로 들어간다.
