import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/meter.dart';
import '../models/solar_mode.dart';
import '../state/meter_provider.dart';

/// Add/Edit Meter screen (PRP.md section 11, screen 2). Used both to
/// create a new meter and to edit an existing one - [existing] is null for
/// "add".
class MeterFormScreen extends StatefulWidget {
  final Meter? existing;

  const MeterFormScreen({super.key, this.existing});

  @override
  State<MeterFormScreen> createState() => _MeterFormScreenState();
}

class _MeterFormScreenState extends State<MeterFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _meterNumberController;
  late final TextEditingController _displayNameController;
  late final TextEditingController _cycleLengthController;
  late SolarMode _solarMode;
  late bool _active;
  DateTime? _billingCycleReferenceDate;
  DateTime? _lastAssessmentDate;
  DateTime? _nextExpectedAssessmentDate;
  bool _saving = false;
  String? _error;

  bool get _isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    _meterNumberController = TextEditingController(text: existing?.meterNumber ?? '');
    _displayNameController = TextEditingController(text: existing?.displayName ?? '');
    _cycleLengthController = TextEditingController(text: (existing?.cycleLengthMonths ?? 2).toString());
    _solarMode = existing?.solarMode ?? SolarMode.none;
    _active = existing?.active ?? true;
    _billingCycleReferenceDate = existing?.billingCycleReferenceDate;
    _lastAssessmentDate = existing?.lastAssessmentDate;
    _nextExpectedAssessmentDate = existing?.nextExpectedAssessmentDate;
  }

  @override
  void dispose() {
    _meterNumberController.dispose();
    _displayNameController.dispose();
    _cycleLengthController.dispose();
    super.dispose();
  }

  Future<void> _pickDate(DateTime? current, ValueChanged<DateTime> onPicked) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked != null) onPicked(picked);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _saving = true;
      _error = null;
    });

    final meterProvider = context.read<MeterProvider>();
    final cycleLength = int.parse(_cycleLengthController.text.trim());

    try {
      if (_isEditing) {
        await meterProvider.updateMeter(
          widget.existing!.id,
          displayName: _displayNameController.text.trim(),
          solarMode: _solarMode,
          active: _active,
          billingCycleReferenceDate: _billingCycleReferenceDate,
          cycleLengthMonths: cycleLength,
          lastAssessmentDate: _lastAssessmentDate,
          nextExpectedAssessmentDate: _nextExpectedAssessmentDate,
        );
      } else {
        await meterProvider.createMeter(
          meterNumber: _meterNumberController.text.trim(),
          displayName: _displayNameController.text.trim().isEmpty ? null : _displayNameController.text.trim(),
          solarMode: _solarMode,
          billingCycleReferenceDate: _billingCycleReferenceDate,
          cycleLengthMonths: cycleLength,
        );
      }
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_isEditing ? 'Edit meter' : 'Add meter')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    controller: _meterNumberController,
                    enabled: !_isEditing,
                    decoration: const InputDecoration(
                      labelText: 'Meter number',
                      helperText: 'EB/TNPDCL service or meter number',
                    ),
                    validator: (value) =>
                        (value == null || value.trim().isEmpty) ? 'Meter number is required' : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _displayNameController,
                    decoration: const InputDecoration(labelText: 'Display name (optional)'),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<SolarMode>(
                    initialValue: _solarMode,
                    decoration: const InputDecoration(labelText: 'Solar mode'),
                    items: SolarMode.values
                        .map((mode) => DropdownMenuItem(value: mode, child: Text(mode.label)))
                        .toList(),
                    onChanged: (mode) => setState(() => _solarMode = mode ?? SolarMode.none),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _cycleLengthController,
                    decoration: const InputDecoration(
                      labelText: 'Billing cycle length (months)',
                      helperText: 'Tamil Nadu domestic billing is normally bi-monthly (2)',
                    ),
                    keyboardType: TextInputType.number,
                    validator: (value) {
                      final parsed = int.tryParse(value?.trim() ?? '');
                      if (parsed == null || parsed <= 0) return 'Enter a positive whole number of months';
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  _DatePickerField(
                    label: 'Billing cycle start date',
                    helperText: 'Used only until an assessment date below is recorded',
                    value: _billingCycleReferenceDate,
                    onTap: () => _pickDate(
                      _billingCycleReferenceDate,
                      (d) => setState(() => _billingCycleReferenceDate = d),
                    ),
                  ),
                  if (_isEditing) ...[
                    const SizedBox(height: 16),
                    _DatePickerField(
                      label: 'Last official assessment date (optional)',
                      helperText: 'TNEB\'s billing cycle isn\'t a fixed 2 months - it\'s whenever the '
                          'meter reader actually visits. Set this to that real date and it becomes '
                          'the current cycle\'s start for every calculation.',
                      value: _lastAssessmentDate,
                      onTap: () =>
                          _pickDate(_lastAssessmentDate, (d) => setState(() => _lastAssessmentDate = d)),
                    ),
                    const SizedBox(height: 16),
                    _DatePickerField(
                      label: 'Next expected assessment date (optional)',
                      helperText: 'Your best guess for the next visit - the cycle end used in '
                          'calculations until you correct it to the real date',
                      value: _nextExpectedAssessmentDate,
                      onTap: () => _pickDate(
                        _nextExpectedAssessmentDate,
                        (d) => setState(() => _nextExpectedAssessmentDate = d),
                      ),
                    ),
                    const SizedBox(height: 16),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Active'),
                      value: _active,
                      onChanged: (value) => setState(() => _active = value),
                    ),
                  ],
                  const SizedBox(height: 24),
                  if (_error != null) ...[
                    Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                    const SizedBox(height: 12),
                  ],
                  FilledButton(
                    onPressed: _saving ? null : _save,
                    child: _saving
                        ? const SizedBox(
                            width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                        : Text(_isEditing ? 'Save changes' : 'Add meter'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DatePickerField extends StatelessWidget {
  final String label;
  final String? helperText;
  final DateTime? value;
  final VoidCallback onTap;

  const _DatePickerField({required this.label, this.helperText, required this.value, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: InputDecorator(
        decoration: InputDecoration(labelText: label, helperText: helperText),
        child: Text(value == null ? 'Not set' : formatDisplayDate(value!)),
      ),
    );
  }
}
