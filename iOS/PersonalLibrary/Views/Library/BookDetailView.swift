import SwiftUI

struct BookDetailView: View {
    @EnvironmentObject var vm: LibraryViewModel
    @Environment(\.dismiss) private var dismiss

    // Mutable local copy so the sheet stays live after an edit
    @State private var book: Book
    @State private var showingEditSheet = false
    @State private var showingDeleteConfirm = false
    @State private var errorMessage: String?

    init(book: Book) {
        _book = State(initialValue: book)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {

                    // ── Header ───────────────────────────────────────────
                    VStack(alignment: .leading, spacing: 6) {
                        Text(book.title)
                            .font(.title2)
                            .fontWeight(.bold)
                        Text(book.author)
                            .font(.title3)
                            .foregroundStyle(.secondary)
                            .italic()
                    }

                    // ── Status / Rating row ──────────────────────────────
                    HStack(spacing: 10) {
                        StatusBadge(status: book.status)
                        if book.rating > 0 { StarRatingView(rating: book.rating) }
                        Spacer()
                    }

                    // ── Blurb ────────────────────────────────────────────
                    if !book.blurb.isEmpty {
                        Text(book.blurb)
                            .font(.subheadline)
                            .italic()
                            .foregroundStyle(.secondary)
                            .padding(.vertical, 10)
                            .padding(.horizontal, 14)
                            .background(Color(.secondarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.accentColor.opacity(0.4), lineWidth: 1)
                            )
                    }

                    // ── Metadata grid ────────────────────────────────────
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                        MetaCell(label: "Genre",   value: book.genre.lowercased() == "n/a" ? "—" : book.genre)
                        MetaCell(label: "Added",   value: String(book.timestamp.prefix(10)))
                        if !book.lastUpdated.isEmpty {
                            MetaCell(label: "Updated", value: String(book.lastUpdated.prefix(10)))
                        }
                    }

                    // ── Tags ─────────────────────────────────────────────
                    if !book.tags.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("TAGS")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.secondary)
                            FlowLayout(spacing: 6) {
                                ForEach(book.tags, id: \.self) { tag in
                                    Text(tag)
                                        .font(.caption)
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 4)
                                        .background(Color(.tertiarySystemBackground))
                                        .clipShape(Capsule())
                                        .overlay(Capsule().stroke(Color.secondary.opacity(0.3), lineWidth: 1))
                                }
                            }
                        }
                    }

                    // ── Notes ────────────────────────────────────────────
                    if !book.notes.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("NOTES")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.secondary)
                            Text(book.notes)
                                .font(.subheadline)
                        }
                    }
                }
                .padding()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button("Edit") { showingEditSheet = true }
                        Divider()
                        Button("Delete", role: .destructive) {
                            showingDeleteConfirm = true
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .sheet(isPresented: $showingEditSheet) {
                AddEditBookView(mode: .edit(book), prefill: nil)
                    .onDisappear {
                        // Sync local copy with any updates made in the edit sheet
                        if let updated = vm.books.first(where: { $0.id == book.id }) {
                            book = updated
                        }
                    }
            }
            .confirmationDialog(
                "Delete \"\(book.title)\"?",
                isPresented: $showingDeleteConfirm,
                titleVisibility: .visible
            ) {
                Button("Delete", role: .destructive) {
                    Task {
                        do {
                            try await vm.deleteBook(book)
                            dismiss()
                        } catch {
                            errorMessage = error.localizedDescription
                        }
                    }
                }
            }
            .alert("Error", isPresented: Binding(
                get: { errorMessage != nil },
                set: { if !$0 { errorMessage = nil } }
            )) {
                Button("OK") { errorMessage = nil }
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }
}

// MARK: - Helpers

private struct MetaCell: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(.caption2)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.subheadline)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

/// Simple horizontal flow layout for tags.
private struct FlowLayout: Layout {
    var spacing: CGFloat = 6

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 0
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0, maxY: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > width && x > 0 {
                y += rowHeight + spacing; x = 0; rowHeight = 0
            }
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
            maxY = y + rowHeight
        }
        return CGSize(width: width, height: maxY)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX && x > bounds.minX {
                y += rowHeight + spacing; x = bounds.minX; rowHeight = 0
            }
            subview.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}
