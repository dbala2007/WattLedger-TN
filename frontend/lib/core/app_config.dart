/// App-wide configuration.
///
/// Kept in one place (not scattered through the UI) so the backend URL can
/// be changed without hunting through every screen - similar in spirit to
/// the backend's own environment-variable-based Settings class.
class AppConfig {
  /// The FastAPI backend's base URL. Both the backend and this Flutter web
  /// build run on the same development machine during Phase 1, so
  /// 127.0.0.1 is correct for local development.
  static const String apiBaseUrl = 'http://127.0.0.1:8001';
}
