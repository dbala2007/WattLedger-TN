import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/api_client.dart';
import '../models/user.dart';
import '../services/auth_service.dart';

/// Holds the logged-in user (if any) and the login tokens, and keeps both
/// in sync with [ApiClient.authToken] so every other provider's requests
/// are automatically authenticated.
///
/// "Keep me logged in on this device":
/// - Ticked: the server also returns a long-lived refresh token. Both
///   tokens are saved with flutter_secure_storage (Windows Credential
///   Manager on desktop, Android Keystore on mobile, encrypted browser
///   storage on web). When the short-lived access token expires - at app
///   start or in the middle of using the app - it is silently renewed
///   with the refresh token, so the password is never asked for again
///   until the user logs out (or doesn't use the app for ~6 months).
/// - Not ticked: nothing is saved, so closing the app logs the user out.
class AuthProvider extends ChangeNotifier {
  static const _accessTokenKey = 'wattledger_access_token';
  static const _refreshTokenKey = 'wattledger_refresh_token';

  final ApiClient _client;
  final AuthApiService _service;
  final _storage = const FlutterSecureStorage();

  AuthProvider(ApiClient client) : _client = client, _service = AuthApiService(client) {
    _client.onAccessTokenExpired = _renewAccessToken;
  }

  AppUser? _currentUser;
  bool _bootstrapping = true;
  String? _pendingWelcomeMessage;

  /// Only set when this device is remembered.
  String? _refreshToken;

  /// If several requests hit an expired token at the same moment, they
  /// all wait for this one renewal instead of each starting their own.
  Future<bool>? _renewalInProgress;

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

  /// A short label the server stores with a remembered device
  /// (e.g. "Windows", "Android", "Web").
  static String get _deviceName {
    if (kIsWeb) return 'Web';
    final name = defaultTargetPlatform.name; // e.g. "windows", "android"
    return name[0].toUpperCase() + name.substring(1);
  }

  /// Call once at app startup: restores a remembered login, if any, so the
  /// user isn't asked to log in again every time they open the app.
  Future<void> bootstrap() async {
    try {
      final accessToken = await _storage.read(key: _accessTokenKey);
      _refreshToken = await _storage.read(key: _refreshTokenKey);
      if (accessToken == null && _refreshToken == null) return;

      _client.authToken = accessToken;
      // No saved access token but a refresh token: renew first. (With an
      // expired access token, ApiClient renews automatically on the 401.)
      if (accessToken == null && !await _renewAccessToken()) return;

      _currentUser = await _service.getCurrentUser();
    } on ApiException catch (e) {
      // 401 = the saved login is no longer valid - forget it. Anything
      // else (e.g. a server error) keeps it for the next start.
      if (e.statusCode == 401) await _forgetSavedLogin();
      _client.authToken = null;
    } catch (_) {
      // Offline or server unreachable: keep the saved login so the next
      // start (with a connection) still works without the password.
      _client.authToken = null;
    } finally {
      _bootstrapping = false;
      notifyListeners();
    }
  }

  Future<void> login({required String email, required String password, required bool rememberMe}) async {
    final tokens = await _service.login(
      email: email,
      password: password,
      rememberMe: rememberMe,
      deviceName: rememberMe ? _deviceName : null,
    );
    await _applyTokens(tokens, (email) => 'Welcome back, $email!');
  }

  Future<List<String>> getSecurityQuestions() => _service.getSecurityQuestions();

  Future<void> signup({
    required String email,
    required String password,
    required String securityQuestion1,
    required String securityAnswer1,
    required String securityQuestion2,
    required String securityAnswer2,
    required bool rememberMe,
  }) async {
    final tokens = await _service.signup(
      email: email,
      password: password,
      securityQuestion1: securityQuestion1,
      securityAnswer1: securityAnswer1,
      securityQuestion2: securityQuestion2,
      securityAnswer2: securityAnswer2,
      rememberMe: rememberMe,
      deviceName: rememberMe ? _deviceName : null,
    );
    await _applyTokens(tokens, (email) => 'Account created! Welcome, $email.');
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
    // Resetting also logs the user back in, for this session only - the
    // server has just signed every remembered device out, this one too.
    await _applyTokens((accessToken: token, refreshToken: null),
        (email) => 'Password reset. Welcome back, $email!');
  }

  Future<void> _applyTokens(LoginTokens tokens, String Function(String email) buildWelcomeMessage) async {
    _refreshToken = tokens.refreshToken;
    if (tokens.refreshToken != null) {
      await _storage.write(key: _accessTokenKey, value: tokens.accessToken);
      await _storage.write(key: _refreshTokenKey, value: tokens.refreshToken);
    } else {
      // Not remembered: make sure no older saved login lingers either.
      await _forgetSavedLogin();
    }
    _client.authToken = tokens.accessToken;
    _currentUser = await _service.getCurrentUser();
    _pendingWelcomeMessage = buildWelcomeMessage(_currentUser!.email);
    notifyListeners();
  }

  /// Gets a new access token using the refresh token. Returns false (and
  /// logs out, if the server rejected it) when that isn't possible.
  /// Called by ApiClient whenever a request fails with 401.
  Future<bool> _renewAccessToken() {
    final refreshToken = _refreshToken;
    if (refreshToken == null) return Future.value(false);

    return _renewalInProgress ??= () async {
      try {
        final accessToken = await _service.refresh(refreshToken);
        _client.authToken = accessToken;
        await _storage.write(key: _accessTokenKey, value: accessToken);
        return true;
      } on ApiException catch (e) {
        if (e.statusCode == 401) {
          // Logged out from elsewhere, password reset, or unused too long.
          await _forgetSavedLogin();
          _client.authToken = null;
          _currentUser = null;
          notifyListeners();
        }
        return false;
      } catch (_) {
        return false; // offline - try again on the next request
      } finally {
        _renewalInProgress = null;
      }
    }();
  }

  Future<void> _forgetSavedLogin() async {
    _refreshToken = null;
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }

  Future<void> logout() async {
    final refreshToken = _refreshToken;
    await _forgetSavedLogin();
    _client.authToken = null;
    _currentUser = null;
    notifyListeners();

    // Tell the server to forget this device too. Best effort: if it fails
    // (e.g. offline), the saved token is already gone from this device.
    if (refreshToken != null) {
      try {
        await _service.logout(refreshToken);
      } catch (_) {}
    }
  }
}
