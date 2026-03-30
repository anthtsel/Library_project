import SwiftUI

struct LibraryView: View {
    @EnvironmentObject var vm: LibraryViewModel
    @State private var showingAddSheet = false
    @State private var selectedBook: Book?

    private let allStatuses = ["All"] + Book.validStatuses

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // ── Status filter pills ──────────────────────────────────
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(allStatuses, id: \.self) { status in
                            let isSelected = (status == "All" && vm.selectedStatus == nil)
                                          || (status == vm.selectedStatus)
                            Button(status) {
                                vm.selectedStatus = (status == "All") ? nil : status
                            }
                            .font(.subheadline)
                            .fontWeight(isSelected ? .semibold : .regular)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 7)
                            .background(isSelected ? Color.accentColor : Color(.secondarySystemBackground))
                            .foregroundStyle(isSelected ? .white : .primary)
                            .clipShape(Capsule())
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                }

                Divider()

                // ── Book list ────────────────────────────────────────────
                if vm.isLoading && vm.books.isEmpty {
                    ProgressView("Loading library…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if vm.displayedBooks.isEmpty {
                    ContentUnavailableViewCompat(
                        title: vm.books.isEmpty ? "Library is Empty" : "No Results",
                        systemImage: "books.vertical",
                        description: vm.books.isEmpty
                            ? "Tap + to add your first book."
                            : "No books match your current filter."
                    )
                } else {
                    List(vm.displayedBooks) { book in
                        BookRowView(book: book)
                            .contentShape(Rectangle())
                            .onTapGesture { selectedBook = book }
                            .listRowSeparator(.hidden)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                    }
                    .listStyle(.plain)
                    .refreshable { await vm.loadBooks() }
                }
            }
            .navigationTitle("My Library")
            .navigationBarTitleDisplayMode(.large)
            .searchable(text: $vm.searchQuery, prompt: "Title, author, genre, tag…")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Picker("Sort by", selection: $vm.sortOrder) {
                            ForEach(LibraryViewModel.SortOrder.allCases) { order in
                                Text(order.rawValue).tag(order)
                            }
                        }
                    } label: {
                        Image(systemName: "arrow.up.arrow.down.circle")
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showingAddSheet = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .font(.title3)
                    }
                }
            }
            .sheet(isPresented: $showingAddSheet) {
                AddEditBookView(mode: .add, prefill: nil)
            }
            .sheet(item: $selectedBook) { book in
                BookDetailView(book: book)
            }
        }
    }
}

// MARK: - Book row

struct BookRowView: View {
    let book: Book

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Spine colour swatch
            RoundedRectangle(cornerRadius: 3)
                .fill(spineColor(for: book.title))
                .frame(width: 5, height: 60)

            VStack(alignment: .leading, spacing: 4) {
                Text(book.title)
                    .font(.headline)
                    .lineLimit(2)
                Text(book.author)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                HStack(spacing: 6) {
                    StatusBadge(status: book.status)
                    if !book.genre.isEmpty && book.genre.lowercased() != "n/a" {
                        Text(book.genre)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    if book.rating > 0 {
                        StarRatingView(rating: book.rating)
                    }
                }
            }
        }
        .padding(.vertical, 6)
    }

    private func spineColor(for title: String) -> Color {
        let colors: [Color] = [.blue, .indigo, .teal, .cyan, .mint, .purple, .pink, .orange]
        let hash = title.unicodeScalars.reduce(0) { ($0 &* 31) &+ Int($1.value) }
        return colors[abs(hash) % colors.count]
    }
}

// MARK: - iOS 16 fallback for ContentUnavailableView (iOS 17+)

struct ContentUnavailableViewCompat: View {
    let title: String
    let systemImage: String
    let description: String

    var body: some View {
        if #available(iOS 17, *) {
            ContentUnavailableView(title,
                                   systemImage: systemImage,
                                   description: Text(description))
        } else {
            VStack(spacing: 12) {
                Image(systemName: systemImage)
                    .font(.system(size: 48))
                    .foregroundStyle(.secondary)
                Text(title)
                    .font(.headline)
                Text(description)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding()
        }
    }
}
