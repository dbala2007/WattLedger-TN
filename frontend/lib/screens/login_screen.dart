import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../state/auth_provider.dart';
import 'forgot_password_screen.dart';

/// Shown when no valid login is stored (PRP.md Phase 3). One screen toggles
/// between "log in" and "create an account" rather than two separate
/// screens, since most fields involved are identical - signup just adds the
/// two security questions used later for self-service password reset.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _answer1Controller = TextEditingController();
  final _answer2Controller = TextEditingController();

  bool _isSignup = false;
  bool _submitting = false;
  String? _error;

  String? _securityQuestion1;
  String? _securityQuestion2;
  List<String>? _availableQuestions;

  @override
  void initState() {
    super.initState();
    // Fetched once up front (no login required for this endpoint) so the
    // dropdowns are ready the moment someone switches to "sign up".
    context.read<AuthProvider>().getSecurityQuestions().then((questions) {
      if (mounted) setState(() => _availableQuestions = questions);
    }).catchError((_) {
      // If this fails, the dropdowns just show as empty/loading - the user
      // can still switch back to "log in" or retry by reopening the app.
    });
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _answer1Controller.dispose();
    _answer2Controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final authProvider = context.read<AuthProvider>();
      final email = _emailController.text.trim();
      final password = _passwordController.text;
      if (_isSignup) {
        await authProvider.signup(
          email: email,
          password: password,
          securityQuestion1: _securityQuestion1!,
          securityAnswer1: _answer1Controller.text.trim(),
          securityQuestion2: _securityQuestion2!,
          securityAnswer2: _answer2Controller.text.trim(),
        );
      } else {
        await authProvider.login(email: email, password: password);
      }
      // No navigation needed: main.dart watches AuthProvider.isAuthenticated
      // and swaps to AppShell automatically once this completes.
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.bolt, size: 48, color: Theme.of(context).colorScheme.primary),
                  const SizedBox(height: 8),
                  Text(
                    'WattLedger TN',
                    style: Theme.of(context).textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  Text(
                    _isSignup ? 'Create an account' : 'Log in',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _emailController,
                    decoration: const InputDecoration(labelText: 'Email'),
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _passwordController,
                    decoration: const InputDecoration(labelText: 'Password'),
                    obscureText: true,
                    autofillHints: [_isSignup ? AutofillHints.newPassword : AutofillHints.password],
                    onFieldSubmitted: (_) => _submit(),
                    validator: (v) {
                      if (v == null || v.isEmpty) return 'Required';
                      if (_isSignup && v.length < 8) return 'At least 8 characters';
                      return null;
                    },
                  ),
                  if (_isSignup) ..._buildSecurityQuestionFields(),
                  const SizedBox(height: 20),
                  if (_error != null) ...[
                    Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                    const SizedBox(height: 12),
                  ],
                  FilledButton(
                    onPressed: _submitting ? null : _submit,
                    child: _submitting
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                        : Text(_isSignup ? 'Create account' : 'Log in'),
                  ),
                  const SizedBox(height: 8),
                  if (!_isSignup)
                    TextButton(
                      onPressed: _submitting
                          ? null
                          : () => Navigator.of(context).push(
                                MaterialPageRoute(builder: (_) => const ForgotPasswordScreen()),
                              ),
                      child: const Text('Forgot password?'),
                    ),
                  TextButton(
                    onPressed: _submitting
                        ? null
                        : () => setState(() {
                              _isSignup = !_isSignup;
                              _error = null;
                            }),
                    child: Text(_isSignup ? 'Already have an account? Log in' : "Don't have an account? Sign up"),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildSecurityQuestionFields() {
    final questions = _availableQuestions;
    return [
      const SizedBox(height: 20),
      Text(
        'Security questions',
        style: Theme.of(context).textTheme.titleSmall,
      ),
      const Text(
        "Used later if you forget your password - there's no email reset yet.",
        style: TextStyle(fontSize: 12),
      ),
      const SizedBox(height: 8),
      if (questions == null)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
        )
      else ...[
        DropdownButtonFormField<String>(
          initialValue: _securityQuestion1,
          decoration: const InputDecoration(labelText: 'Security question 1'),
          items: questions.map((q) => DropdownMenuItem(value: q, child: Text(q))).toList(),
          onChanged: (v) => setState(() => _securityQuestion1 = v),
          validator: (v) => v == null ? 'Required' : null,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _answer1Controller,
          decoration: const InputDecoration(labelText: 'Answer 1'),
          validator: (v) => (v == null || v.trim().length < 2) ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          initialValue: _securityQuestion2,
          decoration: const InputDecoration(labelText: 'Security question 2'),
          items: questions.map((q) => DropdownMenuItem(value: q, child: Text(q))).toList(),
          onChanged: (v) => setState(() => _securityQuestion2 = v),
          validator: (v) {
            if (v == null) return 'Required';
            if (v == _securityQuestion1) return 'Choose a different question';
            return null;
          },
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _answer2Controller,
          decoration: const InputDecoration(labelText: 'Answer 2'),
          validator: (v) => (v == null || v.trim().length < 2) ? 'Required' : null,
        ),
      ],
    ];
  }
}
