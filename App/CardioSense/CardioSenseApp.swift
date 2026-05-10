import SwiftUI

/// Holds a single shared store and fetch service so networking targets the same dashboard state.
@MainActor
final class AppSession {
    let store: PredictionStore
    let predictionService: PredictionService

    init() {
        let store = PredictionStore()
        self.store = store
        self.predictionService = PredictionService(store: store)
    }
}

@main
struct CardioSenseApp: App {
    @State private var session = AppSession()

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environment(session.store)
                .environment(session.predictionService)
        }
    }
}
