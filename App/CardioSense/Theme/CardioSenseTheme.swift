import SwiftUI

enum CardioSenseLayout {
    /// Primary hero / summary panels.
    static let cornerHero: CGFloat = 22
    /// Standard elevated cards.
    static let cornerCard: CGFloat = 16
    /// Nested chips and inner metrics.
    static let cornerNested: CGFloat = 12
    /// Vertical rhythm between major blocks (WHOOP-like breathing room).
    static let sectionSpacing: CGFloat = 28
    /// Horizontal screen inset.
    static let horizontalPadding: CGFloat = 20
    /// Inner card padding.
    static let cardPadding: CGFloat = 18
}

enum CardioSenseTheme {
    static let clinicalBackground = Color("ClinicalBackground")
    static let cardBackground = Color("CardSurface")

    static func accent(for surface: ECGPrediction.InferenceSurface) -> Color {
        switch surface {
        case .normal: return Color("AccentNormal")
        case .arrhythmia: return Color("AccentArrhythmia")
        case .uncertain: return Color("AccentUncertain")
        }
    }

    static func title(for surface: ECGPrediction.InferenceSurface) -> String {
        switch surface {
        case .normal: return "Normal Rhythm"
        case .arrhythmia: return "Arrhythmia Detected"
        case .uncertain: return "Uncertain Result"
        }
    }

    static func headlineSubtitle(
        prediction: ECGPrediction,
        surface: ECGPrediction.InferenceSurface
    ) -> String {
        switch surface {
        case .uncertain:
            return "Low confidence result. Signal may require another reading."
        case .arrhythmia:
            return "Automated classification differs from the expected normal pattern for this window."
        case .normal:
            return "Pattern consistent with normal sinus rhythm for this window."
        }
    }

    /// Soft shadow for stacked panels (color-scheme aware).
    static func cardShadow(elevated: Bool, colorScheme: ColorScheme) -> (color: Color, radius: CGFloat, y: CGFloat) {
        switch colorScheme {
        case .dark:
            return (Color.black.opacity(elevated ? 0.55 : 0.35), elevated ? 22 : 14, elevated ? 12 : 8)
        case .light:
            fallthrough
        @unknown default:
            return (Color.black.opacity(elevated ? 0.11 : 0.06), elevated ? 20 : 12, elevated ? 10 : 6)
        }
    }
}
