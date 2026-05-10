import SwiftUI

struct ImportTestView: View {
    @Environment(PredictionStore.self) private var store
    @State private var selectedFixture: Fixture = .normal

    private enum Fixture: String, CaseIterable, Identifiable {
        case normal
        case arrhythmia
        case uncertain

        var id: String { rawValue }

        var shortTitle: String {
            switch self {
            case .normal: return "Normal"
            case .arrhythmia: return "Arrhythmia"
            case .uncertain: return "Uncertain"
            }
        }

        var prediction: ECGPrediction {
            switch self {
            case .normal: return SamplePredictions.normal
            case .arrhythmia: return SamplePredictions.arrhythmia
            case .uncertain: return SamplePredictions.uncertain
            }
        }

        var json: String {
            switch self {
            case .normal: return SamplePredictions.normalJSON
            case .arrhythmia: return SamplePredictions.arrhythmiaJSON
            case .uncertain: return SamplePredictions.uncertainJSON
            }
        }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: CardioSenseLayout.sectionSpacing) {
                    SectionLabel(title: "Fixture")
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Apply canned ML JSON through the same decoder as production — useful while wiring API, files, or Bluetooth.")
                            .font(.body)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                            .lineSpacing(3)

                        Picker("Fixture", selection: $selectedFixture) {
                            ForEach(Fixture.allCases) { f in
                                Text(f.shortTitle).tag(f)
                            }
                        }
                        .pickerStyle(.segmented)

                        Button {
                            store.applySample(selectedFixture.prediction)
                        } label: {
                            Label("Load into monitor", systemImage: "arrow.down.circle.fill")
                                .font(.body.weight(.semibold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 4)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CardioSenseTheme.accent(for: selectedFixture.prediction.surface))
                        .controlSize(.large)
                    }
                    .clinicalCard(
                        accent: CardioSenseTheme.accent(for: selectedFixture.prediction.surface),
                        elevated: true
                    )

                    SectionLabel(title: "Payload preview")
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Raw JSON")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.tertiary)
                            .tracking(0.8)
                        Text(selectedFixture.json)
                            .font(.caption.monospaced())
                            .foregroundStyle(.primary.opacity(0.92))
                            .textSelection(.enabled)
                            .lineSpacing(3)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .clinicalCard(elevated: false)
                }
                .padding(.horizontal, CardioSenseLayout.horizontalPadding)
                .padding(.vertical, 16)
                .padding(.bottom, 28)
                .frame(maxWidth: 560)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .scrollIndicators(.hidden)
            .background(CardioSenseTheme.clinicalBackground.ignoresSafeArea())
            .navigationTitle("Samples")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
        }
    }
}

#Preview {
    ImportTestView()
        .environment(PredictionStore())
}
