import SwiftUI

struct DetailsView: View {
    @Environment(PredictionStore.self) private var store

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: CardioSenseLayout.sectionSpacing) {
                    SectionLabel(title: "Purpose")
                    referenceCard(
                        title: "About this readout",
                        body: "CardioSense summarizes an automated review of a short ECG segment. It is intended for study and monitoring workflows, not as a sole basis for clinical decisions."
                    )

                    SectionLabel(title: "How to read it")
                    referenceCard(
                        title: "Confidence",
                        body: "Confidence is the estimated probability of the reported label (Normal or Arrhythmia). When confidence is below 60%, results are shown as uncertain and may benefit from another recording or review."
                    )

                    SectionLabel(title: "Live snapshot")
                    referenceCard(
                        title: "Class probabilities",
                        body: "Normal and Arrhythmia probabilities always sum to 100%. They describe how the model weighed both outcomes for this window."
                    ) {
                        miniProbabilitySummary
                    }

                    referenceCard(
                        title: "Heart rate",
                        body: "Heart rate is derived from detected beats in the segment. A missing value means the estimate was not available for this window."
                    )

                    referenceCard(
                        title: "HRV metrics",
                        body: "RMSSD reflects short-term beat-to-beat variation. SDNN captures overall variability across the window. pNN50 is the fraction of intervals that change substantially beat-to-beat. Mean RR is the average interval between beats and relates to overall rate."
                    )

                    referenceCard(
                        title: "Recording metadata",
                        body: "Sample rate, window length, and window count describe how the signal was segmented. R-peaks counts how many beats were detected for analysis."
                    )
                }
                .padding(.horizontal, CardioSenseLayout.horizontalPadding)
                .padding(.vertical, 16)
                .padding(.bottom, 28)
                .frame(maxWidth: 560)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .scrollIndicators(.hidden)
            .background(CardioSenseTheme.clinicalBackground.ignoresSafeArea())
            .navigationTitle("Reference")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
        }
    }

    private func referenceCard(
        title: String,
        body: String
    ) -> some View {
        referenceCard(title: title, body: body) { EmptyView() }
    }

    private func referenceCard<E: View>(
        title: String,
        body: String,
        @ViewBuilder embedded: () -> E
    ) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title)
                .font(.headline.weight(.semibold))
                .foregroundStyle(.primary)
            Text(body)
                .font(.body)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .lineSpacing(4)
            embedded()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .clinicalCard(elevated: false, cornerRadius: CardioSenseLayout.cornerCard)
    }

    private var miniProbabilitySummary: some View {
        let p = store.currentPrediction.probabilities
        return VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Normal")
                    .font(.subheadline.weight(.medium))
                Spacer()
                Text(formatPct(p.normal))
                    .font(.body.monospacedDigit().weight(.semibold))
                    .foregroundStyle(CardioSenseTheme.accent(for: .normal))
            }
            HStack {
                Text("Arrhythmia")
                    .font(.subheadline.weight(.medium))
                Spacer()
                Text(formatPct(p.arrhythmia))
                    .font(.body.monospacedDigit().weight(.semibold))
                    .foregroundStyle(CardioSenseTheme.accent(for: .arrhythmia))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: CardioSenseLayout.cornerNested, style: .continuous)
                .fill(Color.primary.opacity(0.05))
        )
    }

    private func formatPct(_ v: Double) -> String {
        "\(Int((v * 100).rounded()))%"
    }
}

#Preview {
    DetailsView()
        .environment(PredictionStore())
}
