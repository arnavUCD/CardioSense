import SwiftUI

struct ProbabilityBar: View {
    let probabilities: ClassProbabilities
    let accentNormal: Color
    let accentArrhythmia: Color

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            probabilitySplitStrip

            probabilityRow(
                title: "Normal",
                value: probabilities.normal,
                color: accentNormal
            )
            probabilityRow(
                title: "Arrhythmia",
                value: probabilities.arrhythmia,
                color: accentArrhythmia
            )
        }
    }

    /// Single fused strip showing class mix at a glance (WHOOP-style proportion bar, restrained).
    private var probabilitySplitStrip: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let n = CGFloat(probabilities.normal)
            let a = CGFloat(probabilities.arrhythmia)
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(Color.primary.opacity(colorScheme == .dark ? 0.12 : 0.07))
                    .frame(height: 12)

                HStack(spacing: 0) {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [accentNormal.opacity(0.75), accentNormal],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: max(0, w * n))

                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [accentArrhythmia.opacity(0.75), accentArrhythmia],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: max(0, w * a))
                }
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
        }
        .frame(height: 12)
        .accessibilityLabel(
            "Class mix Normal \(Int((probabilities.normal * 100).rounded())) percent, Arrhythmia \(Int((probabilities.arrhythmia * 100).rounded())) percent"
        )
    }

    private func probabilityRow(title: String, value: Double, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(title)
                    .font(.subheadline.weight(.medium))
                Spacer()
                Text(formatPercent(value))
                    .font(.subheadline.monospacedDigit().weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule(style: .continuous)
                        .fill(Color.primary.opacity(colorScheme == .dark ? 0.12 : 0.07))
                    Capsule(style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [color.opacity(0.65), color],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: max(10, geo.size.width * CGFloat(value)))
                }
            }
            .frame(height: 10)
            .accessibilityLabel("\(title) probability \(formatPercent(value))")
        }
    }

    private func formatPercent(_ p: Double) -> String {
        let pct = (p * 100).rounded()
        return "\(Int(pct))%"
    }
}

#Preview {
    ProbabilityBar(
        probabilities: SamplePredictions.normal.probabilities,
        accentNormal: CardioSenseTheme.accent(for: .normal),
        accentArrhythmia: CardioSenseTheme.accent(for: .arrhythmia)
    )
    .clinicalCard()
    .padding()
    .background(CardioSenseTheme.clinicalBackground)
}
