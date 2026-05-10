import SwiftUI

struct StatusHeader: View {
    let prediction: ECGPrediction
    let surface: ECGPrediction.InferenceSurface
    let lastAnalyzed: Date

    private var accent: Color { CardioSenseTheme.accent(for: surface) }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 14) {
                iconBadge

                VStack(alignment: .leading, spacing: 8) {
                    Text(CardioSenseTheme.title(for: surface))
                        .font(.system(.title, design: .rounded).weight(.bold))
                        .tracking(-0.5)
                        .foregroundStyle(.primary)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(CardioSenseTheme.headlineSubtitle(prediction: prediction, surface: surface))
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .lineSpacing(3)
                }
            }

            HStack {
                Text("Model label")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
                Spacer(minLength: 8)
                Text(prediction.label)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Model label \(prediction.label)")

            HStack(spacing: 10) {
                Label(lastAnalyzedFormatted, systemImage: "clock")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.tertiary)

                Spacer(minLength: 0)

                AlertBadge(prediction: prediction, surface: surface)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var iconBadge: some View {
        ZStack {
            Circle()
                .fill(accent.opacity(0.16))
            Circle()
                .strokeBorder(accent.opacity(0.28), lineWidth: 1)
            Image(systemName: iconName)
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(accent)
                .symbolRenderingMode(.hierarchical)
        }
        .frame(width: 52, height: 52)
        .accessibilityHidden(true)
    }

    private var iconName: String {
        switch surface {
        case .normal: return "waveform.path.ecg"
        case .arrhythmia: return "heart.text.square.fill"
        case .uncertain: return "questionmark.circle.fill"
        }
    }

    private var lastAnalyzedFormatted: String {
        let f = RelativeDateTimeFormatter()
        f.unitsStyle = .abbreviated
        return "Last analyzed \(f.localizedString(for: lastAnalyzed, relativeTo: Date()))"
    }
}

private struct AlertBadge: View {
    let prediction: ECGPrediction
    let surface: ECGPrediction.InferenceSurface

    var body: some View {
        let showAlert = prediction.arrhythmia_detected && surface != .uncertain
        Group {
            if showAlert {
                Text("Review recommended")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 7)
                    .background(
                        Capsule(style: .continuous)
                            .fill(CardioSenseTheme.accent(for: .arrhythmia).opacity(0.16))
                    )
                    .foregroundStyle(CardioSenseTheme.accent(for: .arrhythmia))
            } else if surface == .uncertain {
                Text("Low confidence")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 7)
                    .background(
                        Capsule(style: .continuous)
                            .fill(CardioSenseTheme.accent(for: .uncertain).opacity(0.18))
                    )
                    .foregroundStyle(CardioSenseTheme.accent(for: .uncertain))
            }
        }
        .accessibilityElement(children: .combine)
    }
}

#Preview("Normal") {
    StatusHeader(
        prediction: SamplePredictions.normal,
        surface: .normal,
        lastAnalyzed: Date()
    )
    .padding()
    .background(CardioSenseTheme.clinicalBackground)
}
