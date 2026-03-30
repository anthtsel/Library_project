import Foundation
import SwiftUI

@MainActor
final class LibraryViewModel: ObservableObject {

    // MARK: - Published state

    @Published var books: [Book] = []
    @Published var stats: Stats?
    @Published var isLoading = false
    @Published var errorMessage: String?     // non-nil triggers the root error alert

    // Filter / sort state (owned here so views stay thin)
    @Published var selectedStatus: String? = nil    // nil = All
    @Published var searchQuery = ""
    @Published var sortOrder: SortOrder = .dateAdded

    enum SortOrder: String, CaseIterable, Identifiable {
        case dateAdded = "Date Added"
        case title     = "Title"
        case author    = "Author"
        case rating    = "Rating"
        var id: String { rawValue }
    }

    // MARK: - Derived

    var displayedBooks: [Book] {
        var list = books.filter { book in
            if let status = selectedStatus, !status.isEmpty, book.status != status { return false }
            if !searchQuery.isEmpty {
                let hay = "\(book.title) \(book.author) \(book.genre) \(book.tags.joined(separator: " "))".lowercased()
                if !hay.contains(searchQuery.lowercased()) { return false }
            }
            return true
        }
        switch sortOrder {
        case .dateAdded: list.sort { $0.timestamp > $1.timestamp }
        case .title:     list.sort { $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending }
        case .author:    list.sort { $0.author.localizedCaseInsensitiveCompare($1.author) == .orderedAscending }
        case .rating:    list.sort { $0.rating > $1.rating }
        }
        return list
    }

    var hasError: Binding<Bool> {
        Binding(
            get: { self.errorMessage != nil },
            set: { if !$0 { self.errorMessage = nil } }
        )
    }

    // MARK: - Load

    func loadBooks() async {
        isLoading = true
        defer { isLoading = false }
        do {
            books = try await APIService.shared.fetchBooks()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadStats() async {
        do {
            stats = try await APIService.shared.fetchStats()
        } catch {
            // Stats are supplemental — fail silently unless nothing loaded yet
            if stats == nil { errorMessage = error.localizedDescription }
        }
    }

    // MARK: - CRUD

    /// Adds a book and prepends it to the local list. Returns the saved book.
    @discardableResult
    func addBook(_ req: AddBookRequest) async throws -> Book {
        let book = try await APIService.shared.addBook(req)
        books.insert(book, at: 0)
        return book
    }

    /// Updates a book by its current title. Returns the updated book.
    @discardableResult
    func updateBook(_ book: Book, with req: UpdateBookRequest) async throws -> Book {
        let updated = try await APIService.shared.updateBook(title: book.title, req)
        if let idx = books.firstIndex(where: { $0.id == updated.id }) {
            books[idx] = updated
        }
        return updated
    }

    func deleteBook(_ book: Book) async throws {
        try await APIService.shared.deleteBook(title: book.title)
        books.removeAll { $0.id == book.id }
    }

    // MARK: - Lookup (passed through from APIService for scanner)

    func lookupISBN(_ isbn: String) async throws -> BookLookupResult {
        try await APIService.shared.lookupISBN(isbn)
    }

    func lookupTitleAuthor(title: String, author: String) async throws -> BookLookupResult {
        try await APIService.shared.lookupTitleAuthor(title: title, author: author)
    }
}
