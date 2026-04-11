# Personal Library — iOS App

Native SwiftUI app for your personal bookshelf. Talks to the FastAPI backend in this repo.

## Requirements

- **Mac** with Xcode 15+ (iOS development requires macOS + Xcode)
- **iOS 16+** device or simulator
- FastAPI backend running (`uvicorn api:app --reload` from project root)

---

## Setup in Xcode

### 1. Create the Xcode project

1. Open Xcode → **File → New → Project**
2. Choose **iOS → App**
3. Set:
   - **Product Name**: `PersonalLibrary`
   - **Team**: your Apple ID / developer team
   - **Interface**: SwiftUI
   - **Language**: Swift
   - Uncheck "Include Tests" for now
4. Save the project **inside** `iOS/` so the path is `iOS/PersonalLibrary.xcodeproj`

### 2. Replace the generated files

Delete Xcode's generated `ContentView.swift` and `PersonalLibraryApp.swift`, then drag the entire `iOS/PersonalLibrary/` folder into the Xcode project navigator. Make sure **"Copy items if needed"** is **unchecked** — the files are already in the right place.

Your project navigator should look like:

```
PersonalLibrary/
├── PersonalLibraryApp.swift
├── Config.swift
├── Info.plist
├── Models/
│   └── Book.swift
├── Services/
│   └── APIService.swift
├── ViewModels/
│   └── LibraryViewModel.swift
└── Views/
    ├── ContentView.swift
    ├── Components/
    │   └── StatusBadge.swift
    ├── Library/
    │   ├── LibraryView.swift
    │   └── BookDetailView.swift
    ├── AddEdit/
    │   └── AddEditBookView.swift
    ├── Scanner/
    │   └── ScannerView.swift
    ├── Stats/
    │   └── StatsView.swift
    └── Chat/
        └── ChatView.swift
```

### 3. Configure the server URL

Open `Config.swift` and set `baseURL` to match where your backend is running:

| Target              | URL                         |
|---------------------|-----------------------------|
| iOS Simulator       | `http://localhost:8000`     |
| Physical device (same WiFi) | `http://192.168.x.x:8000` |
| Cloud (Railway etc) | `https://your-app.railway.app` |

Find your Mac's LAN IP: run `ipconfig getifaddr en0` in Terminal.

### 4. Info.plist — HTTP + camera permissions

The `Info.plist` in this folder has the required entries. In Xcode:

1. Select your project → **Target → Info**
2. Confirm these keys exist (Xcode may merge them from the file automatically):
   - `NSCameraUsageDescription` — "Scan ISBN barcodes…"
   - `NSAppTransportSecurity` → `NSAllowsLocalNetworking` = YES

If your server is at a raw IP (not `.local`), also add:

```
NSAppTransportSecurity
  NSExceptionDomains
    192.168.x.x
      NSExceptionAllowsInsecureHTTPLoads = YES
```

### 5. Build & Run

1. Select your simulator or connected device
2. Press **⌘R**

---

## Features

| Tab | What it does |
|-----|-------------|
| **Library** | Browse all books with status filter pills, search, and sort. Tap a book for details. |
| **Scan** | Point at any book's ISBN barcode — metadata auto-fills from Google Books / Open Library. |
| **Stats** | Reading stats: total, completed, added this year, avg rating, status breakdown chart. |
| **Chat** | Ask the AI Librarian questions about your collection (requires Ollama on the server). |

---

## Physical Device Testing

1. Connect your iPhone via USB
2. Select it as the run destination in Xcode
3. Xcode will prompt you to trust the developer certificate on the device
4. Make sure your Mac and iPhone are on the **same WiFi network**
5. Update `Config.swift` with your Mac's LAN IP

---

## Troubleshooting

**"Could not connect to server"**
- Backend not running → `uvicorn api:app --reload`
- Wrong IP in `Config.swift`
- Firewall blocking port 8000 → `sudo ufw allow 8000` (Linux)

**Scanner shows blank / crashes**
- Camera permission not granted → Settings → Privacy → Camera → PersonalLibrary → ON
- Running on Simulator → the camera is not available in the Simulator; test on a real device

**"AI Librarian is offline"**
- Ollama not running → `ollama serve` on the Mac running the backend
- Model not pulled → `ollama pull gemma4:4b`

**Charts don't appear (iOS 16)**
- `import Charts` requires iOS 16+. The app targets iOS 16 minimum. If building for iOS 15, remove the Charts import and replace `StatsView`'s chart section with a plain list.
