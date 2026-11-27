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
