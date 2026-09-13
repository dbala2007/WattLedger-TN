import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/billing.dart';
import '../models/meter.dart';
import '../models/solar_mode.dart';
import '../state/billing_provider.dart';
import '../widgets/async_state_view.dart';
import '../widgets/no_meter_placeholder.dart';

/// Combines the Billing Cycle Summary and Estimated EB Bill screens
/// (PRP.md section 11, screens 5 and 6) - they show the same underlying
/// cycle, so one screen avoids duplicating the period-start/end header.
///
/// Per CLAUDE.md section 5 ("Calculation transparency"), every field of the
/// breakdown is shown - never just the final total.
class BillingScreen extends StatefulWidget {
  final Meter? meter;

  const BillingScreen({super.key, required this.meter});

  @override
  State<BillingScreen> createState() => _BillingScreenState();
}

class _BillingScreenState extends State<BillingScreen> {
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant BillingScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.meter?.id != widget.meter?.id) _load();
  }

  void _load() {
    final meter = widget.meter;
    if (meter != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.read<BillingProvider>().loadBilling(meter.id);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.meter == null) return const NoMeterPlaceholder();

    return Consumer<BillingProvider>(
      builder: (context, billingProvider, _) {
        return AsyncStateView(
          loading: billingProvider.loading,
          error: billingProvider.error,
          onRetry: () => widget.meter != null ? billingProvider.loadBilling(widget.meter!.id) : null,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 640),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (billingProvider.cycle != null) _CycleCard(cycle: billingProvider.cycle!),
                  const SizedBox(height: 16),
                  if (billingProvider.estimate != null)
                    _EstimateCard(estimate: billingProvider.estimate!, solarMode: widget.meter!.solarMode),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _CycleCard extends StatelessWidget {
  final BillingCycle cycle;

  const _CycleCard({required this.cycle});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Current billing cycle', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('${formatDisplayDate(cycle.periodStart)} to ${formatDisplayDate(cycle.periodEnd)}'),
          ],
        ),
      ),
    );
  }
}

class _EstimateCard extends StatelessWidget {
  final BillEstimate estimate;
  final SolarMode solarMode;

  const _EstimateCard({required this.estimate, required this.solarMode});

  @override
  Widget build(BuildContext context) {
    if (!estimate.hasBreakdown) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(estimate.note ?? 'No readings yet for this cycle.'),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Estimated bill', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            _row('Total cycle units', formatUnits(estimate.totalEbUnits)),
            if (solarMode != SolarMode.none)
              _row('Total solar units', formatUnits(estimate.totalSolarUnits)),
            _row('Free/subsidized units', formatUnits(estimate.freeUnitsApplied!)),
            if (solarMode == SolarMode.onGrid)
              _row('Solar credit applied', formatUnits(estimate.solarUnitsOffset ?? 0)),
            _row('Chargeable units', formatUnits(estimate.chargeableUnits!)),
            const Divider(height: 24),
            Text('Slabs applied (${estimate.ruleGroup})', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            ...estimate.slabCharges.map(
              (slab) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${formatUnitsShort(slab.fromUnit)} - ${slab.toUnit == null ? '∞' : formatUnitsShort(slab.toUnit!)}'
                      ' @ ${formatCurrency(slab.ratePerUnit)}/unit',
                    ),
                    Text('${formatUnitsShort(slab.unitsCharged)} units = ${formatCurrency(slab.amount)}'),
                  ],
                ),
              ),
            ),
            const Divider(height: 24),
            _row('Fixed/other charges', formatCurrency(estimate.fixedCharge!)),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Total estimated bill', style: Theme.of(context).textTheme.titleMedium),
                Text(
                  formatCurrency(estimate.totalEstimatedAmount!),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Tariff: ${estimate.tariffPlanName} (effective ${formatDisplayDate(estimate.tariffEffectiveFrom!)})\n'
              'Source: ${estimate.tariffSourceReference}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [Text(label), Text(value)],
      ),
    );
  }
}
