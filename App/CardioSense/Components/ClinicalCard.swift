import SwiftUI

struct ClinicalCardModifier: ViewModifier {
    var accent: Color?
    var elevated: Bool
    var cornerRadius: CGFloat
    var paddingLength: CGFloat

    @Environment(\.colorScheme) private var colorScheme

    func body(content: Content) -> some View {
        let shadow = CardioSenseTheme.cardShadow(elevated: elevated, colorScheme: colorScheme)
        let strokeAccent = accent ?? Color.primary.opacity(colorScheme == .dark ? 0.2 : 0.12)

        content
            .padding(paddingLength)
            .background {
                ZStack {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .fill(CardioSenseTheme.cardBackground)
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .strokeBorder(
                            LinearGradient(
                                colors: [
                                    strokeAccent.opacity(colorScheme == .dark ? 0.55 : 0.38),
                                    Color.primary.opacity(colorScheme == .dark ? 0.10 : 0.05),
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                }
                .shadow(color: shadow.color, radius: shadow.radius, x: 0, y: shadow.y)
            }
    }
}

extension View {
    func clinicalCard(
        accent: Color? = nil,
        elevated: Bool = true,
        cornerRadius: CGFloat = CardioSenseLayout.cornerCard,
        padding paddingLength: CGFloat = CardioSenseLayout.cardPadding
    ) -> some View {
        modifier(ClinicalCardModifier(
            accent: accent,
            elevated: elevated,
            cornerRadius: cornerRadius,
            paddingLength: paddingLength
        ))
    }
}

#Preview("Elevated") {
    Text("Clinical surface")
        .frame(maxWidth: .infinity, alignment: .leading)
        .clinicalCard(accent: CardioSenseTheme.accent(for: .normal), elevated: true)
        .padding()
        .background(CardioSenseTheme.clinicalBackground)
}
