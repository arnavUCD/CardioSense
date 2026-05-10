import Foundation
import Observation

/// Fetches `prediction.json` from a configurable HTTP URL (local `python3 -m http.server` demo).
@MainActor
@Observable
final class PredictionService {
    private let store: PredictionStore

    /// Default endpoint. The Mac's LAN IP works for both Simulator and a
    /// physical iPhone on the same Wi-Fi (loopback would only work in the
    /// Simulator). Edit in the app's connection bar if your Mac IP differs.
    static let defaultPredictionURLString = "http://100.73.14.37:8080/shared/prediction.json"

    private enum Keys {
        // Bumped to .v2 so users who already saved the old 127.0.0.1 default
        // automatically pick up the new LAN-IP default.
        static let url = "cardiosense.predictionURL.v2"
        static let autoRefresh = "cardiosense.autoRefreshPrediction.v2"
    }

    private let session: URLSession
    private var autoRefreshTask: Task<Void, Never>?

    /// User-editable endpoint (persisted).
    var predictionURLString: String {
        didSet {
            UserDefaults.standard.set(predictionURLString, forKey: Keys.url)
        }
    }

    /// Poll every 2s when enabled (persisted).
    var autoRefreshEnabled: Bool {
        didSet {
            UserDefaults.standard.set(autoRefreshEnabled, forKey: Keys.autoRefresh)
            configureAutoRefresh()
        }
    }

    private(set) var isFetching = false

    /// One-line status for the dashboard (subtle, clinical).
    private(set) var connectionLine: String = "Waiting for model output"

    private(set) var lastSuccessfulFetchAt: Date?

    init(store: PredictionStore) {
        self.store = store
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 15
        config.timeoutIntervalForResource = 20
        self.session = URLSession(configuration: config)

        self.predictionURLString =
            UserDefaults.standard.string(forKey: Keys.url) ?? Self.defaultPredictionURLString
        // Default ON so the dashboard starts polling the Mac immediately.
        self.autoRefreshEnabled =
            UserDefaults.standard.object(forKey: Keys.autoRefresh) as? Bool ?? true
        // `didSet` does not run for initial property assignments — start polling if enabled.
        configureAutoRefresh()
    }

    func configureAutoRefresh() {
        autoRefreshTask?.cancel()
        autoRefreshTask = nil
        guard autoRefreshEnabled else { return }
        autoRefreshTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.refresh()
                try? await Task.sleep(nanoseconds: 2_000_000_000)
            }
        }
    }

    /// Manual refresh (toolbar / button).
    func refresh() async {
        guard let url = URL(string: predictionURLString.trimmingCharacters(in: .whitespacesAndNewlines)),
              url.scheme == "http" || url.scheme == "https"
        else {
            connectionLine = "Waiting for model output"
            return
        }

        isFetching = true
        defer { isFetching = false }

        do {
            let (data, response) = try await session.data(from: url)
            guard let http = response as? HTTPURLResponse else {
                connectionLine = "Waiting for model output"
                return
            }
            guard (200 ... 299).contains(http.statusCode) else {
                connectionLine = "Waiting for model output"
                return
            }
            let prediction = try JSONDecoder().decode(ECGPrediction.self, from: data)
            store.applyFromRemoteFetch(prediction)
            let now = Date()
            lastSuccessfulFetchAt = now
            let tf = DateFormatter()
            tf.timeStyle = .short
            tf.dateStyle = .none
            connectionLine = "Live · \(tf.string(from: now))"
        } catch {
            connectionLine = "Waiting for model output"
        }
    }
}
