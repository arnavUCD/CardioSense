import SwiftUI

/// Horizontal scrolling chip row for selecting a History time window.
struct HistoryRangeChips: View {
    @Binding var selection: HistoryRange

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(HistoryRange.allCases) { range in
                    chip(for: range)
                }
            }
            .padding(.horizontal, 4)
        }
    }

    private func chip(for range: HistoryRange) -> some View {
        let selected = (range == selection)
        let mint = CardioSenseTheme.accent(for: .normal)

        return Button {
            withAnimation(.easeInOut(duration: 0.2)) {
                selection = range
            }
        } label: {
            Text(range.title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(selected ? Color.black : Color.secondary)
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(
                    Capsule(style: .continuous)
                        .fill(selected ? mint : Color.clear)
                )
                .overlay(
                    Capsule(style: .continuous)
                        .strokeBorder(
                            selected ? Color.clear : Color.primary.opacity(0.18),
                            lineWidth: 1
                        )
                )
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

#Preview {
    @Previewable @State var sel: HistoryRange = .hour
    return HistoryRangeChips(selection: $sel)
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
