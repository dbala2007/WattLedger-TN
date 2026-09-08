import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../state/auth_provider.dart';

/// Self-service password reset via the two security questions chosen at
/// signup (backend/app/domain/auth.py) - there's no email/SMTP setup yet,
/// so this is the only reset path today. Two steps on one screen: enter the
/// email to find out which two questions were chosen, then answer both and
/// pick a new password.
class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _emailFormKey = GlobalKey<FormState>();
  final _resetFormKey = GlobalKey<FormState>();

  final _emailController = TextEditingController();
  final _answer1Controller = TextEditingController();
  final _answer2Controller = TextEditingController();
  final _newPasswordController = TextEditingController();

  (String, String)? _questions;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _answer1Controller.dispose();
    _answer2Controller.dispose();
    _newPasswordController.dispose();
    super.dispose();
  }

  Future<void> _lookUpQuestions() async {
    if (!_emailFormKey.currentState!.validate()) return;

    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final questions = await context.read<AuthProvider>().getForgotPasswordQuestions(
            _emailController.text.trim(),
          );
      setState(() => _questions = questions);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _resetPassword() async {
    if (!_resetFormKey.currentState!.validate()) return;

    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await context.read<AuthProvider>().resetPassword(
            email: _emailController.text.trim(),
            securityAnswer1: _answer1Controller.text.trim(),
            securityAnswer2: _answer2Controller.text.trim(),
            newPassword: _newPasswordController.text,
          );
      // resetPassword also logs the user in; _RootScreen (main.dart) is
      // watching AuthProvider and will swap to AppShell once we pop back
      // to the route underneath this pushed screen.
      if (mounted) Navigator.of(context).pop();
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
      appBar: AppBar(title: const Text('Forgot password')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: _questions == null ? _buildEmailStep() : _buildResetStep(_questions!),
          ),
        ),
      ),
    );
  }

  Widget _buildEmailStep() {
    return Form(
      key: _emailFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('Enter your account email to see your security questions.'),
          const SizedBox(height: 16),
          TextFormField(
            controller: _emailController,
            decoration: const InputDecoration(labelText: 'Email'),
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            onFieldSubmitted: (_) => _lookUpQuestions(),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 20),
          if (_error != null) ...[
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 12),
          ],
          FilledButton(
            onPressed: _submitting ? null : _lookUpQuestions,
            child: _submitting
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Continue'),
          ),
        ],
      ),
    );
  }

  Widget _buildResetStep((String, String) questions) {
    final (question1, question2) = questions;
    return Form(
      key: _resetFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(question1, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 8),
          TextFormField(
            controller: _answer1Controller,
            decoration: const InputDecoration(labelText: 'Answer'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          Text(question2, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 8),
          TextFormField(
            controller: _answer2Controller,
            decoration: const InputDecoration(labelText: 'Answer'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 20),
          TextFormField(
            controller: _newPasswordController,
            decoration: const InputDecoration(labelText: 'New password'),
            obscureText: true,
            autofillHints: const [AutofillHints.newPassword],
            onFieldSubmitted: (_) => _resetPassword(),
            validator: (v) {
              if (v == null || v.isEmpty) return 'Required';
              if (v.length < 8) return 'At least 8 characters';
              return null;
            },
          ),
          const SizedBox(height: 20),
          if (_error != null) ...[
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 12),
          ],
          FilledButton(
            onPressed: _submitting ? null : _resetPassword,
            child: _submitting
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Reset password'),
          ),
        ],
      ),
    );
  }
}
