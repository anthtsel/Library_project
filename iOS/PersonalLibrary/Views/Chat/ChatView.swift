import SwiftUI

struct ChatView: View {
    @State private var messages: [ChatMessage] = []
    @State private var inputText  = ""
    @State private var isWaiting  = false
    @State private var errorBanner: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // ── Message list ─────────────────────────────────────
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 10) {
                            if messages.isEmpty {
                                welcomeMessage
                            }
                            ForEach(messages) { msg in
                                ChatBubble(message: msg)
                                    .id(msg.id)
                            }
                            if isWaiting {
                                TypingIndicator()
                                    .id("typing")
                            }
                        }
                        .padding()
                    }
                    .onChange(of: messages.count) {
                        withAnimation(.easeOut(duration: 0.2)) {
                            if isWaiting {
                                proxy.scrollTo("typing", anchor: .bottom)
                            } else if let last = messages.last {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                    .onChange(of: isWaiting) {
                        if isWaiting {
                            withAnimation { proxy.scrollTo("typing", anchor: .bottom) }
                        }
                    }
                }

                // ── Error banner ─────────────────────────────────────
                if let error = errorBanner {
                    HStack {
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.red)
                        Spacer()
                        Button { errorBanner = nil } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 6)
                    .background(Color(.systemBackground))
                }

                Divider()

                // ── Input bar ────────────────────────────────────────
                HStack(alignment: .bottom, spacing: 10) {
                    TextField("Ask about your library…", text: $inputText, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                        .lineLimit(1...5)

                    Button {
                        Task { await sendMessage() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundStyle(
                                inputText.trimmingCharacters(in: .whitespaces).isEmpty || isWaiting
                                ? Color.secondary
                                : Color.accentColor
                            )
                    }
                    .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty || isWaiting)
                }
                .padding(.horizontal)
                .padding(.vertical, 10)
                .background(Color(.systemBackground))
            }
            .navigationTitle("AI Librarian")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Clear") { messages = [] }
                        .disabled(messages.isEmpty)
                }
            }
        }
    }

    // MARK: - Send

    private func sendMessage() async {
        let text = inputText.trimmingCharacters(in: .whitespaces)
        guard !text.isEmpty else { return }
        inputText = ""
        errorBanner = nil

        let userMsg = ChatMessage(role: "user", content: text)
        messages.append(userMsg)
        isWaiting = true

        defer { isWaiting = false }

        do {
            // Pass history up to (but not including) the message just appended
            let history = Array(messages.dropLast().suffix(20))
            let reply = try await APIService.shared.chat(message: text, history: history)
            messages.append(ChatMessage(role: "assistant", content: reply))
        } catch APIServiceError.httpError(503, _) {
            errorBanner = "AI Librarian is offline. Start Ollama on your server."
            messages.removeLast()
        } catch {
            errorBanner = error.localizedDescription
            messages.removeLast()
        }
    }

    // MARK: - Welcome

    private var welcomeMessage: some View {
        VStack(spacing: 12) {
            Image(systemName: "books.vertical.circle")
                .font(.system(size: 44))
                .foregroundStyle(.secondary)
            Text("Ask me anything about your library.")
                .font(.headline)
            Text("Try: "What should I read next?" or "How many Sci-Fi books have I finished?"")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
    }
}

// MARK: - Chat bubble

private struct ChatBubble: View {
    let message: ChatMessage

    private var isUser: Bool { message.role == "user" }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 50) }

            Text(message.content)
                .font(.callout)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(isUser ? Color.accentColor : Color(.secondarySystemBackground))
                .foregroundStyle(isUser ? .white : .primary)
                .clipShape(
                    RoundedRectangle(cornerRadius: 18)
                        .offset(
                            x: isUser ?  8 : -8,
                            y: isUser ? -4 :  4
                        )
                )
                // Slightly sharper corner on the "tail" side
                .clipShape(RoundedRectangle(cornerRadius: 18))

            if !isUser { Spacer(minLength: 50) }
        }
    }
}

// MARK: - Typing indicator

private struct TypingIndicator: View {
    @State private var phase = 0

    var body: some View {
        HStack(spacing: 5) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(Color.secondary)
                    .frame(width: 7, height: 7)
                    .scaleEffect(phase == i ? 1.4 : 1.0)
                    .animation(.easeInOut(duration: 0.3), value: phase)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .task {
            while !Task.isCancelled {
                for i in 0..<3 {
                    phase = i
                    try? await Task.sleep(nanoseconds: 300_000_000)
                }
            }
        }
    }
}
