import SwiftUI

/// Minimal live indicator: small status dot + connection line ("Live · 12:57 AM").
/// Replaces the full prediction-URL card on the Monitor screen — the full
/// controls now live behind the Settings gear.
struct LiveStatusPill: View {
    let connectionLine: String
    let isLive: Bool

    @State private var pulse = false

    var body: some View {
        HStack(spacing: 8) {
            statusDot

            Text(connectionLine)
                .font(.caption.weight(.medium))
                .foregroundStyle(.secondary)

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(isLive ? "Live, \(connectionLine)" : connectionLine)
    }

    @ViewBuilder
    private var statusDot: some View {
        if isLive {
            ZStack {
                Circle()
                    .fill(CardioSenseTheme.accent(for: .normal).opacity(pulse ? 0.0 : 0.45))
                    .frame(width: 16, height: 16)
                    .scaleEffect(pulse ? 2.0 : 1.0)
                    .animation(
                        .easeOut(duration: 1.2).repeatForever(autoreverses: false),
                        value: pulse
                    )

                Circle()
                    .fill(CardioSenseTheme.accent(for: .normal))
                    .frame(width: 8, height: 8)
                    .opacity(pulse ? 1.0 : 0.55)
                    .animation(
                        .easeInOut(duration: 1.0).repeatForever(autoreverses: true),
                        value: pulse
                    )
            }
            .frame(width: 16, height: 16)
            .onAppear { pulse = true }
            .onDisappear { pulse = false }
            .accessibilityHidden(true)
        } else {
            Circle()
                .fill(Color.secondary.opacity(0.5))
                .frame(width: 8, height: 8)
                .frame(width: 16, height: 16)
                .accessibilityHidden(true)
        }
    }
}

#Preview {
    VStack(alignment: .leading, spacing: 12) {
        LiveStatusPill(connectionLine: "Live · 12:57 AM", isLive: true)
        LiveStatusPill(connectionLine: "Waiting for model output", isLive: false)
    }
    .padding()
    .background(CardioSenseTheme.clinicalBackground)
}
