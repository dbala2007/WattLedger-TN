import '../core/api_client.dart';
import '../models/user.dart';

/// Talks to the backend's /auth endpoints. Mirrors backend/app/api/auth.py.
class AuthApiService {
  final ApiClient client;

  AuthApiService(this.client);

  Future<List<String>> getSecurityQuestions() async {
    final json = await client.get('/auth/security-questions');
    return (json['questions'] as List<dynamic>).cast<String>();
  }

  /// Returns the access token. The caller (AuthProvider) is responsible for
  /// storing it and setting client.authToken.
  Future<String> signup({
    required String email,
    required String password,
    required String securityQuestion1,
    required String securityAnswer1,
    required String securityQuestion2,
    required String securityAnswer2,
  }) async {
    final json = await client.post('/auth/signup', {
      'email': email,
      'password': password,
      'security_question_1': securityQuestion1,
      'security_answer_1': securityAnswer1,
      'security_question_2': securityQuestion2,
      'security_answer_2': securityAnswer2,
    });
    return json['access_token'] as String;
  }

  Future<String> login({required String email, required String password}) async {
    final json = await client.post('/auth/login', {'email': email, 'password': password});
    return json['access_token'] as String;
  }

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
