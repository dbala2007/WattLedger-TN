/// App-wide configuration.
///
/// Kept in one place (not scattered through the UI) so the backend URL can
/// be changed without hunting through every screen - similar in spirit to
/// the backend's own environment-variable-based Settings class.
class AppConfig {
  /// The FastAPI backend's base URL.
  ///
  /// Defaults to 127.0.0.1, which is correct when the client runs on the
  /// SAME machine as the backend (Windows desktop, and Chrome during web
  /// development). A phone or tablet is a separate device on the network,
  /// so 127.0.0.1 on Android would mean "the phone itself", not this PC -
  /// it needs the PC's actual LAN IP instead (see README.md's "Mobile
  /// (Android) - same Wi-Fi" section for how to find it and pass it in).
  ///
  /// Overridden at build/run time with, e.g.:
  ///   `flutter run -d DEVICE --dart-define=API_BASE_URL=http://192.168.1.44:8001`
  /// rather than hardcoded here, since the right value depends on whichever
  /// network the developer's machine is on that day, not on the code.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8001',
  );
}
