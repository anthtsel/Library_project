import Foundation

// MARK: - Core book model

struct Book: Identifiable, Hashable {
    let id: Int
    var title: String
    var author: String
    var genre: String
    var tags: [String]
    var status: String
    var rating: Int
    var blurb: String
    var notes: String
    let event: String
    let timestamp: String
    var lastUpdated: String

    static let validStatuses = ["Want to Read", "Reading", "Completed", "Reread", "DNF"]
}

extension Book: Codable {
    enum CodingKeys: String, CodingKey {
        case id, title, author, genre, tags, status, rating, blurb, notes, event, timestamp
        case lastUpdated = "last_updated"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id          = try c.decode(Int.self,    forKey: .id)
        title       = try c.decode(String.self, forKey: .title)
        author      = try c.decode(String.self, forKey: .author)
        genre       = try c.decode(String.self, forKey: .genre)
        tags        = try c.decode([String].self, forKey: .tags)
        status      = try c.decode(String.self, forKey: .status)
        rating      = try c.decode(Int.self,    forKey: .rating)
        blurb       = (try? c.decode(String.self, forKey: .blurb))      ?? ""
        notes       = (try? c.decode(String.self, forKey: .notes))      ?? ""
        event       = try c.decode(String.self, forKey: .event)
        timestamp   = try c.decode(String.self, forKey: .timestamp)
        lastUpdated = (try? c.decode(String.self, forKey: .lastUpdated)) ?? ""
    }
}

// MARK: - API request bodies

struct AddBookRequest: Encodable {
    var title: String
    var author: String
    var genre: String = "n/a"
    var tags: [String] = []
    var status: String = "Want to Read"
    var rating: Int = 0
    var notes: String = ""
    var generateAiBlurb: Bool = false

    enum CodingKeys: String, CodingKey {
        case title, author, genre, tags, status, rating, notes
        case generateAiBlurb = "generate_ai_blurb"
    }
}

struct UpdateBookRequest: Encodable {
    var title: String?
    var author: String?
    var status: String?
    var rating: Int?
    var genre: String?
    var tags: [String]?
    var notes: String?
    var blurb: String?
}

// MARK: - Barcode lookup result

struct BookLookupResult: Decodable {
    let title: String
    let author: String
    let genre: String
    let description: String?
    let pageCount: Int?
    let publishedDate: String?
    let coverURL: String?
    let isbn: String
    let source: String
    let averageRating: Double?
    let ratingsCount: Int?

    enum CodingKeys: String, CodingKey {
        case title, author, genre, description, isbn, source
        case pageCount      = "page_count"
        case publishedDate  = "published_date"
        case coverURL       = "cover_url"
        case averageRating  = "average_rating"
        case ratingsCount   = "ratings_count"
    }
}

// MARK: - Stats

struct Stats: Decodable {
    let total: Int
    let byStatus: [String: Int]?
    let addedThisMonth: Int?
    let addedThisYear: Int?
    let averageRating: Double?
    let topAuthor: NameCount?
    let topGenre: NameCount?
    let completedCount: Int?

    enum CodingKeys: String, CodingKey {
        case total
        case byStatus       = "by_status"
        case addedThisMonth = "added_this_month"
        case addedThisYear  = "added_this_year"
        case averageRating  = "average_rating"
        case topAuthor      = "top_author"
        case topGenre       = "top_genre"
        case completedCount = "completed_count"
    }
}

struct NameCount: Decodable {
    let name: String
    let count: Int
}

// MARK: - Chat

struct ChatMessage: Identifiable {
    let id: UUID
    let role: String   // "user" or "assistant"
    let content: String

    init(role: String, content: String) {
        self.id = UUID()
        self.role = role
        self.content = content
    }
}

// Wire-format only — strips the local UUID before sending
private struct WireChatMessage: Encodable {
    let role: String
    let content: String
}

struct ChatRequest: Encodable {
    let message: String
    let history: [WireChatMessage]

    init(message: String, history: [ChatMessage]) {
        self.message = message
        self.history = history.map { WireChatMessage(role: $0.role, content: $0.content) }
    }
}

struct ChatResponse: Decodable {
    let reply: String
}

// MARK: - Error envelope from API

struct APIErrorDetail: Decodable {
    let detail: String
}
