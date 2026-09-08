import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/tariff.dart';
import '../state/tariff_provider.dart';
import '../widgets/async_state_view.dart';
import 'tariff_form_screen.dart';

/// Tariff & Subsidy Settings screen (PRP.md section 11, screen 7). Lists
/// every tariff version, with a form to add a new one or edit an existing
/// one in place (see tariff_service.update_tariff_plan for why editing in
/// place is safe today but may need revisiting once real billing history
/// exists - CLAUDE.md section 5).
class TariffsScreen extends StatelessWidget {
  const TariffsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<TariffProvider>(
      builder: (context, tariffProvider, _) {
        return Scaffold(
          body: AsyncStateView(
            loading: tariffProvider.loading,
            error: tariffProvider.error,
            onRetry: tariffProvider.loadPlans,
            child: tariffProvider.plans.isEmpty
                ? const Center(child: Text('No tariff plans yet. Tap + to add one.'))
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: tariffProvider.plansNewestFirst.length,
                    itemBuilder: (context, index) => _PlanCard(plan: tariffProvider.plansNewestFirst[index]),
                  ),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const TariffFormScreen()),
              );
            },
            child: const Icon(Icons.add),
          ),
        );
      },
    );
  }
}

class _PlanCard extends StatelessWidget {
  final TariffPlan plan;

  const _PlanCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    final dateRange = plan.effectiveTo == null
        ? 'from ${formatDisplayDate(plan.effectiveFrom)}'
        : '${formatDisplayDate(plan.effectiveFrom)} to ${formatDisplayDate(plan.effectiveTo!)}';

    return Card(
      child: ExpansionTile(
        title: Row(
          children: [
            Expanded(child: Text('${plan.name}${plan.active ? '' : ' (inactive)'}')),
            IconButton(
              icon: const Icon(Icons.edit),
              tooltip: 'Edit',
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => TariffFormScreen(existingPlan: plan)),
                );
              },
            ),
          ],
        ),
        subtitle: Text('$dateRange | Fixed charge ${formatCurrency(plan.fixedCharge)}'),
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text('Source: ${plan.sourceReference}', style: Theme.of(context).textTheme.bodySmall),
          ),
          for (final rule in plan.subsidyRules)
            ListTile(
              dense: true,
              title: Text(rule.ruleName),
              subtitle: Text(
                '${formatUnits(rule.consumptionMin)} - '
                '${rule.consumptionMax == null ? "∞" : formatUnits(rule.consumptionMax!)}: '
                '${formatUnits(rule.freeUnits)} free',
              ),
            ),
          for (final group in plan.slabs.map((s) => s.ruleGroup).toSet())
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(group, style: Theme.of(context).textTheme.labelLarge),
                  for (final slab in plan.slabs.where((s) => s.ruleGroup == group))
                    Padding(
                      padding: const EdgeInsets.only(left: 8, bottom: 4),
                      child: Text(
                        '${formatUnitsShort(slab.fromUnit)} - '
                        '${slab.toUnit == null ? "∞" : formatUnitsShort(slab.toUnit!)} '
                        '@ ${formatCurrency(slab.ratePerUnit)}/unit',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                ],
              ),
            ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}
