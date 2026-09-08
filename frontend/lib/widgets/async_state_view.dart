import 'package:flutter/material.dart';

/// Shows a spinner while [loading], an error banner (with retry) if [error]
/// is set, or [child] otherwise. Used on every screen that loads data from
/// the API, so loading/error handling looks and behaves the same everywhere
/// instead of being reinvented per screen.
class AsyncStateView extends StatelessWidget {
  final bool loading;
  final String? error;
  final VoidCallback? onRetry;
  final Widget child;

  const AsyncStateView({super.key, required this.loading, required this.error, required this.child, this.onRetry});

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()));
    }
    if (error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, color: Theme.of(context).colorScheme.error, size: 40),
              const SizedBox(height: 12),
              Text(error!, textAlign: TextAlign.center),
              if (onRetry != null) ...[
                const SizedBox(height: 12),
                OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
              ],
            ],
          ),
        ),
      );
    }
    return child;
  }
}
