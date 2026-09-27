import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../models/billing.dart';
import '../models/solar_mode.dart';

/// The full, transparent bill breakdown for one billing cycle. Per CLAUDE.md
/// section 5 ("Calculation transparency") every field is shown - never just
/// the final total. Used for both the current cycle and each past cycle in
/// the billing history, so both always display the same way.
class BillEstimateCard extends StatelessWidget {
  final BillEstimate estimate;
  final SolarMode solarMode;

  /// Heading shown above the breakdown, e.g. 'Estimated bill' for the
  /// running cycle or 'Estimated by app' for a past one.
  final String title;

  const BillEstimateCard({super.key, required this.estimate, required this.solarMode, this.title = 'Estimated bill'});

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
            Text(title, style: Theme.of(context).textTheme.titleMedium),
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
