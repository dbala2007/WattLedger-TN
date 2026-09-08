import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/tariff.dart';
import '../services/tariff_service.dart';
import '../state/tariff_provider.dart';

class _RuleRow {
  final TextEditingController nameController;
  final TextEditingController minController;
  final TextEditingController maxController; // blank = unlimited
  final TextEditingController freeUnitsController;

  _RuleRow()
      : nameController = TextEditingController(),
        minController = TextEditingController(text: '0'),
        maxController = TextEditingController(),
        freeUnitsController = TextEditingController(text: '0');

  _RuleRow.fromExisting(SubsidyRule rule)
      : nameController = TextEditingController(text: rule.ruleName),
        minController = TextEditingController(text: formatUnitsShort(rule.consumptionMin)),
        maxController = TextEditingController(text: rule.consumptionMax == null ? '' : formatUnitsShort(rule.consumptionMax!)),
        freeUnitsController = TextEditingController(text: formatUnitsShort(rule.freeUnits));

  void dispose() {
    nameController.dispose();
    minController.dispose();
    maxController.dispose();
    freeUnitsController.dispose();
  }
}

class _SlabRow {
  final TextEditingController ruleGroupController;
  final TextEditingController fromController;
  final TextEditingController toController; // blank = unlimited
  final TextEditingController rateController;

  _SlabRow()
      : ruleGroupController = TextEditingController(),
        fromController = TextEditingController(text: '0'),
        toController = TextEditingController(),
        rateController = TextEditingController();

  _SlabRow.fromExisting(TariffSlab slab)
      : ruleGroupController = TextEditingController(text: slab.ruleGroup),
        fromController = TextEditingController(text: formatUnitsShort(slab.fromUnit)),
        toController = TextEditingController(text: slab.toUnit == null ? '' : formatUnitsShort(slab.toUnit!)),
        rateController = TextEditingController(text: slab.ratePerUnit.toString());

  void dispose() {
    ruleGroupController.dispose();
    fromController.dispose();
    toController.dispose();
    rateController.dispose();
  }
}

/// Form for adding a new tariff plan version, or editing an existing one
/// when [existingPlan] is passed in (PRP.md section 11, screen 7). A rule's
/// `rule_name` must match the `rule_group` on the slabs that belong to it -
/// e.g. both "cycle_upto_500".
class TariffFormScreen extends StatefulWidget {
  final TariffPlan? existingPlan;

  const TariffFormScreen({super.key, this.existingPlan});

  @override
  State<TariffFormScreen> createState() => _TariffFormScreenState();
}

