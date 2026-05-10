import SwiftUI

/// Subtle one-line patient context shown on the Monitor screen so the
/// demo reads as a real monitoring app, not a generic dashboard.
struct PatientIdentityStrip: View {
    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "person.circle.fill")
                .font(.title3)
                .foregroundStyle(CardioSenseTheme.accent(for: .normal).opacity(0.85))
                .symbolRenderingMode(.hierarchical)
                .accessibilityHidden(true)

            Text("María Sánchez · 58 · Yolo County")
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .truncationMode(.tail)

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Patient María Sánchez, 58, Yolo County")
    }
}

#Preview {
    PatientIdentityStrip()
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
