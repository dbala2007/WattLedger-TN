import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../models/meter.dart';
import '../models/reading.dart';
import '../state/billing_provider.dart';
import '../state/reading_provider.dart';
import '../widgets/async_state_view.dart';
import '../widgets/no_meter_placeholder.dart';

/// Dashboard screen (PRP.md section 11, screen 1 / FR-008): today's EB
/// usage, today's solar balance, current-cycle EB usage, estimated current
/// bill, days since last reading, and a recent usage trend.
class DashboardScreen extends StatefulWidget {
  final Meter? meter;

  const DashboardScreen({super.key, required this.meter});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant DashboardScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.meter?.id != widget.meter?.id) _load();
  }

  void _load() {
    final meter = widget.meter;
    if (meter == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<ReadingProvider>().loadReadings(meter.id);
      context.read<BillingProvider>().loadBilling(meter.id);
    });
  }

  @override
  Widget build(BuildContext context) {
    final meter = widget.meter;
    if (meter == null) return const NoMeterPlaceholder();

    return Consumer2<ReadingProvider, BillingProvider>(
      builder: (context, readingProvider, billingProvider, _) {
        final loading = readingProvider.loading || billingProvider.loading;
        final error = readingProvider.error ?? billingProvider.error;

        return AsyncStateView(
          loading: loading,
          error: error,
          onRetry: _load,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 800),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(meter.label, style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 16),
                  _StatGrid(meter: meter, readings: readingProvider.readingsNewestFirst, billing: billingProvider),
                  const SizedBox(height: 24),
                  Text('Recent readings', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  _RecentTrend(readings: readingProvider.readingsNewestFirst.take(7).toList()),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _StatGrid extends StatelessWidget {
  final Meter meter;
  final List<MeterReading> readings;
  final BillingProvider billing;

  const _StatGrid({required this.meter, required this.readings, required this.billing});

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final todayReading = readings
        .where((r) => r.readingDate.year == now.year && r.readingDate.month == now.month && r.readingDate.day == now.day)
        .toList();
    final todayEb = todayReading.isEmpty ? null : todayReading.first.ebBalance;
    final todaySolar = todayReading.isEmpty ? null : todayReading.first.solarBalance;

    final daysSinceLastReading = readings.isEmpty ? null : now.difference(readings.first.readingDate).inDays;

    final estimate = billing.estimate;

    final cards = <_StatCardData>[
      _StatCardData('Today\'s EB usage', todayEb == null ? 'No reading today' : formatUnits(todayEb)),
      if (meter.solarMode.requiresSolarReading)
        _StatCardData('Today\'s solar', todaySolar == null ? 'No reading today' : formatUnits(todaySolar)),
      _StatCardData(
        'Current cycle EB usage',
        estimate == null ? '-' : formatUnits(estimate.totalEbUnits),
      ),
      _StatCardData(
        'Estimated current bill',
        (estimate == null || !estimate.hasBreakdown) ? '-' : formatCurrency(estimate.totalEstimatedAmount!),
      ),
      _StatCardData(
        'Days since last reading',
        daysSinceLastReading == null ? 'No readings yet' : '$daysSinceLastReading',
      ),
    ];

    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: cards.map((c) => _StatCard(data: c)).toList(),
    );
  }
}

class _StatCardData {
  final String label;
  final String value;

  _StatCardData(this.label, this.value);
}

class _StatCard extends StatelessWidget {
  final _StatCardData data;

  const _StatCard({required this.data});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(data.label, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 8),
              Text(data.value, style: Theme.of(context).textTheme.titleLarge),
            ],
          ),
        ),
      ),
    );
  }
}

class _RecentTrend extends StatelessWidget {
  final List<MeterReading> readings;

  const _RecentTrend({required this.readings});

  @override
  Widget build(BuildContext context) {
    if (readings.isEmpty) {
      return const Text('No readings yet.');
    }
    final maxBalance = readings
        .map((r) => r.ebBalance ?? 0)
        .fold<double>(0, (max, v) => v > max ? v : max);

    return Column(
      children: readings.map((reading) {
        final balance = reading.ebBalance ?? 0;
        final fraction = maxBalance == 0 ? 0.0 : (balance / maxBalance).clamp(0.0, 1.0);
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              SizedBox(width: 90, child: Text(formatDisplayDate(reading.readingDate))),
              Expanded(
                child: FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: fraction == 0 ? 0.02 : fraction,
                  child: Container(
                    height: 14,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primary,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 90,
                child: Text(
                  reading.ebBalance == null ? '-' : formatUnits(reading.ebBalance!),
                  textAlign: TextAlign.right,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
