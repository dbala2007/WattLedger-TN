import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'screens/login_screen.dart';
import 'state/auth_provider.dart';
import 'state/billing_provider.dart';
import 'state/meter_provider.dart';
import 'state/reading_provider.dart';
import 'state/tariff_provider.dart';
import 'widgets/app_shell.dart';

void main() {
  runApp(const WattLedgerApp());
}

class WattLedgerApp extends StatelessWidget {
  const WattLedgerApp({super.key});

  @override
  Widget build(BuildContext context) {
    // One shared ApiClient for the whole app - every provider talks to the
    // same backend base URL (app/core/app_config.dart), and AuthProvider
    // sets its authToken so every request is authenticated the same way on
    // both web and Windows.
    final apiClient = ApiClient();

    return ChangeNotifierProvider(
      create: (_) => AuthProvider(apiClient)..bootstrap(),
      child: MaterialApp(
        title: 'WattLedger TN',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
        darkTheme: ThemeData(colorSchemeSeed: Colors.teal, brightness: Brightness.dark, useMaterial3: true),
        home: _RootScreen(apiClient: apiClient),
      ),
    );
  }
}

/// Chooses between a splash, the login screen, and the main app based on
/// AuthProvider's state. The data providers (meters, readings, billing,
/// tariffs) are only created - and only fetch anything - once a user is
/// actually logged in, and are keyed by user id so logging in as someone
/// else after a logout starts with a clean slate instead of stale data.
class _RootScreen extends StatelessWidget {
  final ApiClient apiClient;

  const _RootScreen({required this.apiClient});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    if (auth.isBootstrapping) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!auth.isAuthenticated) {
      return const LoginScreen();
    }

    return MultiProvider(
      key: ValueKey(auth.currentUser!.id),
      providers: [
        ChangeNotifierProvider(create: (_) => MeterProvider(apiClient)..loadMeters()),
        ChangeNotifierProvider(create: (_) => ReadingProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => BillingProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => TariffProvider(apiClient)..loadPlans()),
      ],
      child: const AppShell(),
    );
  }
}
