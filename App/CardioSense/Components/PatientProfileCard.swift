import SwiftUI

/// Read-only patient profile shown at the top of the Settings sheet.
/// Reinforces the social-good narrative inside the app: when a judge taps
/// the gear to see the technical wiring, they also see who the data is for.
struct PatientProfileCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                Image(systemName: "person.circle.fill")
                    .font(.system(size: 40, weight: .regular))
                    .foregroundStyle(CardioSenseTheme.accent(for: .normal).opacity(0.85))
                    .symbolRenderingMode(.hierarchical)
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 2) {
                    Text("María Sánchez")
                        .font(.headline)
                        .foregroundStyle(.primary)
                    Text("58 · Agricultural worker")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer(minLength: 0)
            }

            Divider()
                .opacity(0.3)

            VStack(alignment: .leading, spacing: 12) {
                profileRow(label: "Location", value: "Yolo County, California")
                profileRow(label: "Primary language", value: "Spanish")
                profileRow(label: "Insurance status", value: "Uninsured")
                profileRow(label: "Monitoring since", value: "January 2026")
                profileRow(label: "Partner clinic", value: "Communicare Health Centers — Woodland")
            }
        }
        .clinicalCard(accent: nil, elevated: false, cornerRadius: CardioSenseLayout.cornerCard)
        .accessibilityElement(children: .contain)
    }

    private func profileRow(label: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.tertiary)
                .tracking(0.3)
            Spacer(minLength: 8)
            Text(value)
                .font(.caption.weight(.medium))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.trailing)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

#Preview {
    ScrollView {
        PatientProfileCard()
            .padding()
    }
    .background(CardioSenseTheme.clinicalBackground)
}
