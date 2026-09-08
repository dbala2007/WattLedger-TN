import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/meter_provider.dart';

/// Dropdown for switching which meter the app is currently showing data
/// for. Lives in the AppBar so it's visible no matter which screen is open
/// (PRP.md FR-009: multiple meters, with a selector when more than one
/// exists).
class MeterSelector extends StatelessWidget {
  const MeterSelector({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<MeterProvider>(
      builder: (context, meterProvider, _) {
        if (meterProvider.meters.isEmpty) {
          return const SizedBox.shrink();
        }
        return DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: meterProvider.selected?.id,
            dropdownColor: Theme.of(context).colorScheme.surface,
            style: Theme.of(context).textTheme.bodyLarge,
            items: meterProvider.meters
                .map((meter) => DropdownMenuItem(value: meter.id, child: Text(meter.label)))
                .toList(),
            onChanged: (id) {
              if (id == null) return;
              final meter = meterProvider.meters.firstWhere((m) => m.id == id);
              meterProvider.selectMeter(meter);
            },
          ),
        );
      },
    );
  }
}
