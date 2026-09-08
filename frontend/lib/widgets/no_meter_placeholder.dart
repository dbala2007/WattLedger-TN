import 'package:flutter/material.dart';

/// Shown on any screen that needs a selected meter but none exists yet.
class NoMeterPlaceholder extends StatelessWidget {
  const NoMeterPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.electric_meter_outlined, size: 48, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 12),
            const Text('No meter yet. Add one from the Meters tab to get started.', textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
