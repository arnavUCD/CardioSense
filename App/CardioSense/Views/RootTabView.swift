import SwiftUI

struct RootTabView: View {
    var body: some View {
        TabView {
            MainMonitorView()
                .tabItem {
                    Label("Monitor", systemImage: "waveform.path.ecg")
                }

            DetailsView()
                .tabItem {
                    Label("Reference", systemImage: "book.closed")
                }

            HistoryView()
                .tabItem {
                    Label("History", systemImage: "clock.arrow.circlepath")
                }

            ImportTestView()
                .tabItem {
                    Label("Samples", systemImage: "testtube.2")
                }
        }
        .tint(Color("AccentNormal"))
        .toolbarBackground(.ultraThinMaterial, for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
    }
}

#Preview {
    let store = PredictionStore()
    RootTabView()
        .environment(store)
        .environment(PredictionService(store: store))
}
