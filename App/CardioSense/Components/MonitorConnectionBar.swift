import SwiftUI

/// Compact endpoint + refresh controls for the local HTTP demo pipeline.
struct MonitorConnectionBar: View {
    let service: PredictionService

    private var urlBinding: Binding<String> {
        Binding(
            get: { service.predictionURLString },
            set: { service.predictionURLString = $0 }
        )
    }

    private var autoRefreshBinding: Binding<Bool> {
        Binding(
            get: { service.autoRefreshEnabled },
            set: { service.autoRefreshEnabled = $0 }
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Image(systemName: "link.circle.fill")
                    .font(.body.weight(.medium))
                    .foregroundStyle(.secondary)
                    .symbolRenderingMode(.hierarchical)
                Text("Prediction URL")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.secondary)
                    .tracking(0.6)
                Spacer(minLength: 0)
                if service.isFetching {
                    ProgressView()
                        .controlSize(.small)
                        .accessibilityLabel("Fetching")
                }
            }

            TextField("http://127.0.0.1:8080/shared/prediction.json", text: urlBinding)
                .textFieldStyle(.plain)
                .font(.footnote.monospaced())
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: CardioSenseLayout.cornerNested, style: .continuous)
                        .fill(Color.primary.opacity(0.055))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: CardioSenseLayout.cornerNested, style: .continuous)
                        .strokeBorder(Color.primary.opacity(0.08), lineWidth: 1)
                )
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(.URL)

            HStack(spacing: 12) {
                Button {
                    Task { await service.refresh() }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.regular)
                .disabled(service.isFetching)

                Toggle(isOn: autoRefreshBinding) {
                    Text("Auto (2s)")
                        .font(.subheadline.weight(.medium))
                }
                .toggleStyle(.switch)
                .labelsHidden()
                .accessibilityLabel("Auto refresh every 2 seconds")
            }

            Text(service.connectionLine)
                .font(.caption.weight(.medium))
                .foregroundStyle(.tertiary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .clinicalCard(accent: nil, elevated: false, cornerRadius: CardioSenseLayout.cornerCard)
    }
}

#Preview {
    let store = PredictionStore()
    MonitorConnectionBar(service: PredictionService(store: store))
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
