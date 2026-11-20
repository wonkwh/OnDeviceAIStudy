// 12단계 — 앱의 실제 문서 검색(ProtocolDocIndex)을 Mac 에서 그대로 돌린다.
// 실행 인자: 저장소 루트 경로(생략하면 현재 폴더).

import Foundation

@main
enum Study {
  static func main() throws {
    let root = URL(fileURLWithPath: CommandLine.arguments.dropFirst().first ?? ".")
    let resources = root.appendingPathComponent("Hub/Resources/AIChat")
    let library = ProtocolDocLibrary(
      korean: ProtocolDocIndex(
        markdown: try String(
          contentsOf: resources.appendingPathComponent("dashcam_protocol.md"), encoding: .utf8)),
      english: ProtocolDocIndex(
        markdown: try String(
          contentsOf: resources.appendingPathComponent("dashcam_protocol_en.md"), encoding: .utf8)))
    print("조각 수: 한국어 \(library.korean.chunks.count) · 영어 \(library.english.chunks.count)")
    print("\"후방 전용\" 의 bigram: \(ProtocolDocIndex.bigrams("후방 전용").sorted())\n")

    for (question, topic) in [
      ("설정에서 뭘 바꿔야 주차녹화가 줄어들지", "주차 녹화"),
      ("How do I lower the impact sensitivity while parked?", "impact sensitivity"),
    ] {
      // 질문에 한글이 있으면 한국어 원문, 없으면 영어 번역에서 찾는다
      let index = library.index(for: question)
      print("■ \(question)  (검색어: \(topic))")
      for chunk in index.search(topic, limit: 4) {
        print("  [\(chunk.key ?? "문단")] \(chunk.text.prefix(90))")
      }
      print("")
    }
  }
}
