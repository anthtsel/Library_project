import SwiftUI
import AVFoundation

// MARK: - Camera preview (UIViewRepresentable)

/// Hosts the AVCaptureVideoPreviewLayer inside a SwiftUI view.
private final class CameraPreviewUIView: UIView {
    override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
    var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
}

private struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> CameraPreviewUIView {
        let view = CameraPreviewUIView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: CameraPreviewUIView, context: Context) {}
}

// MARK: - Barcode coordinator

@MainActor
private final class BarcodeScanCoordinator: NSObject, AVCaptureMetadataOutputObjectsDelegate {
    var onCode: (String) -> Void
    private var lastCode: String?
    private var lastTime: Date = .distantPast

    init(onCode: @escaping (String) -> Void) {
        self.onCode = onCode
    }

    nonisolated func metadataOutput(
        _ output: AVCaptureMetadataOutput,
        didOutput metadataObjects: [AVMetadataObject],
        from connection: AVCaptureConnection
    ) {
        guard
            let obj  = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
            let code = obj.stringValue
        else { return }

        let now = Date()
        Task { @MainActor in
            // Debounce: ignore the same code within 3 seconds
            if code == self.lastCode && now.timeIntervalSince(self.lastTime) < 3 { return }
            self.lastCode = code
            self.lastTime = now
            self.onCode(code)
        }
    }

    func resetDebounce() {
        lastCode = nil
    }
}

// MARK: - Scanner view

struct ScannerView: View {
    @EnvironmentObject var vm: LibraryViewModel

    @State private var session       = AVCaptureSession()
    @State private var coordinator: BarcodeScanCoordinator?
    @State private var isRunning        = false
    @State private var permissionDenied = false
    @State private var sessionConfigured = false

    @State private var isLookingUp   = false
    @State private var lookupResult: BookLookupResult?
    @State private var lookupError: String?
    @State private var showingAddSheet = false

    var body: some View {
        NavigationStack {
            ZStack {
                if permissionDenied {
                    cameraPermissionDeniedView
                } else {
                    // Live preview
                    CameraPreviewView(session: session)
                        .ignoresSafeArea()

                    // Viewfinder overlay
                    ViewfinderOverlay()

                    // Status overlays
                    VStack {
                        Spacer()
                        statusBanner
                            .padding(.bottom, 40)
                    }
                }
            }
            .navigationTitle("Scan ISBN")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear { setupSession() }
            .onDisappear {
                Task.detached(priority: .userInitiated) { [session] in
                    session.stopRunning()
                }
            }
            .sheet(isPresented: $showingAddSheet) {
                AddEditBookView(mode: .add, prefill: lookupResult)
                    .onDisappear {
                        // Re-arm scanner after the add sheet closes
                        coordinator?.resetDebounce()
                        if !session.isRunning {
                            Task.detached(priority: .userInitiated) { [session] in session.startRunning() }
                        }
                    }
            }
        }
    }

    // MARK: - Setup

    private func setupSession() {
        guard !sessionConfigured else { return }
        sessionConfigured = true
        Task.detached(priority: .userInitiated) {
            let status = AVCaptureDevice.authorizationStatus(for: .video)
            switch status {
            case .authorized:
                await configureSession()
            case .notDetermined:
                let granted = await AVCaptureDevice.requestAccess(for: .video)
                if granted { await configureSession() }
                else { await MainActor.run { permissionDenied = true } }
            default:
                await MainActor.run { permissionDenied = true }
            }
        }
    }

    @MainActor
    private func configureSession() async {
        let coord = BarcodeScanCoordinator { isbn in
            handleCode(isbn)
        }
        coordinator = coord

        // Capture the existing session so CameraPreviewView keeps the same reference
        let capturedSession = self.session

        await Task.detached(priority: .userInitiated) {
            guard
                let device = AVCaptureDevice.default(for: .video),
                let input  = try? AVCaptureDeviceInput(device: device),
                capturedSession.canAddInput(input)
            else { return }

            capturedSession.beginConfiguration()
            capturedSession.addInput(input)

            let metaOutput = AVCaptureMetadataOutput()
            if capturedSession.canAddOutput(metaOutput) {
                capturedSession.addOutput(metaOutput)
                // Use main queue so delegate callbacks reach the @MainActor coordinator safely
                metaOutput.setMetadataObjectsDelegate(coord, queue: .main)
                // Support EAN-13 (ISBN-13), EAN-8, UPC-E
                metaOutput.metadataObjectTypes = [.ean13, .ean8, .upce]
            }
            capturedSession.commitConfiguration()
            capturedSession.startRunning()

            await MainActor.run {
                self.isRunning = true
            }
        }.value
    }

