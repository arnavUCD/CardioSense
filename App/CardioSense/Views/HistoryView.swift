import SwiftUI

struct HistoryView: View {
    @Environment(PredictionStore.self) private var store
    @State private var selectedRange: HistoryRange = .hour

    private var scopedAscending: [PredictionHistoryItem] {
        HistoryAnalysis.filter(store.history, within: selectedRange)
    }

    private var summary: HistorySummary {
        HistoryAnalysis.summary(for: store.history, range: selectedRange)
    }

    private var episodes: [HistoryEpisode] {
        HistoryAnalysis.episodes(from: scopedAscending, range: selectedRange)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: CardioSenseLayout.sectionSpacing) {
                    HistoryRangeChips(selection: $selectedRange)

                    if scopedAscending.isEmpty {
                        emptyState
                    } else {
                        HistorySummaryCard(
                            summary: summary,
                            rangeTitle: selectedRange.title
                        )

                        SectionLabel(title: "Events")
                        episodeList
                    }
                }
                .padding(.horizontal, CardioSenseLayout.horizontalPadding)
                .padding(.top, 8)
                .padding(.bottom, 36)
                .frame(maxWidth: 560)
                .frame(maxWidth: .infinity)
            }
            .scrollIndicators(.hidden)
            .background(CardioSenseTheme.clinicalBackground.ignoresSafeArea())
            .navigationTitle("History")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
            .animation(.easeInOut(duration: 0.25), value: selectedRange)
        }
    }

    private var episodeList: some View {
        // Newest-first ordering from HistoryAnalysis.episodes; "first in range"
        // means the oldest episode (last in the array).
        let oldestID = episodes.last?.id
        return LazyVStack(spacing: 12) {
            ForEach(episodes) { episode in
                HistoryEpisodeRow(
                    episode: episode,
                    isFirstInRange: episode.id == oldestID
                )
                .clinicalCard(
                    accent: CardioSenseTheme.accent(for: episode.surface),
                    elevated: false,
                    cornerRadius: CardioSenseLayout.cornerCard,
                    padding: 16
                )
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "clock.arrow.circlepath")
                .font(.system(size: 36))
                .foregroundStyle(.tertiary)
            Text("No readings in this window")
                .font(.headline)
                .foregroundStyle(.secondary)
            Text("Try a longer time range or wait for new readings.")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
    }
}

#Preview {
    HistoryView()
        .environment(PredictionStore())
}
