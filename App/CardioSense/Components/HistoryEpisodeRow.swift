import SwiftUI

/// One condensed row in the History list — a single state-period (episode).
struct HistoryEpisodeRow: View {
    let episode: HistoryEpisode
    /// First episode in the range gets a neutral title (no "restored" wording).
    let isFirstInRange: Bool

    private var accent: Color {
        CardioSenseTheme.accent(for: episode.surface)
    }

    var body: some View {
        HStack(alignment: .center, spacing: 14) {
            ZStack {
                Circle()
                    .fill(accent.opacity(0.22))
                    .frame(width: 36, height: 36)
                Circle()
                    .fill(accent)
                    .frame(width: 12, height: 12)
            }
            .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 5) {
                Text(titleText)
                    .font(.body.weight(.semibold))
                    .foregroundStyle(.primary)
                Text(timeAndDurationText)
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.tertiary)
            }

            Spacer(minLength: 0)

            VStack(alignment: .trailing, spacing: 5) {
                Text(confidenceText)
                    .font(.subheadline.monospacedDigit().weight(.semibold))
                    .foregroundStyle(.secondary)
                Text(heartRateText)
                    .font(.caption.monospacedDigit().weight(.medium))
                    .foregroundStyle(.tertiary)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilitySummary)
    }

    private var titleText: String {
        switch episode.surface {
        case .arrhythmia: return "Arrhythmia detected"
        case .normal: return isFirstInRange ? "Normal rhythm" : "Normal rhythm restored"
        case .uncertain: return "Low-confidence reading"
        }
    }

    private var timeAndDurationText: String {
        let timeText = formatStartTime(episode.start)
        let durationText: String
        if episode.isOngoing {
            durationText = "ongoing"
        } else if episode.duration < 60 {
            durationText = "< 1 min"
        } else {
            let mins = Int((episode.duration / 60).rounded())
            durationText = mins == 1 ? "for 1 min" : "for \(mins) min"
        }
        return "at \(timeText) · \(durationText)"
    }

    private var confidenceText: String {
        let pct = Int((episode.peakConfidence * 100).rounded())
        return "\(pct)% conf."
    }

    private var heartRateText: String {
        guard let hr = episode.representativeHeartRate else { return "-- bpm" }
        return "\(Int(hr.rounded())) bpm"
    }

    private func formatStartTime(_ date: Date) -> String {
        let cal = Calendar.current
        let timeFmt = DateFormatter()
        timeFmt.dateStyle = .none
        timeFmt.timeStyle = .short
        let timeText = timeFmt.string(from: date)
        if cal.isDateInToday(date) { return timeText }
        if cal.isDateInYesterday(date) { return "Yesterday \(timeText)" }
        let dayFmt = DateFormatter()
        dayFmt.dateFormat = "MMM d"
        return "\(dayFmt.string(from: date)) \(timeText)"
    }

    private var accessibilitySummary: String {
        "\(titleText), \(timeAndDurationText), \(confidenceText), \(heartRateText)"
    }
}

#Preview {
    VStack(spacing: 12) {
        HistoryEpisodeRow(
            episode: HistoryEpisode(
                surface: .arrhythmia,
                start: Date().addingTimeInterval(-15 * 60),
                end: Date().addingTimeInterval(-11 * 60),
                peakConfidence: 0.94,
                representativeHeartRate: 118,
                isOngoing: false
            ),
            isFirstInRange: false
        )
        .clinicalCard(accent: CardioSenseTheme.accent(for: .arrhythmia))

        HistoryEpisodeRow(
            episode: HistoryEpisode(
                surface: .normal,
                start: Date().addingTimeInterval(-11 * 60),
                end: Date(),
                peakConfidence: 0.97,
                representativeHeartRate: 68,
                isOngoing: true
            ),
            isFirstInRange: false
        )
        .clinicalCard(accent: CardioSenseTheme.accent(for: .normal))
    }
    .padding()
    .background(CardioSenseTheme.clinicalBackground)
}
