import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_config.dart';
import '../state/auth_provider.dart';

/// Settings / Backup screen (PRP.md section 11, screen 8). Backup/restore
/// itself is a backend capability that does not exist yet (PRP.md FR-010,
/// Phase 2 "Local backup/restore") - this screen says so plainly rather
/// than showing a button that does nothing.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: ListView(
          padding: const EdgeInsets.all(24),
          shrinkWrap: true,
          children: [
            Text('Account', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('Logged in as ${auth.currentUser?.email ?? '-'}'),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => auth.logout(),
              icon: const Icon(Icons.logout),
              label: const Text('Log out'),
            ),
            const SizedBox(height: 24),
            Text('About', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            const Text('WattLedger TN - Tamil Nadu household electricity and solar usage tracker.'),
            const SizedBox(height: 24),
            Text('Backend connection', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            const Text(AppConfig.apiBaseUrl),
            const SizedBox(height: 24),
            Text('Backup & restore', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            const Text(
              'Not implemented yet. For now, the database file itself '
              '(backend/wattledger.db) can be copied manually as a backup.',
            ),
          ],
        ),
      ),
    );
  }
}
