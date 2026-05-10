import Foundation

/// ML prediction payload — matches `shared/prediction.json` from `watch_and_predict.py`.
/// Fetched over HTTP (e.g. `python3 -m http.server 8080`).
struct ECGPrediction: Codable, Equatable {
    let label: String
    let confidence: Double
    let probabilities: ClassProbabilities
    let arrhythmia_detected: Bool
    let heart_rate: Double?
    let hrv: HRVMetrics?
    let sample_rate: Int
    let window_seconds: Int
    let n_windows: Int
    let n_r_peaks: Int

    enum InferenceSurface {
        case normal
        case arrhythmia
        case uncertain
    }

    /// Presentation priority: low confidence overrides label for headline treatment.
    var surface: InferenceSurface {
        if confidence < CardioSenseThresholds.uncertainConfidence { return .uncertain }
        if arrhythmia_detected || label.caseInsensitiveCompare("Arrhythmia") == .orderedSame {
            return .arrhythmia
        }
        return .normal
    }
}

struct ClassProbabilities: Codable, Equatable {
    let normal: Double
    let arrhythmia: Double

    enum CodingKeys: String, CodingKey {
        case normal = "Normal"
        case arrhythmia = "Arrhythmia"
    }
}

struct HRVMetrics: Codable, Equatable {
    let rmssd: Double?
    let sdnn: Double?
    let pnn50: Double?
    let mean_rr_ms: Double?
}

enum CardioSenseThresholds {
    /// Below this confidence, show uncertain / low-confidence treatment.
    static let uncertainConfidence: Double = 0.60
}
