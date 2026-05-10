import SwiftUI

/// Aggregate stat card shown above the History episode list.
struct HistorySummaryCard: View {
    let summary: HistorySummary
    let rangeTitle: String

    private var arrhythmiaColor: Color {
        summary.arrhythmiaEventCount > 0
            ? CardioSenseTheme.accent(for: .arrhythmia)
            : Color.secondary
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .firstTextBaseline) {
                Text(rangeTitle.uppercased())
                    .font(.caption.weight(.bold))
                    .tracking(0.8)
                    .foregroundStyle(.tertiary)
                Spacer(minLength: 0)
                Text(rangeWindowText)
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.tertiary)
                    .monospacedDigit()
            }

            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("\(summary.arrhythmiaEventCount)")
                    .font(.system(size: 56, weight: .bold, design: .rounded))
                    .foregroundStyle(arrhythmiaColor)
                    .monospacedDigit()
                VStack(alignment: .leading, spacing: 2) {
                    Text(summary.arrhythmiaEventCount == 1 ? "arrhythmia event" : "arrhythmia events")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    if summary.arrhythmiaEventCount > 0 {
                        Text("\(formatDuration(summary.arrhythmiaTotalDuration)) total")
                            .font(.caption.weight(.medium))
                            .foregroundStyle(.secondary)
                    } else {
                        Text("Continuous normal rhythm")
                            .font(.caption.weight(.medium))
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer(minLength: 0)
            }

            Divider().opacity(0.3)

            HStack(spacing: 18) {
                statTile(
                    label: "Readings",
                    value: "\(summary.totalReadings)",
                    accessibility: "\(summary.totalReadings) readings analyzed"
                )
                statTile(
                    label: "Avg HR",
                    value: averageHRText,
                    accessibility: "Average heart rate \(averageHRText)"
                )
            }
        }
        .clinicalCard(accent: nil, elevated: true, cornerRadius: CardioSenseLayout.cornerCard)
    }

    private func statTile(label: String, value: String, accessibility: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased())
                .font(.caption2.weight(.bold))
                .tracking(0.6)
                .foregroundStyle(.tertiary)
            Text(value)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.primary)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibility)
    }

    private var averageHRText: String {
        guard let hr = summary.averageHeartRate else { return "-- bpm" }
        return "\(Int(hr.rounded())) bpm"
    }

    private var rangeWindowText: String {
        guard summary.totalReadings > 0 else { return "—" }
        let f = DateFormatter()
        f.dateStyle = .none
        f.timeStyle = .short
        let startDay = relativeDay(summary.rangeStart)
        let endDay = relativeDay(summary.rangeEnd)
        let startTime = f.string(from: summary.rangeStart)
        let endTime = f.string(from: summary.rangeEnd)
        if startDay == endDay {
            return "\(startTime) – \(endTime)"
        } else {
            return "\(startDay) \(startTime) – \(endDay) \(endTime)"
        }
    }

    private func relativeDay(_ date: Date) -> String {
        let cal = Calendar.current
        if cal.isDateInToday(date) { return "Today" }
        if cal.isDateInYesterday(date) { return "Yesterday" }
        let f = DateFormatter()
        f.dateFormat = "MMM d"
        return f.string(from: date)
    }

    private func formatDuration(_ seconds: TimeInterval) -> String {
        let s = Int(seconds.rounded())
        if s < 60 { return "\(s)s" }
        let mins = s / 60
        if mins < 60 { return "\(mins) min" }
        let hours = mins / 60
        let remMins = mins % 60
        return remMins == 0 ? "\(hours)h" : "\(hours)h \(remMins)m"
    }
}

#Preview {
    HistorySummaryCard(
        summary: HistorySummary(
            totalReadings: 1240,
            arrhythmiaEventCount: 3,
            arrhythmiaTotalDuration: 11 * 60,
            averageHeartRate: 74.2,
            rangeStart: Date().addingTimeInterval(-3600),
            rangeEnd: Date()
        ),
        rangeTitle: "Last hour"
    )
    .padding()
    .background(CardioSenseTheme.clinicalBackground)
}
