// 13단계 — Foundation Models: iOS·macOS 에 들어 있는 모델에게 정해진 칸을 채우게 한다.
// macOS 26 이상 + Apple Intelligence 가 켜진 Mac 에서 돈다. 앱의 FMQueryParser 를 두 칸으로 줄인 것이다.

import Foundation
import FoundationModels

@Generable
struct TinyQuery {
  @Guide(
    description: "video, drive, settingsHelp, unknown 중 하나",
    .anyOf(["video", "drive", "settingsHelp", "unknown"]))
  var intent: String
  @Guide(description: "며칠 전인지. 오늘 0, 어제 1. 날짜를 말하지 않았으면 비운다")
  var daysAgo: Int?
}

@main
enum Study {
  static func main() async throws {
    let model = SystemLanguageModel.default
    print("availability: \(model.availability)")
    print("현재 언어 지원: \(model.supportsLocale(Locale.current))")
    guard case .available = model.availability else {
      print("이 Mac 에서는 시스템 모델을 쓸 수 없다 — 앱이라면 안내 문구를 띄우는 경우다")
      return
    }
    let instructions =
      "You convert a question about a dashcam app into search fields. Do not answer the question."
      + " intent: video (show a recording), drive (show a drive route), settingsHelp (how to"
      + " change settings), unknown (anything else). daysAgo: 0 today, 1 yesterday."
    for question in ["어제 아침 9시 30분 영상 보여줘", "주차 녹화를 줄이려면?", "노래 틀어줘"] {
      // 질문마다 새 세션 — 앱과 같다
      let session = LanguageModelSession(instructions: instructions)
      let response = try await session.respond(
        to: "today: 2026-11-16 (Mon) 14:00\nquestion: \(question)",
        generating: TinyQuery.self, options: GenerationOptions(temperature: 0))
      let query = response.content
      print("\(question) -> intent=\(query.intent) daysAgo=\(String(describing: query.daysAgo))")
    }
  }
}
