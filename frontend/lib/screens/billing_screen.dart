import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/billing.dart';
import '../models/meter.dart';
import '../state/billing_provider.dart';
import '../widgets/async_state_view.dart';
import '../widgets/bill_estimate_card.dart';
import '../widgets/billing_history_section.dart';
import '../widgets/no_meter_placeholder.dart';

/// Combines the Billing Cycle Summary and Estimated EB Bill screens
/// (PRP.md section 11, screens 5 and 6) - they show the same underlying
/// cycle, so one screen avoids duplicating the period-start/end header.
/// Below the current cycle, [BillingHistorySection] lists past cycles and
/// the meter reader visits that define them.
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
                    BillEstimateCard(estimate: billingProvider.estimate!, solarMode: widget.meter!.solarMode),
                  const SizedBox(height: 32),
                  BillingHistorySection(meter: widget.meter!),
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
