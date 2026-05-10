import SwiftUI

struct HistoryRow: View {
    let item: PredictionHistoryItem

    private var surface: ECGPrediction.InferenceSurface {
        item.prediction.surface
    }

    private var accent: Color {
        CardioSenseTheme.accent(for: surface)
    }

    var body: some View {
        HStack(alignment: .center, spacing: 14) {
            ZStack {
                Circle()
                    .fill(accent.opacity(0.22))
                    .frame(width: 36, height: 36)
                Circle()
                    .fill(accent.opacity(0.55))
                    .frame(width: 12, height: 12)
            }
            .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 5) {
                Text(CardioSenseTheme.title(for: surface))
                    .font(.body.weight(.semibold))
                    .foregroundStyle(.primary)
                Text(timeString)
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.tertiary)
            }

            Spacer(minLength: 0)

            VStack(alignment: .trailing, spacing: 5) {
                Text(formatConfidence(item.prediction.confidence))
                    .font(.subheadline.monospacedDigit().weight(.semibold))
                    .foregroundStyle(.secondary)
                Text(heartRateLine)
                    .font(.caption.monospacedDigit().weight(.medium))
                    .foregroundStyle(.tertiary)
            }
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilitySummary)
    }

    private var heartRateLine: String {
        if let hr = item.prediction.heart_rate {
            return String(format: "%.0f bpm", hr)
        }
        return "-- bpm"
    }

    private func formatConfidence(_ c: Double) -> String {
        let pct = (c * 100).rounded()
        return "\(Int(pct))% conf."
    }

    private var timeString: String {
        let f = DateFormatter()
        f.dateStyle = .medium
        f.timeStyle = .short
        return f.string(from: item.recordedAt)
    }

    private var accessibilitySummary: String {
        "\(CardioSenseTheme.title(for: surface)), \(formatConfidence(item.prediction.confidence)), \(heartRateLine), \(timeString)"
    }
}

#Preview {
    ScrollView {
        HistoryRow(item: PredictionHistoryItem(id: UUID(), recordedAt: Date(), prediction: SamplePredictions.normal))
            .clinicalCard(accent: CardioSenseTheme.accent(for: .normal))
            .padding()
    }
    .background(CardioSenseTheme.clinicalBackground)
}
