import SwiftUI

/// WHOOP-adjacent section rails — uppercase micro-label with generous tracking.
struct SectionLabel: View {
    let title: String

    var body: some View {
        Text(title.uppercased())
            .font(.caption.weight(.semibold))
            .tracking(2.0)
            .foregroundStyle(.secondary.opacity(0.92))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.leading, 2)
            .accessibilityAddTraits(.isHeader)
    }
}

#Preview {
    SectionLabel(title: "Vitals")
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
