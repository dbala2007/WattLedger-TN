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

    // All providers live above MaterialApp (and therefore above its
    // Navigator), not inside `home`. Flutter's Navigator gives each pushed
    // route (Navigator.push, used by every "Add/Edit" form) its own
    // subtree in the app's Overlay - a sibling of the route it was pushed
    // from, not a descendant of it. A provider placed inside `home`'s
    // content is invisible from any pushed route for exactly that reason
    // (this is what caused "Could not find the correct Provider" when
    // opening the tariff/meter forms). Being above the Navigator instead
    // means every route, pushed or not, can see these providers.
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider(apiClient)..bootstrap()),
        ChangeNotifierProvider(create: (_) => MeterProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => ReadingProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => BillingProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => TariffProvider(apiClient)),
      ],
      child: MaterialApp(
        title: 'WattLedger TN',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
        darkTheme: ThemeData(colorSchemeSeed: Colors.teal, brightness: Brightness.dark, useMaterial3: true),
        home: const _RootScreen(),
      ),
    );
  }
}

/// Chooses between a splash, the login screen, and the main app based on
/// AuthProvider's state. Since the data providers now live above the
/// Navigator (see WattLedgerApp) rather than being created fresh per login,
/// this widget is what triggers their initial load once a user is
/// authenticated, and clears them back out on logout - replacing the old
/// "destroy and recreate the provider" trick for keeping one user's data
/// from leaking into the next login.
class _RootScreen extends StatefulWidget {
  const _RootScreen();

  @override
  State<_RootScreen> createState() => _RootScreenState();
}

class _RootScreenState extends State<_RootScreen> {
  String? _loadedForUserId;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    if (auth.isBootstrapping) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (!auth.isAuthenticated) {
      if (_loadedForUserId != null) {
        _loadedForUserId = null;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          context.read<MeterProvider>().reset();
          context.read<ReadingProvider>().reset();
          context.read<BillingProvider>().reset();
          context.read<TariffProvider>().reset();
        });
      }
      return const LoginScreen();
    }

    final userId = auth.currentUser!.id;
    if (_loadedForUserId != userId) {
      _loadedForUserId = userId;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        context.read<MeterProvider>().loadMeters();
        context.read<TariffProvider>().loadPlans();
      });
    }

    return const AppShell();
  }
}
