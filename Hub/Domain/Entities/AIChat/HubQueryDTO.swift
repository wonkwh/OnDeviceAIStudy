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
