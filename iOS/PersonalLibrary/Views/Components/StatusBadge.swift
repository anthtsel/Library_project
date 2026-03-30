import SwiftUI

struct StatusBadge: View {
    let status: String

    var body: some View {
        Text(status)
            .font(.caption2)
            .fontWeight(.semibold)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(color.opacity(0.18))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }

    var color: Color {
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

struct StarRatingView: View {
    let rating: Int

    var body: some View {
        HStack(spacing: 2) {
            ForEach(1...5, id: \.self) { i in
                Image(systemName: i <= rating ? "star.fill" : "star")
                    .font(.caption)
                    .foregroundStyle(i <= rating ? .yellow : .secondary)
            }
        }
    }
}

struct StarRatingPicker: View {
    @Binding var rating: Int

    var body: some View {
        HStack(spacing: 4) {
            ForEach(1...5, id: \.self) { i in
                Image(systemName: i <= rating ? "star.fill" : "star")
                    .font(.title3)
                    .foregroundStyle(i <= rating ? .yellow : .secondary)
                    .onTapGesture {
                        rating = (rating == i) ? 0 : i   // tap same star to clear
                    }
            }
            if rating > 0 {
                Button("Clear") { rating = 0 }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.leading, 4)
            }
        }
    }
}
