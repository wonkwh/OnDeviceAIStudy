// 11단계 — 앱의 실제 규칙 코드를 Mac 에서 그대로 돌린다.
// 모델이 쓴 JSON 이 HubQueryMapper 에서 걸러지고 HubQueryResolver 에서 시간 범위가 되는 과정을 본다.

import Foundation

@main
enum Study {
  static let outputs: [(note: String, json: String)] = [
    (
      "어제 9시 30분 영상",
      #"{"intent":"video","daysAgo":1,"month":null,"dayOfMonth":null,"hour":9,"minute":30,"period":"any","origin":null,"destination":null,"event":"any","reference":"none","topic":null}"#
    ),
    (
      "퇴근길 6시 — 오후 시간대라 18시로 올린다",
      #"{"intent":"video","daysAgo":0,"month":null,"dayOfMonth":null,"hour":6,"minute":null,"period":"eveningCommute","origin":null,"destination":null,"event":"any","reference":"none","topic":null}"#
    ),
    (
      "범위 밖 값(hour 25, 모르는 intent·period)은 버린다",
      #"{"intent":"movie","daysAgo":-3,"month":null,"dayOfMonth":null,"hour":25,"minute":70,"period":"dawn","origin":"  ","destination":null,"event":"any","reference":"none","topic":null}"#
    ),
    (
      "날짜도 시각도 없는 주행 질문 — 최근 30일, 퇴근 시간대",
      #"{"intent":"drive","daysAgo":null,"month":null,"dayOfMonth":null,"hour":null,"minute":null,"period":"eveningCommute","origin":"판교","destination":"인천","event":"impact","reference":"none","topic":null}"#
    ),
  ]

  static func main() throws {
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = TimeZone(identifier: "Asia/Seoul") ?? .current
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = calendar.timeZone
    formatter.dateFormat = "MM-dd HH:mm"
    guard
      let now = calendar.date(
        from: DateComponents(year: 2026, month: 11, day: 16, hour: 14, minute: 0))
    else { return }
    print("지금: \(formatter.string(from: now))\n")

    for output in outputs {
      let dto = try JSONDecoder().decode(HubQueryDTO.self, from: Data(output.json.utf8))
      let query = HubQueryMapper.map(dto)
      let window = HubQueryResolver.window(for: query, now: now, calendar: calendar)
      print("■ \(output.note)")
      print("  intent=\(query.intent) day=\(query.day) clock=\(String(describing: query.clock))")
      print("  period=\(query.period) origin=\(query.origin ?? "nil") event=\(query.event)")
      print(
        "  찾을 범위: \(formatter.string(from: window.interval.start)) ~ "
          + "\(formatter.string(from: window.interval.end))"
          + " 시간대=\(String(describing: window.hours))"
          + " 기준시각=\(window.anchor.map(formatter.string(from:)) ?? "없음")\n")
    }
  }
}