class _TariffFormScreenState extends State<TariffFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _providerController;
  late final TextEditingController _fixedChargeController;
  late final TextEditingController _sourceReferenceController;
  late DateTime _effectiveFrom;
  DateTime? _effectiveTo;
  late String _billingFrequency;
  late bool _active;

  late final List<_RuleRow> _rules;
  late final List<_SlabRow> _slabs;

  bool _saving = false;
  String? _error;

  bool get _isEditing => widget.existingPlan != null;

  @override
  void initState() {
    super.initState();
    final plan = widget.existingPlan;
    _nameController = TextEditingController(text: plan?.name ?? 'TN Domestic');
    _providerController = TextEditingController(text: plan?.provider ?? 'TANGEDCO');
    _fixedChargeController = TextEditingController(text: plan == null ? '0' : plan.fixedCharge.toString());
    _sourceReferenceController = TextEditingController(text: plan?.sourceReference ?? '');
    _effectiveFrom = plan?.effectiveFrom ?? DateTime.now();
    _effectiveTo = plan?.effectiveTo;
    _billingFrequency = plan?.billingFrequency ?? 'BI_MONTHLY';
    _active = plan?.active ?? true;
    _rules = plan == null ? [_RuleRow()] : plan.subsidyRules.map(_RuleRow.fromExisting).toList();
    _slabs = plan == null ? [_SlabRow()] : plan.slabs.map(_SlabRow.fromExisting).toList();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _providerController.dispose();
    _fixedChargeController.dispose();
    _sourceReferenceController.dispose();
    for (final r in _rules) {
      r.dispose();
    }
    for (final s in _slabs) {
      s.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate(DateTime? current, ValueChanged<DateTime?> onPicked) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    onPicked(picked);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final ruleInputs = _rules
          .map((r) => SubsidyRuleInput(
                ruleName: r.nameController.text.trim(),
                consumptionMin: double.parse(r.minController.text.trim()),
                consumptionMax: r.maxController.text.trim().isEmpty ? null : double.parse(r.maxController.text.trim()),
                freeUnits: double.parse(r.freeUnitsController.text.trim()),
                effectiveFrom: _effectiveFrom,
                effectiveTo: _effectiveTo,
              ))
          .toList();

      final slabInputs = <TariffSlabInput>[];
      for (final group in _slabs.map((s) => s.ruleGroupController.text.trim()).toSet()) {
        var order = 1;
        for (final slab in _slabs.where((s) => s.ruleGroupController.text.trim() == group)) {
          slabInputs.add(TariffSlabInput(
            ruleGroup: group,
            fromUnit: double.parse(slab.fromController.text.trim()),
            toUnit: slab.toController.text.trim().isEmpty ? null : double.parse(slab.toController.text.trim()),
            ratePerUnit: double.parse(slab.rateController.text.trim()),
            sortOrder: order++,
          ));
        }
      }

      final tariffProvider = context.read<TariffProvider>();
      if (_isEditing) {
        await tariffProvider.updatePlan(
          id: widget.existingPlan!.id,
          name: _nameController.text.trim(),
          provider: _providerController.text.trim(),
          consumerCategory: 'DOMESTIC',
          effectiveFrom: _effectiveFrom,
          effectiveTo: _effectiveTo,
          billingFrequency: _billingFrequency,
          fixedCharge: double.parse(_fixedChargeController.text.trim()),
          sourceReference: _sourceReferenceController.text.trim(),
          active: _active,
          subsidyRules: ruleInputs,
          slabs: slabInputs,
        );
      } else {
        await tariffProvider.createPlan(
          name: _nameController.text.trim(),
          provider: _providerController.text.trim(),
          consumerCategory: 'DOMESTIC',
          effectiveFrom: _effectiveFrom,
          effectiveTo: _effectiveTo,
          billingFrequency: _billingFrequency,
          fixedCharge: double.parse(_fixedChargeController.text.trim()),
          sourceReference: _sourceReferenceController.text.trim(),
          subsidyRules: ruleInputs,
          slabs: slabInputs,
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
      appBar: AppBar(title: Text(_isEditing ? 'Edit tariff plan' : 'Add tariff plan')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Card(
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        'Tip: enter the exact TNERC order number/date in "Source reference". '
                        'PRP.md requires this to be verified before real bills rely on it.',
                        style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _nameController,
                    decoration: const InputDecoration(labelText: 'Plan name'),
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _providerController,
                    decoration: const InputDecoration(labelText: 'Provider'),
                  ),
                  const SizedBox(height: 12),
                  InkWell(
                    onTap: () => _pickDate(_effectiveFrom, (d) => setState(() => _effectiveFrom = d ?? _effectiveFrom)),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: 'Effective from'),
                      child: Text(formatDisplayDate(_effectiveFrom)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  InkWell(
                    onTap: () => _pickDate(_effectiveTo, (d) => setState(() => _effectiveTo = d)),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: 'Effective to (optional - blank = ongoing)'),
                      child: Text(_effectiveTo == null ? 'Ongoing' : formatDisplayDate(_effectiveTo!)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _billingFrequency,
                    decoration: const InputDecoration(labelText: 'Billing frequency'),
                    items: const [
                      DropdownMenuItem(value: 'BI_MONTHLY', child: Text('Bi-monthly')),
                      DropdownMenuItem(value: 'MONTHLY', child: Text('Monthly')),
                    ],
                    onChanged: (v) => setState(() => _billingFrequency = v ?? 'BI_MONTHLY'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _fixedChargeController,
                    decoration: const InputDecoration(labelText: 'Fixed charge per bill (₹)'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) => double.tryParse(v?.trim() ?? '') == null ? 'Enter a number' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _sourceReferenceController,
                    decoration: const InputDecoration(labelText: 'Source reference (TNERC order no./date)'),
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Active'),
                    subtitle: const Text('Inactive plans are kept for history but never used for new bill estimates'),
                    value: _active,
                    onChanged: (v) => setState(() => _active = v),
                  ),
                  const SizedBox(height: 12),
                  Text('Subsidy rule groups', style: Theme.of(context).textTheme.titleMedium),
                  const Text(
                    'Each rule defines a consumption band and how many units are free within it.',
                    style: TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: 8),
                  ..._rules.asMap().entries.map((entry) => _buildRuleRow(entry.key, entry.value)),
                  OutlinedButton.icon(
                    onPressed: () => setState(() => _rules.add(_RuleRow())),
                    icon: const Icon(Icons.add),
                    label: const Text('Add rule group'),
                  ),
                  const SizedBox(height: 24),
                  Text('Slabs', style: Theme.of(context).textTheme.titleMedium),
                  const Text(
                    'Rule group name must match a rule above exactly. Leave "to" blank on the last slab '
                    'in each group so the full chargeable range is covered.',
                    style: TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: 8),
                  ..._slabs.asMap().entries.map((entry) => _buildSlabRow(entry.key, entry.value)),
                  OutlinedButton.icon(
                    onPressed: () => setState(() => _slabs.add(_SlabRow())),
                    icon: const Icon(Icons.add),
                    label: const Text('Add slab'),
                  ),
                  const SizedBox(height: 24),
                  if (_error != null) ...[
                    Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                    const SizedBox(height: 12),
                  ],
                  FilledButton(
                    onPressed: _saving ? null : _save,
                    child: _saving
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                        : Text(_isEditing ? 'Save changes' : 'Create tariff plan'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRuleRow(int index, _RuleRow row) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: TextFormField(
              controller: row.nameController,
              decoration: const InputDecoration(labelText: 'Rule name', isDense: true),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextFormField(
              controller: row.minController,
              decoration: const InputDecoration(labelText: 'Min units', isDense: true),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: (v) => double.tryParse(v?.trim() ?? '') == null ? 'Invalid' : null,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextFormField(
              controller: row.maxController,
              decoration: const InputDecoration(labelText: 'Max units (blank=∞)', isDense: true),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextFormField(
              controller: row.freeUnitsController,
              decoration: const InputDecoration(labelText: 'Free units', isDense: true),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: (v) => double.tryParse(v?.trim() ?? '') == null ? 'Invalid' : null,
            ),
          ),
          if (_rules.length > 1)
            IconButton(
              icon: const Icon(Icons.remove_circle_outline),
              onPressed: () => setState(() => _rules.removeAt(index)),
            ),
        ],
      ),
    );
  }

  Widget _buildSlabRow(int index, _SlabRow row) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: TextFormField(
              controller: row.ruleGroupController,
              decoration: const InputDecoration(labelText: 'Rule group', isDense: true),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextFormField(
              controller: row.fromController,
              decoration: const InputDecoration(labelText: 'From', isDense: true),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: (v) => double.tryParse(v?.trim() ?? '') == null ? 'Invalid' : null,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextFormField(
              controller: row.toController,
              decoration: const InputDecoration(labelText: 'To (blank=∞)', isDense: true),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextFormField(
              controller: row.rateController,
              decoration: const InputDecoration(labelText: 'Rate/unit (₹)', isDense: true),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: (v) => double.tryParse(v?.trim() ?? '') == null ? 'Invalid' : null,
            ),
          ),
          if (_slabs.length > 1)
            IconButton(
              icon: const Icon(Icons.remove_circle_outline),
              onPressed: () => setState(() => _slabs.removeAt(index)),
            ),
        ],
      ),
    );
  }
}
