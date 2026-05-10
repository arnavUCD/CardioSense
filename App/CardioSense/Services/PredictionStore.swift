import Foundation
import Observation

struct PredictionHistoryItem: Identifiable, Equatable {
    let id: UUID
    let recordedAt: Date
    let prediction: ECGPrediction
}

@Observable
final class PredictionStore {
    var currentPrediction: ECGPrediction
    /// Updated whenever a new prediction is applied (sample, decode, or future API).
    var lastAnalyzedAt: Date
    /// Most recent first.
    var history: [PredictionHistoryItem]

    private let decoder = JSONDecoder()

    init(
        initial: ECGPrediction = SamplePredictions.normal,
        seedHistory: [PredictionHistoryItem]? = nil,
        lastAnalyzedAt: Date = Date()
    ) {
        self.currentPrediction = initial
        self.lastAnalyzedAt = lastAnalyzedAt
        self.history = seedHistory ?? PredictionStore.mockHistorySeed()
    }

    func load(from data: Data) throws {
        let p = try decoder.decode(ECGPrediction.self, from: data)
        apply(p)
    }

    func applySample(_ prediction: ECGPrediction) {
        apply(prediction)
    }

    /// Replace monitor reading and append history (dedupe identical consecutive applies optional — skipped for hackathon simplicity).
    func apply(_ prediction: ECGPrediction) {
        currentPrediction = prediction
        lastAnalyzedAt = Date()
        history.insert(
            PredictionHistoryItem(id: UUID(), recordedAt: Date(), prediction: prediction),
            at: 0
        )
        if history.count > 1000 {
            history.removeLast(history.count - 1000)
        }
    }

    /// Updates the dashboard from HTTP polling without flooding history when JSON is unchanged.
    func applyFromRemoteFetch(_ prediction: ECGPrediction) {
        let changed = prediction != currentPrediction
        currentPrediction = prediction
        if changed {
            lastAnalyzedAt = Date()
            history.insert(
                PredictionHistoryItem(id: UUID(), recordedAt: Date(), prediction: prediction),
                at: 0
            )
            if history.count > 50 {
                history.removeLast(history.count - 50)
            }
        }
    }

    /// Plausible 30-day demo history: normal readings sampled at varying density,
    /// with 6 arrhythmia episodes scattered across the window so the History
    /// time-range filters all show meaningful content.
    static func mockHistorySeed() -> [PredictionHistoryItem] {
        let now = Date()
        var items: [PredictionHistoryItem] = []

        // (secondsAgo from now, episode duration)
        let arrhythmiaEpisodes: [(secondsAgo: TimeInterval, durationSec: TimeInterval)] = [
            (15 * 60, 4 * 60),       // 15 min ago — visible in "Last hour"
            (3 * 3600, 6 * 60),      //  3 h  ago — "Last day"
            (22 * 3600, 3 * 60),     // 22 h  ago — "Last day"
            (3 * 86400, 8 * 60),     //  3 d  ago — "Last week"
            (9 * 86400, 5 * 60),     //  9 d  ago — "Last month"
            (21 * 86400, 12 * 60),   // 21 d  ago — "Last month"
        ]

        func insideAnyEpisode(_ secAgo: TimeInterval) -> Bool {
            for ep in arrhythmiaEpisodes {
                let half = ep.durationSec / 2
                if secAgo >= ep.secondsAgo - half && secAgo <= ep.secondsAgo + half {
                    return true
                }
            }
            return false
        }

        // Normal readings sampled at increasing intervals further back in time.
        let bands: [(start: TimeInterval, end: TimeInterval, step: TimeInterval)] = [
            (30, 600, 30),                         // last 10 min, every 30s
            (600, 3600, 5 * 60),                   // 10–60 min, every 5 min
            (3600, 86400, 30 * 60),                // 1–24 h, every 30 min
            (86400, 7 * 86400, 2 * 3600),          // 1–7 d, every 2 h
            (7 * 86400, 30 * 86400, 6 * 3600),     // 7–30 d, every 6 h
        ]

        for band in bands {
            var t = band.start
            while t < band.end {
                if !insideAnyEpisode(t) {
                    items.append(
                        PredictionHistoryItem(
                            id: UUID(),
                            recordedAt: now.addingTimeInterval(-t),
                            prediction: makeMockPrediction(surface: .normal, jitter: t)
                        )
                    )
                }
                t += band.step
            }
        }

        // Dense readings within each arrhythmia episode (every 60s).
        for ep in arrhythmiaEpisodes {
            let half = ep.durationSec / 2
            var t = ep.secondsAgo - half
            let endT = ep.secondsAgo + half
            while t <= endT {
                items.append(
                    PredictionHistoryItem(
                        id: UUID(),
                        recordedAt: now.addingTimeInterval(-t),
                        prediction: makeMockPrediction(surface: .arrhythmia, jitter: t)
                    )
                )
                t += 60
            }
        }

        return items.sorted { $0.recordedAt > $1.recordedAt }
    }

    /// Builds a synthetic ECGPrediction matching the wire schema. Slight HR
    /// variation via `jitter` so the seeded readings don't all look identical.
    private static func makeMockPrediction(
        surface: ECGPrediction.InferenceSurface,
        jitter: TimeInterval
    ) -> ECGPrediction {
        let isArrhythmia = (surface == .arrhythmia)
        let baseHR: Double = isArrhythmia ? 112.0 : 68.0
        let variation = sin(jitter / 600.0) * 6.0
        let hr = baseHR + variation

        let confidence: Double = isArrhythmia ? 0.93 : 0.97
        let normalProb = isArrhythmia ? 1.0 - confidence : confidence
        let arrProb = 1.0 - normalProb

        return ECGPrediction(
            label: isArrhythmia ? "Arrhythmia" : "Normal",
            confidence: confidence,
            probabilities: ClassProbabilities(normal: normalProb, arrhythmia: arrProb),
            arrhythmia_detected: isArrhythmia,
            heart_rate: hr,
            hrv: HRVMetrics(
                rmssd: isArrhythmia ? 121.0 : 28.0,
                sdnn: isArrhythmia ? 102.0 : 41.0,
                pnn50: isArrhythmia ? 0.59 : 0.12,
                mean_rr_ms: 60_000.0 / hr
            ),
            sample_rate: 250,
            window_seconds: 10,
            n_windows: 5,
            n_r_peaks: isArrhythmia ? 19 : 11
        )
    }
}
