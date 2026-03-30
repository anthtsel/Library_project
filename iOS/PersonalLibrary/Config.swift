import Foundation

enum Config {
    /// Base URL of the FastAPI backend.
    ///
    /// - Simulator: "http://localhost:8000" works fine.
    /// - Physical device: change to your Mac's LAN IP, e.g. "http://192.168.1.42:8000"
    ///   (find it in System Settings → Network, or run `ipconfig getifaddr en0` on the Mac).
    /// - Production: replace with your Railway / Fly.io URL once deployed.
    ///
    /// You can also override at runtime by setting the API_BASE_URL environment variable
    /// in your Xcode scheme (Product → Scheme → Edit Scheme → Run → Arguments).
    static let baseURL: String = {
        ProcessInfo.processInfo.environment["API_BASE_URL"] ?? "http://localhost:8000"
    }()
}
