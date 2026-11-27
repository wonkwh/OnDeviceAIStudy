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
