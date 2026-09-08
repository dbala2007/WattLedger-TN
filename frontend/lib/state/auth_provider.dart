import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/api_client.dart';
import '../models/user.dart';
import '../services/auth_service.dart';

/// Holds the logged-in user (if any) and the login token, and keeps both in
/// sync with [ApiClient.authToken] so every other provider's requests are
/// automatically authenticated. The token is persisted with
/// flutter_secure_storage, which uses Windows Credential Manager on desktop
/// and browser-side encrypted storage on web - same API, same behavior, so
/// "stay logged in between restarts" works identically on both platforms.
class AuthProvider extends ChangeNotifier {
  static const _tokenStorageKey = 'wattledger_access_token';

  final ApiClient _client;
  final AuthApiService _service;
  final _storage = const FlutterSecureStorage();

  AuthProvider(ApiClient client) : _client = client, _service = AuthApiService(client);

  AppUser? _currentUser;
  bool _bootstrapping = true;
  String? _pendingWelcomeMessage;

  AppUser? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null;
  bool get isBootstrapping => _bootstrapping;

  /// One-shot welcome message set by an explicit login/signup/reset (not by
  /// [bootstrap]'s silent restore-from-storage). AppShell reads and clears
  /// this right after it's first shown, so it appears exactly once per
  /// sign-in rather than every time AppShell rebuilds.
  String? consumeWelcomeMessage() {
    final message = _pendingWelcomeMessage;
    _pendingWelcomeMessage = null;
    return message;
  }

  /// Call once at app startup: restores a previously-saved login, if any,
  /// so the user isn't asked to log in again every time they open the app.
  Future<void> bootstrap() async {
    try {
      final token = await _storage.read(key: _tokenStorageKey);
      if (token != null) {
        _client.authToken = token;
        try {
          _currentUser = await _service.getCurrentUser();
        } catch (_) {
          // Saved token is expired/invalid - fall back to logged-out.
          await _storage.delete(key: _tokenStorageKey);
          _client.authToken = null;
        }
      }
    } finally {
      _bootstrapping = false;
      notifyListeners();
    }
  }

  Future<void> login({required String email, required String password}) async {
    final token = await _service.login(email: email, password: password);
    await _applyToken(token, (email) => 'Welcome back, $email!');
  }

  Future<List<String>> getSecurityQuestions() => _service.getSecurityQuestions();

  Future<void> signup({
    required String email,
    required String password,
    required String securityQuestion1,
    required String securityAnswer1,
    required String securityQuestion2,
    required String securityAnswer2,
  }) async {
    final token = await _service.signup(
      email: email,
      password: password,
      securityQuestion1: securityQuestion1,
      securityAnswer1: securityAnswer1,
      securityQuestion2: securityQuestion2,
      securityAnswer2: securityAnswer2,
    );
    await _applyToken(token, (email) => 'Account created! Welcome, $email.');
  }

  Future<(String, String)> getForgotPasswordQuestions(String email) =>
      _service.getForgotPasswordQuestions(email);

  Future<void> resetPassword({
    required String email,
    required String securityAnswer1,
    required String securityAnswer2,
    required String newPassword,
  }) async {
    final token = await _service.resetPassword(
      email: email,
      securityAnswer1: securityAnswer1,
      securityAnswer2: securityAnswer2,
      newPassword: newPassword,
    );
    // resetting also logs the user back in
    await _applyToken(token, (email) => 'Password reset. Welcome back, $email!');
  }

  Future<void> _applyToken(String token, String Function(String email) buildWelcomeMessage) async {
    await _storage.write(key: _tokenStorageKey, value: token);
    _client.authToken = token;
    _currentUser = await _service.getCurrentUser();
    _pendingWelcomeMessage = buildWelcomeMessage(_currentUser!.email);
    notifyListeners();
  }

  Future<void> logout() async {
    await _storage.delete(key: _tokenStorageKey);
    _client.authToken = null;
    _currentUser = null;
    notifyListeners();
  }
}
