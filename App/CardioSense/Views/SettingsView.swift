import SwiftUI

/// Hosts the prediction-pipeline configuration (URL, refresh, auto-poll)
/// behind a gear icon on the Monitor screen so the demo surface stays clean.
struct SettingsView: View {
    let service: PredictionService
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: CardioSenseLayout.sectionSpacing) {
                    SectionLabel(title: "Patient Profile")
                    PatientProfileCard()

                    SectionLabel(title: "Connection")
                    MonitorConnectionBar(service: service)
                }
                .padding(.horizontal, CardioSenseLayout.horizontalPadding)
                .padding(.top, 8)
                .padding(.bottom, 36)
                .frame(maxWidth: 560)
                .frame(maxWidth: .infinity)
            }
            .scrollIndicators(.hidden)
            .background(CardioSenseTheme.clinicalBackground.ignoresSafeArea())
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                        .font(.body.weight(.semibold))
                }
            }
        }
    }
}

#Preview {
    let store = PredictionStore()
    SettingsView(service: PredictionService(store: store))
}
