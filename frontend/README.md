# WattLedger TN - Frontend

Flutter client. See the [project README](../README.md) and
[`PRP.md`](../PRP.md) / [`CLAUDE.md`](../CLAUDE.md) at the repository root
for product context and working rules.

## Setup

Requires the Flutter SDK (built against 3.44.4). On this machine it's
installed at `F:\flutter_windows_3.44.4-stable\flutter` and added to the
user PATH.

```bash
flutter pub get
```

## Run

The backend (`../backend`) must be running first - see its README.

```bash
flutter run -d windows    # native desktop app
flutter run -d chrome     # or in a browser
```

Windows desktop needs Visual Studio Build Tools with the "Desktop
development with C++" workload - installed at `F:\VisualStudioBuildTools`
on this machine (via the silent installer: `vs_buildtools.exe --quiet --wait
--norestart --installPath F:\VisualStudioBuildTools --add
Microsoft.VisualStudio.Workload.VCTools --includeRecommended`). The same
Dart/Flutter code runs on both targets unchanged (PRP.md section 8).

## Run tests / analyze

```bash
flutter analyze
flutter test
```

## Folder structure

| Folder | Purpose |
|---|---|
| `lib/core/` | API client, app config, formatters, JSON parsing helpers |
| `lib/models/` | Plain Dart classes mirroring the backend's API schemas (hand-written `fromJson`, no code generation) |
| `lib/services/` | One class per backend router (`MeterApiService`, `ReadingApiService`, ...) - HTTP calls only |
| `lib/state/` | `ChangeNotifier` providers holding app state (selected meter, readings, billing, tariffs) |
| `lib/screens/` | One file per screen |
| `lib/widgets/` | Shared widgets (app shell/navigation, meter selector, loading/error view) |

## Architecture

```text
Screens (UI only)
  -> Providers (app state, calls services, notifies UI)
    -> Services (HTTP calls to the backend)
      -> Models (JSON <-> Dart objects)
```

All business logic (balance calculation, validation, billing) lives in the
backend, never here - this UI only displays what the API returns and sends
back what the user typed. This is required by CLAUDE.md section 8 so the
same backend can later serve a web and mobile build without rewriting rules.

## Configuration

The backend base URL is a constant in `lib/core/app_config.dart`
(`http://127.0.0.1:8000` for local development). There's no environment
variable mechanism for this yet - change the constant directly if needed.
