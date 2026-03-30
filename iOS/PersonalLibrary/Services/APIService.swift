import Foundation

// MARK: - Error type

enum APIServiceError: LocalizedError {
    case invalidURL
    case networkError(Error)
    case httpError(Int, String)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid server URL. Check Config.swift."
        case .networkError(let e):
            return "Network error: \(e.localizedDescription)"
        case .httpError(let code, let detail):
            return detail.isEmpty ? "Server error \(code)." : detail
        case .decodingError(let e):
            return "Unexpected response from server: \(e.localizedDescription)"
        }
    }
}

// MARK: - Service

actor APIService {
    static let shared = APIService()

    private let session: URLSession
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 15
        session = URLSession(configuration: config)
    }

    // MARK: - Internal helpers

    private func url(_ path: String, queryItems: [URLQueryItem]? = nil) throws -> URL {
        var components = URLComponents(string: Config.baseURL + path)
        if let queryItems { components?.queryItems = queryItems }
        guard let url = components?.url else { throw APIServiceError.invalidURL }
        return url
    }

    private func fetch<T: Decodable>(
        _ method: String,
        path: String,
        queryItems: [URLQueryItem]? = nil,
        body: (some Encodable)? = nil,
        expectedStatus: Int = 200
    ) async throws -> T {
        var request = URLRequest(url: try url(path, queryItems: queryItems))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let body { request.httpBody = try encoder.encode(body) }

        let (data, response) = try await session.data(for: request)

        guard let http = response as? HTTPURLResponse else {
            throw APIServiceError.networkError(URLError(.badServerResponse))
        }
        guard http.statusCode == expectedStatus else {
            let detail = (try? decoder.decode(APIErrorDetail.self, from: data))?.detail ?? ""
            throw APIServiceError.httpError(http.statusCode, detail)
        }
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIServiceError.decodingError(error)
        }
    }

    /// For DELETE and other void responses (HTTP 204 — no body).
    private func fetchVoid(
        _ method: String,
        path: String
    ) async throws {
        let request = URLRequest(url: try url(path))
        var req = request
        req.httpMethod = method
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else {
            throw APIServiceError.networkError(URLError(.badServerResponse))
        }
        guard (200..<300).contains(http.statusCode) else {
            let detail = (try? decoder.decode(APIErrorDetail.self, from: data))?.detail ?? ""
            throw APIServiceError.httpError(http.statusCode, detail)
        }
    }

    // MARK: - Books

    func fetchBooks(status: String? = nil) async throws -> [Book] {
        var items: [URLQueryItem]?
        if let status { items = [URLQueryItem(name: "status", value: status)] }
        return try await fetch("GET", path: "/books", queryItems: items)
    }

    func addBook(_ req: AddBookRequest) async throws -> Book {
        return try await fetch("POST", path: "/books", body: req, expectedStatus: 201)
    }

    func updateBook(title: String, _ req: UpdateBookRequest) async throws -> Book {
        let encoded = Self.encodePathSegment(title)
        return try await fetch("PATCH", path: "/books/\(encoded)", body: req)
    }

    func deleteBook(title: String) async throws {
        let encoded = Self.encodePathSegment(title)
        try await fetchVoid("DELETE", path: "/books/\(encoded)")
    }

    /// Percent-encodes a single path segment, ensuring `/` is also encoded.
    private static func encodePathSegment(_ s: String) -> String {
        var allowed = CharacterSet.urlPathAllowed
        allowed.remove("/")
        return s.addingPercentEncoding(withAllowedCharacters: allowed) ?? s
    }

    // MARK: - Lookup (barcode / title search)

    func lookupISBN(_ isbn: String) async throws -> BookLookupResult {
        return try await fetch("GET", path: "/books/lookup",
                               queryItems: [URLQueryItem(name: "isbn", value: isbn)])
    }

    func lookupTitleAuthor(title: String, author: String? = nil) async throws -> BookLookupResult {
        var items = [URLQueryItem(name: "title", value: title)]
        if let author { items.append(URLQueryItem(name: "author", value: author)) }
        return try await fetch("GET", path: "/books/lookup", queryItems: items)
    }

    // MARK: - Stats

    func fetchStats() async throws -> Stats {
        return try await fetch("GET", path: "/stats")
    }

    // MARK: - Chat

    func chat(message: String, history: [ChatMessage]) async throws -> String {
        // Truncate history to last 20 messages to stay within Ollama's context window
        let trimmedHistory = Array(history.suffix(20))
        let req = ChatRequest(message: message, history: trimmedHistory)
        let response: ChatResponse = try await fetch("POST", path: "/chat", body: req)
        return response.reply
    }
}
