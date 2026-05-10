import SwiftUI

struct MetricTile: View {
    let title: String
    let value: String
    let unit: String?
    let systemImage: String
    let accent: Color

    init(
        title: String,
        value: String,
        unit: String? = nil,
        systemImage: String,
        accent: Color = .accentColor
    ) {
        self.title = title
        self.value = value
        self.unit = unit
        self.systemImage = systemImage
        self.accent = accent
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label(title, systemImage: systemImage)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .labelStyle(.titleAndIcon)
                .symbolRenderingMode(.hierarchical)
                .tint(accent.opacity(0.85))

            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text(value)
                    .font(.system(size: 44, weight: .semibold, design: .rounded))
                    .foregroundStyle(.primary)
                    .minimumScaleFactor(0.65)
                    .lineLimit(1)
                    .monospacedDigit()
                if let unit {
                    Text(unit)
                        .font(.title3.weight(.medium))
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview {
    MetricTile(
        title: "Heart rate",
        value: "72",
        unit: "bpm",
        systemImage: "heart.fill",
        accent: CardioSenseTheme.accent(for: .normal)
    )
    .clinicalCard(accent: CardioSenseTheme.accent(for: .normal))
    .padding()
    .background(CardioSenseTheme.clinicalBackground)
}
