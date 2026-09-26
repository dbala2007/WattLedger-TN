import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/billing.dart';
import '../models/meter.dart';
import '../state/billing_provider.dart';
import '../state/meter_provider.dart';
import 'bill_estimate_card.dart';

/// Past billing cycles and the meter reader visits that define them.
///
/// Each pair of consecutive visits (official TNPDCL assessments) is one
/// completed cycle. All the calculation happens on the backend
/// (GET /meters/{id}/billing-history) - this widget only displays it and
/// lets the user record, correct or delete visits.
class BillingHistorySection extends StatelessWidget {
  final Meter meter;

  const BillingHistorySection({super.key, required this.meter});

  @override
  Widget build(BuildContext context) {
    final billingProvider = context.watch<BillingProvider>();
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(child: Text('Billing history', style: theme.textTheme.titleLarge)),
            FilledButton.tonalIcon(
              onPressed: () => showVisitDialog(context, meter: meter),
              icon: const Icon(Icons.add),
              label: const Text('Record meter reader visit'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Each time the EB meter reader visits, record that date here (with the official bill '
          'amount if you have it). The cycle between two visits appears below with its full bill.',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 16),
        if (billingProvider.history.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                billingProvider.assessmentsNewestFirst.isEmpty
                    ? 'No visits recorded yet. To see your previous cycle, record the visit that started '
                        'it and the visit that ended it.'
                    : 'Only one visit recorded so far - it starts the current cycle. Record the visit '
                        'before it to see the previous cycle.',
              ),
            ),
          )
        else
          ...billingProvider.history.map((cycle) => _PastCycleTile(cycle: cycle, meter: meter)),
        if (billingProvider.assessmentsNewestFirst.isNotEmpty) ...[
          const SizedBox(height: 24),
          Text('Meter reader visits', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: billingProvider.assessmentsNewestFirst
                  .map((visit) => _VisitTile(visit: visit, meter: meter))
                  .toList(),
            ),
          ),
        ],
      ],
    );
  }
}

/// One completed cycle: a one-line summary, expanding to the full breakdown.
class _PastCycleTile extends StatelessWidget {
  final PastCycleBill cycle;
  final Meter meter;

  const _PastCycleTile({required this.cycle, required this.meter});

  @override
  Widget build(BuildContext context) {
    final estimate = cycle.estimate;
    final estimated = estimate.totalEstimatedAmount;
    final summary = [
      formatUnits(estimate.totalEbUnits),
      if (estimated != null) 'Estimated ${formatCurrency(estimated)}',
      if (cycle.officialBillAmount != null) 'Official ${formatCurrency(cycle.officialBillAmount!)}',
    ].join('  ·  ');

    return Card(
      child: ExpansionTile(
        title: Text('${formatDisplayDate(estimate.periodStart)} to ${formatDisplayDate(estimate.periodEnd)}'),
        subtitle: Text(summary),
        childrenPadding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
        children: [
          if (cycle.officialBillAmount != null) _OfficialVsEstimate(cycle: cycle),
          BillEstimateCard(estimate: estimate, solarMode: meter.solarMode, title: 'Estimated by app'),
        ],
      ),
    );
  }
}

class _OfficialVsEstimate extends StatelessWidget {
  final PastCycleBill cycle;

  const _OfficialVsEstimate({required this.cycle});

  @override
  Widget build(BuildContext context) {
    final difference = cycle.difference;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _row('Official TNPDCL bill', formatCurrency(cycle.officialBillAmount!)),
            if (difference != null)
              _row(
                difference >= 0 ? 'Official is higher by' : 'Official is lower by',
                formatCurrency(difference.abs()),
              ),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(label), Text(value)]),
    );
  }
}

class _VisitTile extends StatelessWidget {
  final BillingAssessment visit;
  final Meter meter;

  const _VisitTile({required this.visit, required this.meter});

