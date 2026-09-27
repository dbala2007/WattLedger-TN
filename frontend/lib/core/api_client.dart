import 'dart:convert';

import 'package:http/http.dart' as http;

import 'app_config.dart';

/// Thrown when the backend returns a non-2xx response. Carries the backend's
/// own error message (from the {"detail": ...} shape our FastAPI error
/// handlers always return - see backend/app/main.py) so the UI can show the
/// same validation message the user would see in /docs.
class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

/// A small wrapper around package:http that handles the JSON
/// encode/decode + error-message extraction every API call needs, so
/// individual service classes (MeterService, ReadingService, ...) only
/// have to say *what* endpoint to call, not how to parse the response.
class ApiClient {
  final String baseUrl;

  ApiClient({this.baseUrl = AppConfig.apiBaseUrl});

  // Set by AuthProvider after login/signup/startup-restore, and cleared on
  // logout. Every request below attaches it (when present) so web and
  // Windows authenticate identically - they're both just callers of this
  // same ApiClient. A plain mutable field is enough here: only one user is
  // ever logged in per app instance.
  String? authToken;

  /// Set by AuthProvider when this device is remembered ("Keep me logged
  /// in"). Called when a request comes back 401 because the access token
  /// has expired: it should fetch and set a fresh [authToken] and return
  /// true, or return false if the device can't be refreshed. The request
  /// is then retried once with the new token.
  Future<bool> Function()? onAccessTokenExpired;

  static const refreshPath = '/auth/refresh';

  Map<String, String> get _jsonHeaders => {
        'Content-Type': 'application/json',
        if (authToken != null) 'Authorization': 'Bearer $authToken',
      };

  Uri _uri(String path, [Map<String, String>? query]) {
    final uri = Uri.parse('$baseUrl$path');
    if (query == null || query.isEmpty) return uri;
    return uri.replace(queryParameters: query);
  }

  Future<dynamic> get(String path, {Map<String, String>? query}) =>
      _send(path, () => http.get(_uri(path, query), headers: _jsonHeaders));

  Future<dynamic> post(String path, Map<String, dynamic> body) =>
      _send(path, () => http.post(_uri(path), headers: _jsonHeaders, body: jsonEncode(body)));

  Future<dynamic> patch(String path, Map<String, dynamic> body) =>
      _send(path, () => http.patch(_uri(path), headers: _jsonHeaders, body: jsonEncode(body)));

  /// Full replace of a resource - unlike [patch], fields left out are cleared.
  Future<dynamic> put(String path, Map<String, dynamic> body) =>
      _send(path, () => http.put(_uri(path), headers: _jsonHeaders, body: jsonEncode(body)));

  Future<void> delete(String path) => _send(path, () => http.delete(_uri(path), headers: _jsonHeaders));

  /// Runs [request]; if it fails with 401 while logged in, asks
  /// [onAccessTokenExpired] for a new token and runs it once more.
  /// [request] is a function (not a ready-made request) so the retry
  /// re-reads [_jsonHeaders] and picks up the new token.
  Future<dynamic> _send(String path, Future<http.Response> Function() request) async {
    var response = await request();
    final refresher = onAccessTokenExpired;
    // Never for the refresh call itself - a rejected refresh must not
    // trigger another refresh (that would loop forever).
    final canRefresh = path != refreshPath && authToken != null && refresher != null;
    if (response.statusCode == 401 && canRefresh && await refresher()) {
      response = await request();
    }
    return _handle(response);
  }

  dynamic _handle(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }

    String message = 'Request failed (HTTP ${response.statusCode})';
    try {
      final decoded = jsonDecode(response.body);
      final detail = decoded is Map ? decoded['detail'] : null;
      if (detail is String) {
        message = detail;
      } else if (detail is List) {
        message = detail.join('\n');
      }
    } catch (_) {
      // Response body wasn't JSON - fall back to the generic message above.
    }
    throw ApiException(response.statusCode, message);
  }
}
