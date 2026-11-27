//
//  HubGuidePrompt.swift
//  Hub
//

import Foundation

/// 설정 안내 답변 지시문·프롬프트. FM·MLX 공용.
enum HubGuidePrompt {
  static let instructions = """
    You are the settings helper of a dashcam app. Answer only from the guide, the protocol \
    reference and the current values given.
    Reply in the user's language in at most 3 short sentences. Prefer the guide when it covers \
    the question.
    The protocol reference is a developer document: use it only for facts, explain values in \
    plain words, and never mention field names (like parksensorsen), API names or value codes.
    Refer to a setting by its screen title when one is given. Never say you will change a \
    setting; tell the user which setting to change.
    """
  /// 조각 하나가 프롬프트를 독차지하지 않게 자른다(값 목록이 긴 행이 있다).
  static let maxReferenceLength = 240
  static let maxResponseTokens = 200

  static func prompt(
    question: String, sections: [SettingsGuideSection], references: [ProtocolDocChunk],
    currentValues: [String: HubSettingValue], language: String
  ) -> String {
    var lines = ["guide:"]
    for section in sections {
      var line = "- \(section.title(language: language)): \(section.body(language: language))"
      if let key = section.configKey, let value = currentValues[key] {
        line += " (current: \(value.value))"
      }
      lines.append(line)
    }
    lines.append("protocol reference:")
    for reference in references {
      var line = "- \(reference.text.prefix(maxReferenceLength))"
      if let key = reference.key, let value = currentValues[key] {
        line += " (screen title: \(value.title), current: \(value.value))"
      }
      lines.append(line)
    }
    return lines.joined(separator: "\n") + "\n\nquestion: \(question)"
  }
}
