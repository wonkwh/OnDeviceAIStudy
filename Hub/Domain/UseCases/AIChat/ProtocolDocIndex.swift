//
//  ProtocolDocIndex.swift
//  Hub
//

import Foundation

/// 프로토콜 문서 한 조각 — 표의 필드 행(같은 key 는 여러 절을 합친다) 또는 본문 문단.
struct ProtocolDocChunk: Equatable {
  let section: String
  let key: String?
  let text: String
}

/// HTTP 프로토콜 문서를 조각으로 나눠 어절 bigram + IDF 로 찾는다.
/// 기기 내 모델 컨텍스트(4,096 토큰)에 문서 전체(약 6만 토큰)가 들어가지 않아 질문마다 몇 조각만 넣는다.
struct ProtocolDocIndex {
  let chunks: [ProtocolDocChunk]
  private let grams: [Set<String>]
  private let idf: [String: Double]

  /// 검색 대상에서 빼는 절 — 버전 이력·목차는 질문과 무관한 단어로 순위를 흐린다.
  private static let skippedSections: Set<String> = [
    "변경 이력", "목차", "Revision History", "Table of Contents",
  ]
  /// 표 머리·메타 행의 첫 칸.
  private static let headerCells: Set<String> = [
    "항목", "Item", "Return", "Type Field", "Name", "API", "Method", "Type", "Field", "Describes",
  ]

  init(markdown: String) {
    chunks = Self.parse(markdown)
    grams = chunks.map { Self.bigrams("\($0.section) \($0.text)") }
    var documentFrequency: [String: Int] = [:]
    for set in grams {
      for gram in set { documentFrequency[gram, default: 0] += 1 }
    }
    let count = Double(chunks.count)
    idf = documentFrequency.mapValues { log(count / Double(1 + $0)) }
  }

  /// 겹치는 bigram 의 IDF 합을 조각 길이로 나눈 점수 순. 같으면 문서 순서.
  func search(_ text: String, limit: Int) -> [ProtocolDocChunk] {
    let query = Self.bigrams(text)
    guard !query.isEmpty else { return [] }
    let scored: [(index: Int, score: Double)] = grams.enumerated().map { index, set in
      let hits = query.intersection(set).reduce(0.0) { $0 + (idf[$1] ?? 0) }
      // 긴 문단이 bigram 을 많이 가져 위로 오는 것을 누른다
      return (index, hits / Double(set.count + 10).squareRoot())
    }
    return
      scored
      .filter { $0.score > 0 }
      .sorted { $0.score != $1.score ? $0.score > $1.score : $0.index < $1.index }
      .prefix(limit)
      .map { chunks[$0.index] }
  }

  /// 어절 안에서만 bigram 을 만든다 — 공백을 지우면 "후방 전용" 에서 "방전" 이 생긴다.
  static func bigrams(_ text: String) -> Set<String> {
    var result: Set<String> = []
    let words = text.lowercased().split { !($0.isLetter || $0.isNumber) }
    for word in words {
      let characters = Array(word)
      if characters.count == 1 { result.insert(String(characters[0])) }
      for index in characters.indices.dropLast() {
        result.insert(String(characters[index...index + 1]))
      }
    }
    return result
  }

  // MARK: - 파싱

  private static func parse(_ markdown: String) -> [ProtocolDocChunk] {
    var builder = ChunkBuilder()
    var section: String?
    var paragraph: [String] = []
    var inCode = false

    func flushParagraph() {
      defer { paragraph = [] }
      guard let section, !skippedSections.contains(section) else { return }
      let text = paragraph.joined(separator: " ")
      if text.count >= 20 { builder.append(section: section, key: nil, body: text) }
    }

    for raw in markdown.components(separatedBy: "\n") {
      let line = raw.trimmingCharacters(in: .whitespaces)
      if line.hasPrefix("```") {
        flushParagraph()
        inCode.toggle()
        continue
      }
      if inCode { continue }
      if line.hasPrefix("#") {
        flushParagraph()
        section = line.drop { $0 == "#" }.trimmingCharacters(in: .whitespaces)
        continue
      }
      if line.hasPrefix("|") {
        flushParagraph()
        guard let section, !skippedSections.contains(section),
          let row = tableRow(line)
        else { continue }
        builder.append(section: section, key: row.key, body: row.body)
        continue
      }
      if line.isEmpty || line.hasPrefix(">") || line.hasPrefix("**") {
        flushParagraph()
        continue
      }
      paragraph.append(line)
    }
    flushParagraph()
    return builder.chunks
  }

  /// 필드 행이면 (영문 필드명 key, 나머지 칸). 구분선·머리·응답 코드 행은 nil.
  private static func tableRow(_ line: String) -> (key: String?, body: String)? {
    let cells = line.trimmingCharacters(in: CharacterSet(charactersIn: "|"))
      .components(separatedBy: "|")
      .map { $0.trimmingCharacters(in: .whitespaces) }
    guard cells.count >= 2, let first = cells.first else { return nil }
    let isSeparator = first.allSatisfy { "-: ".contains($0) }
    let isStatusCode = first.prefix(3).allSatisfy(\.isNumber) && first.count > 3
    guard !isSeparator, !isStatusCode, !headerCells.contains(first) else { return nil }
    let body = cells.dropFirst().filter { !$0.isEmpty }.joined(separator: " — ")
    guard !body.isEmpty else { return nil }
    return isFieldName(first) ? (first, body) : (nil, "\(first) — \(body)")
  }

  private static func isFieldName(_ text: String) -> Bool {
    guard let head = text.first, head.isASCII, head.isLetter else { return false }
    return text.allSatisfy { $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "_" || $0 == "-") }
  }
}

/// 같은 필드 key 는 한 조각으로 합친다(Get/Set Configuration 등에 같은 행이 반복된다).
private struct ChunkBuilder {
  private var order: [String] = []
  private var entries: [String: (section: String, key: String?, bodies: [String])] = [:]

  mutating func append(section: String, key: String?, body: String) {
    let id = key ?? "\(section)\u{1}\(body)"
    if entries[id] == nil {
      order.append(id)
      entries[id] = (section, key, [])
    }
    if entries[id]?.bodies.contains(body) == false { entries[id]?.bodies.append(body) }
  }

  var chunks: [ProtocolDocChunk] {
    order.compactMap { id in
      guard let entry = entries[id] else { return nil }
      let body = entry.bodies.joined(separator: " / ")
      return ProtocolDocChunk(
        section: entry.section, key: entry.key, text: entry.key.map { "\($0): \(body)" } ?? body)
    }
  }
}

/// 질문 언어별 문서 색인. 한글이 들어간 질문은 한국어 원문, 그 밖은 영어 번역에서 찾는다.
/// 폰 언어가 아니라 질문 언어로 고른다 — 한국어 폰에서 영어로 묻는 경우가 있다.
struct ProtocolDocLibrary {
  let korean: ProtocolDocIndex
  let english: ProtocolDocIndex

  func index(for question: String) -> ProtocolDocIndex {
    question.unicodeScalars.contains(where: Self.isHangul) ? korean : english
  }

  /// 한글 음절(가–힣)·호환 자모(ㄱ–ㆎ).
  private static func isHangul(_ scalar: Unicode.Scalar) -> Bool {
    (0xAC00...0xD7A3).contains(scalar.value) || (0x3131...0x318E).contains(scalar.value)
  }
}
