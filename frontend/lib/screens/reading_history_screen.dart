import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/meter.dart';
import '../models/reading.dart';
import '../state/reading_provider.dart';
import '../widgets/async_state_view.dart';
import '../widgets/no_meter_placeholder.dart';

/// Reading History screen (PRP.md section 11, screen 4): date, EB
/// cumulative + balance, solar cumulative + balance, and edit/delete
/// controls (FR-003, FR-004).
class ReadingHistoryScreen extends StatefulWidget {
  final Meter? meter;

  const ReadingHistoryScreen({super.key, required this.meter});

  @override
  State<ReadingHistoryScreen> createState() => _ReadingHistoryScreenState();
}

class _ReadingHistoryScreenState extends State<ReadingHistoryScreen> {
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant ReadingHistoryScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.meter?.id != widget.meter?.id) _load();
  }

  void _load() {
    final meter = widget.meter;
    if (meter != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.read<ReadingProvider>().loadReadings(meter.id);
      });
    }
  }

  Future<void> _confirmDelete(MeterReading reading) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete reading?'),
        content: Text(
          'Delete the reading for ${formatDisplayDate(reading.readingDate)}? '
          'Balances for later readings will be recalculated.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      try {
        await context.read<ReadingProvider>().removeReading(reading.id);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
        }
      }
    }
  }

  Future<void> _editReading(MeterReading reading) async {
    final ebController = TextEditingController(text: reading.ebUnits.toString());
    final solarController = TextEditingController(text: reading.solarUnits?.toString() ?? '');
    final formKey = GlobalKey<FormState>();

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Edit reading - ${formatDisplayDate(reading.readingDate)}'),
        content: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: ebController,
                decoration: const InputDecoration(labelText: 'EB units'),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                validator: (v) => double.tryParse(v?.trim() ?? '') == null ? 'Enter a valid number' : null,
              ),
              if (reading.solarUnits != null) ...[
                const SizedBox(height: 12),
                TextFormField(
                  controller: solarController,
                  decoration: const InputDecoration(labelText: 'Solar unit'),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  validator: (v) => double.tryParse(v?.trim() ?? '') == null ? 'Enter a valid number' : null,
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              if (formKey.currentState!.validate()) Navigator.of(context).pop(true);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (saved == true && mounted) {
      try {
        await context.read<ReadingProvider>().editReading(
              reading.id,
              ebUnits: double.parse(ebController.text.trim()),
              solarUnits: reading.solarUnits == null ? null : double.parse(solarController.text.trim()),
            );
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.meter == null) return const NoMeterPlaceholder();

    return Consumer<ReadingProvider>(
      builder: (context, readingProvider, _) {
        return AsyncStateView(
          loading: readingProvider.loading,
          error: readingProvider.error,
          onRetry: () => widget.meter != null ? readingProvider.loadReadings(widget.meter!.id) : null,
          child: readingProvider.readingsNewestFirst.isEmpty
              ? const Center(child: Text('No readings yet. Add one from the Reading Entry tab.'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('Date')),
                        DataColumn(label: Text('EB units'), numeric: true),
                        DataColumn(label: Text('EB balance'), numeric: true),
                        DataColumn(label: Text('Solar unit'), numeric: true),
                        DataColumn(label: Text('Solar balance'), numeric: true),
                        DataColumn(label: Text('Notes')),
                        DataColumn(label: Text('')),
                      ],
                      rows: readingProvider.readingsNewestFirst.map((reading) {
                        return DataRow(
                          cells: [
                            DataCell(Text(formatDisplayDate(reading.readingDate))),
                            DataCell(Text(formatUnitsShort(reading.ebUnits))),
                            DataCell(Text(reading.ebBalance == null ? '-' : formatUnitsShort(reading.ebBalance!))),
                            DataCell(Text(reading.solarUnits == null ? '-' : formatUnitsShort(reading.solarUnits!))),
                            DataCell(
                              Text(reading.solarBalance == null ? '-' : formatUnitsShort(reading.solarBalance!)),
                            ),
                            DataCell(Text(reading.notes ?? '')),
                            DataCell(
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    icon: const Icon(Icons.edit_outlined),
                                    tooltip: 'Edit',
                                    onPressed: () => _editReading(reading),
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.delete_outline),
                                    tooltip: 'Delete',
                                    onPressed: () => _confirmDelete(reading),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        );
                      }).toList(),
                    ),
                  ),
                ),
        );
      },
    );
  }
}
