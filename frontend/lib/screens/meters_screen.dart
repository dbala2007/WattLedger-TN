import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../state/meter_provider.dart';
import '../widgets/async_state_view.dart';
import 'meter_form_screen.dart';

/// Meter list, with add/edit (PRP.md section 11, screen 2).
class MetersScreen extends StatelessWidget {
  const MetersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<MeterProvider>(
      builder: (context, meterProvider, _) {
        return Scaffold(
          body: AsyncStateView(
            loading: meterProvider.loading,
            error: meterProvider.error,
            onRetry: meterProvider.loadMeters,
            child: meterProvider.meters.isEmpty
                ? const Center(child: Text('No meters yet. Tap + to add one.'))
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: meterProvider.meters.length,
                    itemBuilder: (context, index) {
                      final meter = meterProvider.meters[index];
                      return Card(
                        child: ListTile(
                          leading: Icon(meter.active ? Icons.electric_meter : Icons.electric_meter_outlined),
                          title: Text(meter.label),
                          subtitle: Text(
                            'Meter no: ${meter.meterNumber} | ${meter.solarMode.label} | '
                            '${meter.active ? "Active" : "Inactive"}'
                            '${meter.billingCycleReferenceDate != null ? " | Cycle starts ${formatDisplayDate(meter.billingCycleReferenceDate!)}, every ${meter.cycleLengthMonths}mo" : ""}',
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () async {
                            await Navigator.of(context).push(
                              MaterialPageRoute(builder: (_) => MeterFormScreen(existing: meter)),
                            );
                          },
                        ),
                      );
                    },
                  ),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const MeterFormScreen()),
              );
            },
            child: const Icon(Icons.add),
          ),
        );
      },
    );
  }
}
