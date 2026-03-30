import SwiftUI

struct ContentView: View {
    @StateObject private var vm = LibraryViewModel()

    var body: some View {
        TabView {
            LibraryView()
                .tabItem { Label("Library", systemImage: "books.vertical") }

            ScannerView()
                .tabItem { Label("Scan", systemImage: "barcode.viewfinder") }

            StatsView()
                .tabItem { Label("Stats", systemImage: "chart.bar.fill") }

            ChatView()
                .tabItem { Label("Librarian", systemImage: "bubble.left.and.bubble.right") }
        }
        .environmentObject(vm)
        .task { await vm.loadBooks() }
        .alert("Error", isPresented: vm.hasError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(vm.errorMessage ?? "")
        }
    }
}
