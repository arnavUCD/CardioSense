import SwiftUI

struct HRVGrid: View {
    let hrv: HRVMetrics?
    let accent: Color

    @Environment(\.colorScheme) private var colorScheme

    private let columns = [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            LazyVGrid(columns: columns, spacing: 12) {
                metricCell(title: "RMSSD", value: formatMs(hrv?.rmssd), caption: "Short-term variability")
                metricCell(title: "SDNN", value: formatMs(hrv?.sdnn), caption: "Overall variability")
                metricCell(title: "pNN50", value: formatRatio(hrv?.pnn50), caption: "Beat-to-beat jumps")
                metricCell(title: "Mean RR", value: formatMs(hrv?.mean_rr_ms), caption: "Avg. beat interval")
            }
        }
    }

    private func metricCell(title: String, value: String, caption: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
                .tracking(0.6)
            Text(value)
                .font(.system(.title3, design: .rounded).weight(.semibold))
                .foregroundStyle(.primary)
                .monospacedDigit()
                .minimumScaleFactor(0.85)
            Text(caption)
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .fixedSize(horizontal: false, vertical: true)
                .lineSpacing(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: CardioSenseLayout.cornerNested, style: .continuous)
                .fill(Color.primary.opacity(colorScheme == .dark ? 0.06 : 0.045))
        )
        .overlay(
            RoundedRectangle(cornerRadius: CardioSenseLayout.cornerNested, style: .continuous)
                .strokeBorder(accent.opacity(0.12), lineWidth: 1)
        )
    }

    private func formatMs(_ v: Double?) -> String {
        guard let v else { return "--" }
        return String(format: "%.1f ms", v)
    }

    private func formatRatio(_ v: Double?) -> String {
        guard let v else { return "--" }
        return String(format: "%.0f%%", v * 100)
    }
}

#Preview {
    HRVGrid(hrv: SamplePredictions.normal.hrv, accent: CardioSenseTheme.accent(for: .normal))
        .clinicalCard(accent: CardioSenseTheme.accent(for: .normal))
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
