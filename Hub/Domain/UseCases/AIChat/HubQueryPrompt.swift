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

  /// MLX 출력을 강제하는 `HubQueryDTO` JSON Schema. 선택지는 Swift enum 에서 만들어 어긋나지 않게 한다.
  /// 모든 키를 필수로 두고 말하지 않은 값은 null — 작은 모델이 키를 빼먹지 않게 한다. 범위 검증은 `HubQueryMapper`.
  /// XGrammar 는 properties 순서대로 생성하므로 직렬화기(키 정렬)를 쓰지 않고 순서대로 쓴다.
  static let jsonSchema: String = {
    let properties = schemaFields.map { "\"\($0.key)\":\($0.type.schema)" }
    let required = schemaFields.map { "\"\($0.key)\"" }
    return #"{"type":"object","properties":{"# + properties.joined(separator: ",")
      + #"},"required":["# + required.joined(separator: ",") + #"],"additionalProperties":false}"#
  }()

  /// 생성 순서. intent 를 먼저 정해야 나머지 칸이 그 의도에 맞게 채워진다.
  static let schemaFields: [(key: String, type: SchemaType)] = [
    ("intent", .choice(HubQueryIntent.allCases.map(\.rawValue))),
    ("daysAgo", .nullableInteger),
    ("month", .nullableInteger),
    ("dayOfMonth", .nullableInteger),
    ("hour", .nullableInteger),
    ("minute", .nullableInteger),
    ("period", .choice(HubDayPeriod.allCases.map(\.rawValue))),
    ("origin", .nullableString),
    ("destination", .nullableString),
    ("event", .choice(HubEventFilter.allCases.map(\.rawValue))),
    ("reference", .choice(HubQueryReference.allCases.map(\.rawValue))),
    ("topic", .nullableString),
  ]

  enum SchemaType {
    case choice([String])
    case nullableInteger
    case nullableString

    var schema: String {
      switch self {
      case .choice(let values):
        #"{"type":"string","enum":["# + values.map { "\"\($0)\"" }.joined(separator: ",") + "]}"
      case .nullableInteger: #"{"type":["integer","null"]}"#
      case .nullableString: #"{"type":["string","null"]}"#
      }
    }
  }

  /// MLX 는 지시문 뒤에 출력 형식을 붙인다(FM 은 `@Generable` 이 대신한다).
  static let jsonInstructions =
    instructions + "\nAnswer with one JSON object with exactly these keys: "
    + schemaFields.map(\.key).joined(separator: ", ")
    + ". Use null for anything the user did not say."

  /// 질문 파싱 전용 어댑터의 지시문. 학습 데이터의 system 과 글자 단위로 같아야 한다
  /// (`Scripts/ai_chat_train/generate_dataset.py` 의 `SYSTEM_PROMPT`).
  static let dedicatedInstructions =
    "Convert a question about a dashcam app into search fields. Do not answer the question. "
    + "Answer with one JSON object with exactly these keys: "
    + schemaFields.map(\.key).joined(separator: ", ")
    + ". Use null for anything the user did not say."

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
      lines.append(
        "previous result: video \(format(video.startedAt, "yyyy-MM-dd HH:mm", calendar))")
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
