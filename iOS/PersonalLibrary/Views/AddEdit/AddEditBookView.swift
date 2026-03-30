import SwiftUI

// MARK: - Mode

enum AddEditMode {
    case add
    case edit(Book)
}

// MARK: - View

struct AddEditBookView: View {
    @EnvironmentObject var vm: LibraryViewModel
    @Environment(\.dismiss) private var dismiss

    let mode: AddEditMode
    let prefill: BookLookupResult?   // from barcode scanner

    // Form fields
    @State private var title    = ""
    @State private var author   = ""
    @State private var genre    = ""
    @State private var tagsText = ""
    @State private var status   = "Want to Read"
    @State private var rating   = 0
    @State private var notes    = ""
    @State private var generateBlurb = false

    // Manual lookup state (add mode only)
    @State private var isLookingUp     = false
    @State private var lookupError: String?

    // Submission state
    @State private var isSubmitting  = false
    @State private var submitError: String?

    // MARK: - Body

    var body: some View {
        NavigationStack {
            Form {
                Section("Book Info") {
                    TextField("Title *", text: $title)
                        .autocorrectionDisabled()
                    TextField("Author *", text: $author)
                        .autocorrectionDisabled()
                    TextField("Genre", text: $genre)
                    TextField("Tags (comma-separated)", text: $tagsText)
                        .autocorrectionDisabled()
                        .autocapitalization(.none)
                }

                Section("Status & Rating") {
                    Picker("Status", selection: $status) {
                        ForEach(Book.validStatuses, id: \.self) { Text($0) }
                    }
                    HStack {
                        Text("Rating")
                        Spacer()
                        StarRatingPicker(rating: $rating)
                    }
                }

                Section("Notes") {
                    TextEditor(text: $notes)
                        .frame(minHeight: 80)
                }

                if case .add = mode {
                    Section {
                        Toggle("Generate AI blurb", isOn: $generateBlurb)
                            .tint(.accentColor)
                    } footer: {
                        Text("Requires Ollama running on the server.")
                    }

                    Section {
                        Button {
                            Task { await lookupByTitleAuthor() }
                        } label: {
                            HStack {
                                Image(systemName: "magnifyingglass")
                                Text("Look up metadata online")
                                Spacer()
                                if isLookingUp { ProgressView() }
                            }
                        }
                        .disabled(title.isEmpty || isLookingUp)
                    } footer: {
                        if let e = lookupError {
                            Text(e).foregroundStyle(.red)
                        }
                    }
                }

                if let e = submitError {
                    Section {
                        Text(e)
                            .foregroundStyle(.red)
                            .font(.callout)
                    }
                }
            }
            .navigationTitle(navigationTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await submit() }
                    }
                    .fontWeight(.semibold)
                    .disabled(title.trimmingCharacters(in: .whitespaces).isEmpty
                              || author.trimmingCharacters(in: .whitespaces).isEmpty
                              || isSubmitting)
                }
            }
            .overlay {
                if isSubmitting {
                    ZStack {
                        Color.black.opacity(0.25).ignoresSafeArea()
                        ProgressView("Saving…")
                            .padding()
                            .background(.regularMaterial)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }
            }
        }
        .onAppear { populateFields() }
    }

    // MARK: - Helpers

    private var navigationTitle: String {
        switch mode {
        case .add:  return "Add Book"
        case .edit: return "Edit Book"
        }
    }

    private func populateFields() {
        switch mode {
        case .edit(let book):
            title    = book.title
            author   = book.author
            genre    = book.genre.lowercased() == "n/a" ? "" : book.genre
            tagsText = book.tags.joined(separator: ", ")
            status   = book.status
            rating   = book.rating
            notes    = book.notes

        case .add:
            if let p = prefill {
                // Pre-fill from barcode lookup
                title  = p.title
                author = p.author
                genre  = p.genre.lowercased() == "n/a" ? "" : p.genre
                // Use description as a starting note only if it's short enough
                if let desc = p.description, !desc.isEmpty && desc.count < 300 {
                    notes = desc
                }
            }
        }
    }

    private func lookupByTitleAuthor() async {
        isLookingUp = true
        lookupError = nil
        defer { isLookingUp = false }
        do {
            let result = try await vm.lookupTitleAuthor(
                title: title,
                author: author.isEmpty ? "" : author
            )
            // Only fill fields that are still empty
            if author.isEmpty  { author = result.author }
            if genre.isEmpty   { genre  = result.genre.lowercased() == "n/a" ? "" : result.genre }
            if let desc = result.description, notes.isEmpty && !desc.isEmpty && desc.count < 300 {
                notes = desc
            }
        } catch {
            lookupError = error.localizedDescription
        }
    }

    private func submit() async {
        isSubmitting = true
        submitError  = nil
        defer { isSubmitting = false }

        let tags = tagsText
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
            .filter { !$0.isEmpty }

        do {
            switch mode {
            case .add:
                let req = AddBookRequest(
                    title:  title.trimmingCharacters(in: .whitespaces),
                    author: author.trimmingCharacters(in: .whitespaces),
                    genre:  genre.trimmingCharacters(in: .whitespaces).isEmpty ? "n/a" : genre,
                    tags:   tags,
                    status: status,
                    rating: rating,
                    notes:  notes,
                    generateAiBlurb: generateBlurb
                )
                try await vm.addBook(req)

            case .edit(let book):
                let req = UpdateBookRequest(
                    title:  title.trimmingCharacters(in: .whitespaces),
                    author: author.trimmingCharacters(in: .whitespaces),
                    status: status,
                    rating: rating,
                    genre:  genre.trimmingCharacters(in: .whitespaces).isEmpty ? "n/a" : genre,
                    tags:   tags,
                    notes:  notes
                )
                try await vm.updateBook(book, with: req)
            }
            dismiss()
        } catch {
            submitError = error.localizedDescription
        }
    }
}
