import SwiftUI

/// Ring-style confidence readout (WHOOP-inspired); stays analytical, not gamified.
struct ConfidenceGauge: View {
    let confidence: Double
    let accent: Color

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.colorScheme) private var colorScheme

    private var percentInt: Int {
        Int((confidence * 100).rounded())
    }

    var body: some View {
        let lineWidth: CGFloat = 11
        let size: CGFloat = 132

        ZStack {
            Circle()
                .stroke(
                    Color.primary.opacity(colorScheme == .dark ? 0.12 : 0.08),
                    lineWidth: lineWidth
                )
                .frame(width: size, height: size)

            Circle()
                .trim(from: 0, to: CGFloat(confidence))
                .stroke(
                    AngularGradient(
                        colors: [
                            accent.opacity(0.55),
                            accent,
                            accent.opacity(0.85),
                        ],
                        center: .center,
                        angle: .degrees(-90)
                    ),
                    style: StrokeStyle(lineWidth: lineWidth, lineCap: .round)
                )
                .frame(width: size, height: size)
                .rotationEffect(.degrees(-90))
                .animation(
                    reduceMotion ? nil : .spring(response: 0.55, dampingFraction: 0.78),
                    value: confidence
                )

            VStack(spacing: 4) {
                Text("\(percentInt)%")
                    .font(.system(size: 30, weight: .semibold, design: .rounded))
                    .monospacedDigit()
                    .foregroundStyle(.primary)
                    .minimumScaleFactor(0.7)
                    .lineLimit(1)
                Text("confidence")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.tertiary)
                    .textCase(.uppercase)
                    .tracking(0.8)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Model confidence \(percentInt) percent")
        }
        .frame(width: size, height: size)
    }
}

#Preview {
    ConfidenceGauge(confidence: 0.91, accent: CardioSenseTheme.accent(for: .normal))
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
