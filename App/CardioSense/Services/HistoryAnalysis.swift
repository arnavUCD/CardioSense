import Foundation

/// Time window options for the History tab filter row.
enum HistoryRange: CaseIterable, Identifiable {
    case tenMin
    case hour
    case day
    case week
    case month

    var id: String { title }

    var title: String {
        switch self {
        case .tenMin: return "Last 10 min"
        case .hour:   return "Last hour"
        case .day:    return "Last day"
        case .week:   return "Last week"
        case .month:  return "Last month"
        }
    }

    /// Window length back from "now".
    var interval: TimeInterval {
        switch self {
        case .tenMin: return 10 * 60
        case .hour:   return 60 * 60
        case .day:    return 24 * 60 * 60
        case .week:   return 7 * 24 * 60 * 60
        case .month:  return 30 * 24 * 60 * 60
        }
    }
}

/// Aggregate stats over a filtered slice of history.
struct HistorySummary {
    let totalReadings: Int
    let arrhythmiaEventCount: Int
    let arrhythmiaTotalDuration: TimeInterval
    let averageHeartRate: Double?
    let rangeStart: Date
    let rangeEnd: Date
}

/// A contiguous run of readings sharing the same inference surface.
struct HistoryEpisode: Identifiable {
    let id = UUID()
    let surface: ECGPrediction.InferenceSurface
    let start: Date
    let end: Date
    let peakConfidence: Double
    let representativeHeartRate: Double?
    /// True for the most-recent episode whose end is "now".
    let isOngoing: Bool

    var duration: TimeInterval { end.timeIntervalSince(start) }
}

enum HistoryAnalysis {
    /// Items inside the range, sorted ascending by time.
    static func filter(
        _ items: [PredictionHistoryItem],
        within range: HistoryRange,
        relativeTo reference: Date = Date()
    ) -> [PredictionHistoryItem] {
        let cutoff = reference.addingTimeInterval(-range.interval)
        return items
            .filter { $0.recordedAt >= cutoff && $0.recordedAt <= reference }
            .sorted { $0.recordedAt < $1.recordedAt }
    }

    static func summary(
        for items: [PredictionHistoryItem],
        range: HistoryRange,
        relativeTo reference: Date = Date()
    ) -> HistorySummary {
        let scoped = filter(items, within: range, relativeTo: reference)
        let episodes = self.episodes(from: scoped, range: range, relativeTo: reference)
        let arrhythmiaEpisodes = episodes.filter { $0.surface == .arrhythmia }
        let totalDuration = arrhythmiaEpisodes.reduce(0) { $0 + $1.duration }

        let hrValues = scoped.compactMap { $0.prediction.heart_rate }
        let avgHR: Double? = hrValues.isEmpty ? nil : hrValues.reduce(0, +) / Double(hrValues.count)

        let start = scoped.first?.recordedAt ?? reference.addingTimeInterval(-range.interval)
        let end = scoped.last?.recordedAt ?? reference

        return HistorySummary(
            totalReadings: scoped.count,
            arrhythmiaEventCount: arrhythmiaEpisodes.count,
            arrhythmiaTotalDuration: totalDuration,
            averageHeartRate: avgHR,
            rangeStart: start,
            rangeEnd: end
        )
    }

    /// Group consecutive same-surface readings into episodes. Returns newest-first.
    static func episodes(
        from sortedAscending: [PredictionHistoryItem],
        range: HistoryRange,
        relativeTo reference: Date = Date()
    ) -> [HistoryEpisode] {
        guard !sortedAscending.isEmpty else { return [] }

        var episodes: [HistoryEpisode] = []
        var runStart = sortedAscending[0].recordedAt
        var runSurface = sortedAscending[0].prediction.surface
        var peakConfidence = sortedAscending[0].prediction.confidence
        var hrSum = sortedAscending[0].prediction.heart_rate ?? 0
        var hrCount = sortedAscending[0].prediction.heart_rate == nil ? 0 : 1
        var lastTime = sortedAscending[0].recordedAt

        for item in sortedAscending.dropFirst() {
            let s = item.prediction.surface
            if s == runSurface {
                peakConfidence = max(peakConfidence, item.prediction.confidence)
                if let hr = item.prediction.heart_rate {
                    hrSum += hr
                    hrCount += 1
                }
                lastTime = item.recordedAt
            } else {
                episodes.append(
                    HistoryEpisode(
                        surface: runSurface,
                        start: runStart,
                        end: item.recordedAt,
                        peakConfidence: peakConfidence,
                        representativeHeartRate: hrCount > 0 ? hrSum / Double(hrCount) : nil,
                        isOngoing: false
                    )
                )
                runStart = item.recordedAt
                runSurface = s
                peakConfidence = item.prediction.confidence
                hrSum = item.prediction.heart_rate ?? 0
                hrCount = item.prediction.heart_rate == nil ? 0 : 1
                lastTime = item.recordedAt
            }
        }

        // Final run extends to "now" (ongoing).
        episodes.append(
            HistoryEpisode(
                surface: runSurface,
                start: runStart,
                end: max(lastTime, reference),
                peakConfidence: peakConfidence,
                representativeHeartRate: hrCount > 0 ? hrSum / Double(hrCount) : nil,
                isOngoing: true
            )
        )

        return episodes.reversed()
    }
}
