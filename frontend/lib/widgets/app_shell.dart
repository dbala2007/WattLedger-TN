import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../screens/billing_screen.dart';
import '../screens/dashboard_screen.dart';
import '../screens/meters_screen.dart';
import '../screens/reading_entry_screen.dart';
import '../screens/reading_history_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/tariffs_screen.dart';
import '../state/auth_provider.dart';
import '../state/meter_provider.dart';
import 'meter_selector.dart';

/// The app's overall navigation shell: a NavigationRail (this is a
/// desktop/web-first app - PRP.md section 8) on the left, an AppBar with
/// the meter selector, and the selected screen in the body.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    // AppShell is only ever built once a login/signup/reset succeeded (see
    // main.dart's _RootScreen), so this is the right place to surface the
    // one-shot welcome message AuthProvider queued for that. Scheduled for
    // after the first frame since ScaffoldMessenger isn't available yet
    // during initState.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final message = context.read<AuthProvider>().consumeWelcomeMessage();
      if (message != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message), duration: const Duration(seconds: 3)),
        );
      }
    });
  }

  static const _destinations = [
    NavigationRailDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: Text('Dashboard')),
    NavigationRailDestination(icon: Icon(Icons.add_circle_outline), selectedIcon: Icon(Icons.add_circle), label: Text('Add reading')),
    NavigationRailDestination(icon: Icon(Icons.history_outlined), selectedIcon: Icon(Icons.history), label: Text('History')),
    NavigationRailDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: Text('Billing')),
    NavigationRailDestination(icon: Icon(Icons.electric_meter_outlined), selectedIcon: Icon(Icons.electric_meter), label: Text('Meters')),
    NavigationRailDestination(icon: Icon(Icons.request_quote_outlined), selectedIcon: Icon(Icons.request_quote), label: Text('Tariffs')),
    NavigationRailDestination(icon: Icon(Icons.settings_outlined), selectedIcon: Icon(Icons.settings), label: Text('Settings')),
  ];

  static const _titles = ['Dashboard', 'Add reading', 'Reading history', 'Billing', 'Meters', 'Tariff settings', 'Settings'];

  @override
  Widget build(BuildContext context) {
    final meter = context.watch<MeterProvider>().selected;

    final screens = [
      DashboardScreen(meter: meter),
      ReadingEntryScreen(meter: meter),
      ReadingHistoryScreen(meter: meter),
      BillingScreen(meter: meter),
      const MetersScreen(),
      const TariffsScreen(),
      const SettingsScreen(),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_selectedIndex]),
        actions: const [Padding(padding: EdgeInsets.only(right: 16), child: Center(child: MeterSelector()))],
      ),
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: _selectedIndex,
            onDestinationSelected: (index) => setState(() => _selectedIndex = index),
            labelType: NavigationRailLabelType.all,
            destinations: _destinations,
          ),
          const VerticalDivider(width: 1),
          Expanded(child: screens[_selectedIndex]),
        ],
      ),
    );
  }
}
