import SwiftUI

struct MainMonitorView: View {
    @Environment(PredictionStore.self) private var store
    @Environment(PredictionService.self) private var predictionService

    @State private var showSettings = false

    private var prediction: ECGPrediction { store.currentPrediction }
    private var surface: ECGPrediction.InferenceSurface { prediction.surface }
    private var accent: Color { CardioSenseTheme.accent(for: surface) }

    private var isUncertain: Bool {
        prediction.confidence < CardioSenseThresholds.uncertainConfidence
    }

    private var isLive: Bool {
        predictionService.lastSuccessfulFetchAt != nil
            && predictionService.connectionLine.hasPrefix("Live")
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: CardioSenseLayout.sectionSpacing) {
                    LiveStatusPill(
                        connectionLine: predictionService.connectionLine,
                        isLive: isLive
                    )

                    PatientIdentityStrip()

                    heroSection
                        .transition(.opacity.combined(with: .move(edge: .top)))

                    SectionLabel(title: "Heart rate")
                    MetricTile(
                        title: "Heart rate",
                        value: heartRateDisplayValue,
                        unit: heartRateDisplayUnit,
                        systemImage: "heart.fill",
                        accent: accent
                    )
                    .clinicalCard(accent: accent, elevated: true)

                    SectionLabel(title: "Classification")
                    ProbabilityBar(
                        probabilities: prediction.probabilities,
                        accentNormal: CardioSenseTheme.accent(for: .normal),
                        accentArrhythmia: CardioSenseTheme.accent(for: .arrhythmia)
                    )
                    .clinicalCard(accent: accent, elevated: true)

                    SectionLabel(title: "Heart rate variability")
                    HRVGrid(hrv: prediction.hrv, accent: accent)
                        .clinicalCard(accent: accent, elevated: true)

                    SectionLabel(title: "Signal detail")
                    RecordingDetailsView(
                        sampleRate: prediction.sample_rate,
                        windowSeconds: prediction.window_seconds,
                        nWindows: prediction.n_windows,
                        nRPeaks: prediction.n_r_peaks
                    )
                    .clinicalCard(accent: nil, elevated: false)
                }
                .padding(.horizontal, CardioSenseLayout.horizontalPadding)
                .padding(.top, 8)
                .padding(.bottom, 36)
                .frame(maxWidth: 560)
                .frame(maxWidth: .infinity)
            }
            .scrollIndicators(.hidden)
            .background(CardioSenseTheme.clinicalBackground.ignoresSafeArea())
            .navigationTitle("Monitor")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showSettings = true
                    } label: {
                        Image(systemName: "gearshape.fill")
                            .font(.body.weight(.medium))
                            .foregroundStyle(.secondary)
                    }
                    .accessibilityLabel("Settings")
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView(service: predictionService)
            }
            .animation(.easeOut(duration: 0.35), value: store.lastAnalyzedAt)
            .task {
                await predictionService.refresh()
            }
        }
    }

    private var heroSection: some View {
        VStack(spacing: 22) {
            StatusHeader(
                prediction: prediction,
                surface: surface,
                lastAnalyzed: store.lastAnalyzedAt
            )

            ConfidenceGauge(confidence: prediction.confidence, accent: accent)
                .frame(maxWidth: .infinity)
                .padding(.top, 4)

            if isUncertain {
                Label("Low confidence result — interpret with care.", systemImage: "info.circle")
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(CardioSenseTheme.accent(for: .uncertain))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(14)
                    .background(
                        RoundedRectangle(cornerRadius: CardioSenseLayout.cornerNested, style: .continuous)
                            .fill(CardioSenseTheme.accent(for: .uncertain).opacity(0.12))
                    )
                    .accessibilityLabel("Low confidence result. Interpret with care.")
            }
        }
        .clinicalCard(
            accent: accent,
            elevated: true,
            cornerRadius: CardioSenseLayout.cornerHero,
            padding: CardioSenseLayout.cardPadding + 2
        )
    }

    /// Requirement: null heart rate renders as `-- bpm` (single readable token).
    private var heartRateDisplayValue: String {
        guard let hr = prediction.heart_rate else { return "-- bpm" }
        return String(format: "%.0f", hr)
    }

    private var heartRateDisplayUnit: String? {
        prediction.heart_rate == nil ? nil : "bpm"
    }
}

#Preview {
    let store = PredictionStore()
    MainMonitorView()
        .environment(store)
        .environment(PredictionService(store: store))
}
