import SwiftUI
import Charts

struct StatsView: View {
    @EnvironmentObject var vm: LibraryViewModel

    var body: some View {
        NavigationStack {
            Group {
                if let stats = vm.stats {
                    statsContent(stats)
                } else if vm.isLoading {
                    ProgressView("Loading stats…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ContentUnavailableViewCompat(
                        title: "No Stats Yet",
                        systemImage: "chart.bar",
                        description: "Add some books to see your reading stats."
                    )
                }
            }
            .navigationTitle("Stats")
            .refreshable { await vm.loadStats() }
            .task { if vm.stats == nil { await vm.loadStats() } }
        }
    }

    // MARK: - Stats content

    @ViewBuilder
    private func statsContent(_ stats: Stats) -> some View {
        ScrollView {
            VStack(spacing: 20) {

                // ── Top stat cards ────────────────────────────────────
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    StatCard(title: "Total Books",    value: "\(stats.total)",            icon: "books.vertical.fill",  color: .blue)
                    StatCard(title: "Completed",      value: "\(stats.completedCount ?? 0)", icon: "checkmark.seal.fill", color: .green)
                    StatCard(title: "Added This Year", value: "\(stats.addedThisYear ?? 0)",  icon: "calendar",            color: .orange)
                    if let avg = stats.averageRating {
                        StatCard(title: "Avg Rating",  value: String(format: "%.1f ★", avg), icon: "star.fill",           color: .yellow)
                    }
                }
                .padding(.horizontal)

                // ── Status breakdown chart ────────────────────────────
                if let byStatus = stats.byStatus, !byStatus.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("By Status")
                            .font(.headline)
                            .padding(.horizontal)

                        Chart(byStatus.sorted(by: { $0.value > $1.value }), id: \.key) { item in
                            BarMark(
                                x: .value("Count", item.value),
                                y: .value("Status", item.key)
                            )
                            .foregroundStyle(statusColor(item.key))
                            .annotation(position: .trailing) {
                                Text("\(item.value)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .chartYAxis {
                            AxisMarks { _ in
                                AxisValueLabel()
                            }
                        }
                        .frame(height: CGFloat(byStatus.count) * 44)
                        .padding(.horizontal)
                    }
                    .padding(.vertical, 12)
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal)
                }

                // ── Top author / genre ────────────────────────────────
                if stats.topAuthor != nil || stats.topGenre != nil {
                    HStack(spacing: 12) {
                        if let top = stats.topAuthor {
                            TopCard(label: "Top Author", name: top.name, count: top.count, icon: "person.fill")
                        }
                        if let top = stats.topGenre {
                            TopCard(label: "Top Genre", name: top.name, count: top.count, icon: "tag.fill")
                        }
                    }
                    .padding(.horizontal)
                }
            }
            .padding(.vertical)
        }
    }

    // MARK: - Status color

    private func statusColor(_ status: String) -> Color {
        switch status {
        case "Completed":    return .green
        case "Reading":      return .blue
        case "Want to Read": return .orange
        case "Reread":       return .purple
        case "DNF":          return .red
        default:             return .secondary
        }
    }
}

// MARK: - Sub-views

private struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)
                Spacer()
            }
            Text(value)
                .font(.title2)
                .fontWeight(.bold)
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

private struct TopCard: View {
    let label: String
    let name: String
    let count: Int
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(.accentColor)
                Text(label)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Text(name)
                .font(.subheadline)
                .fontWeight(.semibold)
                .lineLimit(2)
            Text("\(count) book\(count == 1 ? "" : "s")")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
