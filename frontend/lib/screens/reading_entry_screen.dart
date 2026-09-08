import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/meter.dart';
import '../state/reading_provider.dart';
import '../widgets/no_meter_placeholder.dart';

/// Daily Reading Entry screen (PRP.md section 11, screen 3). Lets the user
/// type today's cumulative EB/solar reading; the balance is calculated by
/// the backend, never here (CLAUDE.md section 3 - balances are
/// calculated values, not typed by the user).
class ReadingEntryScreen extends StatefulWidget {
  final Meter? meter;

  const ReadingEntryScreen({super.key, required this.meter});

  @override
  State<ReadingEntryScreen> createState() => _ReadingEntryScreenState();
}

class _ReadingEntryScreenState extends State<ReadingEntryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _ebUnitsController = TextEditingController();
  final _solarUnitsController = TextEditingController();
  final _notesController = TextEditingController();
  DateTime _readingDate = DateTime.now();
  bool _saving = false;
  String? _error;
  String? _successMessage;

  @override
  void dispose() {
    _ebUnitsController.dispose();
    _solarUnitsController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _readingDate,
      firstDate: DateTime(2000),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked != null) setState(() => _readingDate = picked);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _saving = true;
      _error = null;
      _successMessage = null;
    });

    try {
      final reading = await context.read<ReadingProvider>().addReading(
            widget.meter!.id,
            readingDate: _readingDate,
            ebUnits: double.parse(_ebUnitsController.text.trim()),
            solarUnits: _solarUnitsController.text.trim().isEmpty
                ? null
                : double.parse(_solarUnitsController.text.trim()),
            notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
          );
      setState(() {
        _successMessage = reading.ebBalance == null
            ? 'Saved. This is the first reading for this meter, so there is no balance yet.'
            : 'Saved. EB balance: ${formatUnits(reading.ebBalance!)}'
                '${reading.solarBalance != null ? ', Solar balance: ${formatUnits(reading.solarBalance!)}' : ''}';
        _ebUnitsController.clear();
        _solarUnitsController.clear();
        _notesController.clear();
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final meter = widget.meter;
    if (meter == null) return const NoMeterPlaceholder();

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Daily reading for ${meter.label}', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 16),
                InkWell(
                  onTap: _pickDate,
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: 'Date'),
                    child: Text(formatDisplayDate(_readingDate)),
                  ),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _ebUnitsController,
                  decoration: const InputDecoration(labelText: 'EB units (cumulative meter reading)'),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) return 'EB units is required';
                    if (double.tryParse(value.trim()) == null) return 'Enter a valid number';
                    return null;
                  },
                ),
                if (meter.solarMode.requiresSolarReading) ...[
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _solarUnitsController,
                    decoration: const InputDecoration(labelText: 'Solar unit (cumulative reading)'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Solar unit is required for a ${meter.solarMode.label} meter';
                      }
                      if (double.tryParse(value.trim()) == null) return 'Enter a valid number';
                      return null;
                    },
                  ),
                ],
                const SizedBox(height: 16),
                TextFormField(
                  controller: _notesController,
                  decoration: const InputDecoration(labelText: 'Notes (optional)'),
                ),
                const SizedBox(height: 24),
                if (_error != null) ...[
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  const SizedBox(height: 12),
                ],
                if (_successMessage != null) ...[
                  Text(_successMessage!, style: TextStyle(color: Theme.of(context).colorScheme.primary)),
                  const SizedBox(height: 12),
                ],
                FilledButton(
                  onPressed: _saving ? null : _save,
                  child: _saving
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Save reading'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
