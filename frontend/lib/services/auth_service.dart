import '../core/api_client.dart';
import '../models/user.dart';

/// What login/signup return: the access token, plus a refresh token only
/// when "Keep me logged in" was ticked.
typedef LoginTokens = ({String accessToken, String? refreshToken});

/// Talks to the backend's /auth endpoints. Mirrors backend/app/api/auth.py.
class AuthApiService {
  final ApiClient client;

  AuthApiService(this.client);

  Future<List<String>> getSecurityQuestions() async {
    final json = await client.get('/auth/security-questions');
    return (json['questions'] as List<dynamic>).cast<String>();
  }

  /// The caller (AuthProvider) is responsible for storing the tokens and
  /// setting client.authToken.
  Future<LoginTokens> signup({
    required String email,
    required String password,
    required String securityQuestion1,
    required String securityAnswer1,
    required String securityQuestion2,
    required String securityAnswer2,
    required bool rememberMe,
    String? deviceName,
  }) async {
    final json = await client.post('/auth/signup', {
      'email': email,
      'password': password,
      'security_question_1': securityQuestion1,
      'security_answer_1': securityAnswer1,
      'security_question_2': securityQuestion2,
      'security_answer_2': securityAnswer2,
      'remember_me': rememberMe,
      'device_name': deviceName,
    });
    return _tokens(json);
  }

  Future<LoginTokens> login({
    required String email,
    required String password,
    required bool rememberMe,
    String? deviceName,
  }) async {
    final json = await client.post('/auth/login', {
      'email': email,
      'password': password,
      'remember_me': rememberMe,
      'device_name': deviceName,
    });
    return _tokens(json);
  }

  /// Swaps a remembered device's refresh token for a new access token.
  /// Throws ApiException(401) if the device was logged out or unused too long.
  Future<String> refresh(String refreshToken) async {
    final json = await client.post(ApiClient.refreshPath, {'refresh_token': refreshToken});
    return json['access_token'] as String;
  }

  /// Tells the server to forget this remembered device.
  Future<void> logout(String refreshToken) => client.post('/auth/logout', {'refresh_token': refreshToken});

  LoginTokens _tokens(dynamic json) => (
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String?,
      );

  Future<AppUser> getCurrentUser() async {
    final json = await client.get('/auth/me');
    return AppUser.fromJson(json as Map<String, dynamic>);
  }

  /// Returns (question_1, question_2) for the given email.
  Future<(String, String)> getForgotPasswordQuestions(String email) async {
    final json = await client.post('/auth/forgot-password/questions', {'email': email});
    return (json['security_question_1'] as String, json['security_question_2'] as String);
  }

  Future<String> resetPassword({
    required String email,
    required String securityAnswer1,
    required String securityAnswer2,
    required String newPassword,
  }) async {
    final json = await client.post('/auth/forgot-password/reset', {
      'email': email,
      'security_answer_1': securityAnswer1,
      'security_answer_2': securityAnswer2,
      'new_password': newPassword,
    });
    return json['access_token'] as String;
  }
}
