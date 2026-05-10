import Foundation

enum SamplePredictions {
    static let normalJSON = """
    {
      "label": "Normal",
      "confidence": 1.00,
      "probabilities": {
        "Normal": 1.00,
        "Arrhythmia": 0.00
      },
      "arrhythmia_detected": false,
      "heart_rate": 67.0,
      "hrv": {
        "rmssd": 28.4,
        "sdnn": 41.2,
        "pnn50": 0.12,
        "mean_rr_ms": 895.0
      },
      "sample_rate": 250,
      "window_seconds": 10,
      "n_windows": 5,
      "n_r_peaks": 33
    }
    """

    static let arrhythmiaJSON = """
    {
      "label": "Arrhythmia",
      "confidence": 0.96,
      "probabilities": {
        "Normal": 0.04,
        "Arrhythmia": 0.96
      },
      "arrhythmia_detected": true,
      "heart_rate": 115.9,
      "hrv": {
        "rmssd": 121.1,
        "sdnn": 102.7,
        "pnn50": 0.59,
        "mean_rr_ms": 517.5
      },
      "sample_rate": 250,
      "window_seconds": 10,
      "n_windows": 5,
      "n_r_peaks": 58
    }
    """

    /// Low-confidence sample for uncertain UI (still valid schema).
    static let uncertainJSON = """
    {
      "label": "Arrhythmia",
      "confidence": 0.42,
      "probabilities": {
        "Normal": 0.58,
        "Arrhythmia": 0.42
      },
      "arrhythmia_detected": true,
      "heart_rate": null,
      "hrv": {
        "rmssd": null,
        "sdnn": null,
        "pnn50": null,
        "mean_rr_ms": null
      },
      "sample_rate": 250,
      "window_seconds": 10,
      "n_windows": 3,
      "n_r_peaks": 12
    }
    """

    static let normal: ECGPrediction = decode(normalJSON)!
    static let arrhythmia: ECGPrediction = decode(arrhythmiaJSON)!
    static let uncertain: ECGPrediction = decode(uncertainJSON)!

    static func decode(_ string: String) -> ECGPrediction? {
        guard let data = string.data(using: .utf8) else { return nil }
        let decoder = JSONDecoder()
        return try? decoder.decode(ECGPrediction.self, from: data)
    }
}
