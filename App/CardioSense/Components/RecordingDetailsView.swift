import SwiftUI

struct RecordingDetailsView: View {
    let sampleRate: Int
    let windowSeconds: Int
    let nWindows: Int
    let nRPeaks: Int

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(spacing: 0) {
            detailRow(title: "Sample rate", value: "\(sampleRate) Hz")
            rowDivider
            detailRow(title: "Window length", value: "\(windowSeconds) s")
            rowDivider
            detailRow(title: "Windows analyzed", value: "\(nWindows)")
            rowDivider
            detailRow(title: "R-peaks detected", value: "\(nRPeaks)")
        }
    }

    private var rowDivider: some View {
        Divider()
            .overlay(Color.primary.opacity(colorScheme == .dark ? 0.14 : 0.08))
            .padding(.leading, 2)
    }

    private func detailRow(title: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.body.monospacedDigit().weight(.semibold))
                .foregroundStyle(.primary)
        }
        .padding(.vertical, 12)
        .accessibilityElement(children: .combine)
    }
}

#Preview {
    RecordingDetailsView(sampleRate: 250, windowSeconds: 10, nWindows: 5, nRPeaks: 33)
        .clinicalCard()
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