    // MARK: - Handle scanned code

    private func handleCode(_ code: String) {
        guard !isLookingUp && !showingAddSheet else { return }
        isLookingUp = true
        lookupError = nil

        Task {
            defer { isLookingUp = false }
            do {
                lookupResult = try await vm.lookupISBN(code)
                showingAddSheet = true
                // Pause scanning while the sheet is open
                Task.detached(priority: .userInitiated) { [session] in session.stopRunning() }
            } catch APIServiceError.httpError(404, _) {
                lookupError = "ISBN \(code) not found. You can still add the book manually."
            } catch APIServiceError.httpError(504, _) {
                lookupError = "Lookup timed out. Check your internet connection."
            } catch {
                lookupError = error.localizedDescription
            }
        }
    }

    // MARK: - Sub-views

    @ViewBuilder
    private var statusBanner: some View {
        if isLookingUp {
            Label("Looking up…", systemImage: "magnifyingglass")
                .padding(.horizontal, 20).padding(.vertical, 12)
                .background(.ultraThinMaterial)
                .clipShape(Capsule())
        } else if let error = lookupError {
            Text(error)
                .font(.footnote)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 20).padding(.vertical, 12)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .padding(.horizontal, 32)
        } else {
            Label("Point camera at a book's barcode", systemImage: "barcode")
                .font(.callout)
                .padding(.horizontal, 20).padding(.vertical, 12)
                .background(.ultraThinMaterial)
                .clipShape(Capsule())
        }
    }

    private var cameraPermissionDeniedView: some View {
        VStack(spacing: 20) {
            Image(systemName: "camera.slash")
                .font(.system(size: 52))
                .foregroundStyle(.secondary)
            Text("Camera Access Required")
                .font(.title3)
                .fontWeight(.semibold)
            Text("Allow camera access in Settings to scan ISBN barcodes.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(32)
    }
}

// MARK: - Viewfinder overlay

private struct ViewfinderOverlay: View {
    var body: some View {
        GeometryReader { geo in
            let size = min(geo.size.width, geo.size.height) * 0.65
            let x    = (geo.size.width  - size) / 2
            let y    = (geo.size.height - size) / 2

            ZStack {
                // Dim everything outside the viewfinder
                Color.black.opacity(0.45)
                    .mask(
                        Rectangle()
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .frame(width: size, height: size / 2)
                                    .blendMode(.destinationOut)
                            )
                            .compositingGroup()
                    )

                // Corner brackets
                CornerBrackets(size: size, height: size / 2)
                    .position(x: geo.size.width / 2, y: geo.size.height / 2)
            }
        }
        .ignoresSafeArea()
    }
}

private struct CornerBrackets: View {
    let size: CGFloat
    let height: CGFloat
    private let len: CGFloat = 22
    private let thick: CGFloat = 3

    var body: some View {
        ZStack {
            ForEach(corners, id: \.0) { (_, xSign, ySign) in
                Path { p in
                    let ox = xSign * size / 2
                    let oy = ySign * height / 2
                    p.move(to: CGPoint(x: ox - xSign * len, y: oy))
                    p.addLine(to: CGPoint(x: ox, y: oy))
                    p.addLine(to: CGPoint(x: ox, y: oy - ySign * len))
                }
                .stroke(Color.white, lineWidth: thick)
            }
        }
    }

    private var corners: [(String, CGFloat, CGFloat)] {
        [("TL", -1, -1), ("TR", 1, -1), ("BL", -1, 1), ("BR", 1, 1)]
    }
}