  @override
  Widget build(BuildContext context) {
    final details = [
      if (visit.officialBillAmount != null) 'Official bill ${formatCurrency(visit.officialBillAmount!)}',
      if (visit.notes != null) visit.notes!,
    ];
    return ListTile(
      leading: const Icon(Icons.event_available),
      title: Text(formatDisplayDate(visit.assessedOn)),
      subtitle: details.isEmpty ? null : Text(details.join('  ·  ')),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            tooltip: 'Edit visit',
            icon: const Icon(Icons.edit_outlined),
            onPressed: () => showVisitDialog(context, meter: meter, existing: visit),
          ),
          IconButton(
            tooltip: 'Delete visit',
            icon: const Icon(Icons.delete_outline),
            onPressed: () => _confirmDelete(context),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete visit?'),
        content: Text(
          'Delete the meter reader visit on ${formatDisplayDate(visit.assessedOn)}? '
          'The cycles on either side of it will be merged into one.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;

    await _runAndRefresh(
      context,
      () => context.read<BillingProvider>().deleteAssessment(meter.id, visit.id),
    );
  }
}

/// Dialog to record a new visit, or edit [existing] if given.
Future<void> showVisitDialog(BuildContext context, {required Meter meter, BillingAssessment? existing}) async {
  final amountController = TextEditingController(text: existing?.officialBillAmount?.toStringAsFixed(2) ?? '');
  final notesController = TextEditingController(text: existing?.notes ?? '');
  final formKey = GlobalKey<FormState>();
  DateTime? visitDate = existing?.assessedOn;

  final saved = await showDialog<bool>(
    context: context,
    builder: (context) => StatefulBuilder(
      // StatefulBuilder lets the dialog redraw itself when the date is
      // picked, without a separate StatefulWidget class.
      builder: (context, setDialogState) => AlertDialog(
        title: Text(existing == null ? 'Record meter reader visit' : 'Edit meter reader visit'),
        content: Form(
          key: formKey,
          child: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                FormField<DateTime>(
                  initialValue: visitDate,
                  validator: (_) => visitDate == null ? 'Pick the date of the visit' : null,
                  builder: (field) => InkWell(
                    onTap: () async {
                      final now = DateTime.now();
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: visitDate ?? now,
                        firstDate: DateTime(2000),
                        lastDate: now, // a visit can't be in the future
                      );
                      if (picked != null) {
                        setDialogState(() => visitDate = picked);
                        field.didChange(picked);
                      }
                    },
                    child: InputDecorator(
                      decoration: InputDecoration(
                        labelText: 'Visit (assessment) date',
                        helperText: 'As printed on your EB card / TNPDCL SMS',
                        errorText: field.errorText,
                      ),
                      child: Text(visitDate == null ? 'Not set' : formatDisplayDate(visitDate!)),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: amountController,
                  decoration: const InputDecoration(
                    labelText: 'Official bill amount, ₹ (optional)',
                    helperText: 'The bill raised at this visit, for the cycle that just ended',
                  ),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  validator: (v) {
                    final text = v?.trim() ?? '';
                    if (text.isEmpty) return null;
                    final parsed = double.tryParse(text);
                    if (parsed == null || parsed < 0) return 'Enter a valid amount';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: notesController,
                  decoration: const InputDecoration(labelText: 'Notes (optional)'),
                ),
              ],
            ),
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
    ),
  );

  if (saved != true || !context.mounted) return;

  final amountText = amountController.text.trim();
  final amount = amountText.isEmpty ? null : double.parse(amountText);
  final billingProvider = context.read<BillingProvider>();

  await _runAndRefresh(
    context,
    () => existing == null
        ? billingProvider.recordAssessment(meter.id,
            assessedOn: visitDate!, officialBillAmount: amount, notes: notesController.text)
        : billingProvider.updateAssessment(meter.id, existing.id,
            assessedOn: visitDate!, officialBillAmount: amount, notes: notesController.text),
  );
}

/// Runs a visit change, then reloads meters too - the meter's "last
/// assessment date" follows the latest visit, so the meter form and
/// dashboard must see the new value. Errors (e.g. a duplicate date) are
/// shown as a snackbar.
Future<void> _runAndRefresh(BuildContext context, Future<void> Function() action) async {
  final messenger = ScaffoldMessenger.of(context);
  final meterProvider = context.read<MeterProvider>();
  try {
    await action();
    await meterProvider.loadMeters();
  } catch (e) {
    messenger.showSnackBar(SnackBar(content: Text(e.toString())));
  }
}
