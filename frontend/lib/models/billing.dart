import '../core/json_helpers.dart';

class BillingCycle {
  final String meterId;
  final DateTime periodStart;
  final DateTime periodEnd;

  BillingCycle({required this.meterId, required this.periodStart, required this.periodEnd});

  factory BillingCycle.fromJson(Map<String, dynamic> json) {
    return BillingCycle(
      meterId: json['meter_id'] as String,
      periodStart: parseDate(json['period_start'] as String),
      periodEnd: parseDate(json['period_end'] as String),
    );
  }
}

class SlabCharge {
  final String ruleGroup;
  final double fromUnit;
  final double? toUnit;
  final double ratePerUnit;
  final double unitsCharged;
  final double amount;

  SlabCharge({
    required this.ruleGroup,
    required this.fromUnit,
    required this.toUnit,
    required this.ratePerUnit,
    required this.unitsCharged,
    required this.amount,
  });

  factory SlabCharge.fromJson(Map<String, dynamic> json) {
    return SlabCharge(
      ruleGroup: json['rule_group'] as String,
      fromUnit: parseDecimal(json['from_unit']),
      toUnit: parseNullableDecimal(json['to_unit']),
      ratePerUnit: parseDecimal(json['rate_per_unit']),
      unitsCharged: parseDecimal(json['units_charged']),
      amount: parseDecimal(json['amount']),
    );
  }
}

/// The full transparent bill breakdown - CLAUDE.md section 5 requires every
/// one of these fields to be shown, never just [totalEstimatedAmount] alone.
class BillEstimate {
  final String meterId;
  final DateTime periodStart;
  final DateTime periodEnd;
  final double totalEbUnits;
  final double totalSolarUnits;
  final int readingCount;
  final String? note;

  final String? ruleGroup;
  final double? freeUnitsApplied;
  final double? chargeableUnits;
  final List<SlabCharge> slabCharges;
  final double? fixedCharge;
  final double? totalEstimatedAmount;
  final String? tariffPlanId;
  final String? tariffPlanName;
  final DateTime? tariffEffectiveFrom;
  final String? tariffSourceReference;

  BillEstimate({
    required this.meterId,
    required this.periodStart,
    required this.periodEnd,
    required this.totalEbUnits,
    required this.totalSolarUnits,
    required this.readingCount,
    required this.note,
    required this.ruleGroup,
    required this.freeUnitsApplied,
    required this.chargeableUnits,
    required this.slabCharges,
    required this.fixedCharge,
    required this.totalEstimatedAmount,
    required this.tariffPlanId,
    required this.tariffPlanName,
    required this.tariffEffectiveFrom,
    required this.tariffSourceReference,
  });

  bool get hasBreakdown => totalEstimatedAmount != null;

  factory BillEstimate.fromJson(Map<String, dynamic> json) {
    return BillEstimate(
      meterId: json['meter_id'] as String,
      periodStart: parseDate(json['period_start'] as String),
      periodEnd: parseDate(json['period_end'] as String),
      totalEbUnits: parseDecimal(json['total_eb_units']),
      totalSolarUnits: parseDecimal(json['total_solar_units']),
      readingCount: json['reading_count'] as int,
      note: json['note'] as String?,
      ruleGroup: json['rule_group'] as String?,
      freeUnitsApplied: parseNullableDecimal(json['free_units_applied']),
      chargeableUnits: parseNullableDecimal(json['chargeable_units']),
      slabCharges: (json['slab_charges'] as List<dynamic>? ?? [])
          .map((e) => SlabCharge.fromJson(e as Map<String, dynamic>))
          .toList(),
      fixedCharge: parseNullableDecimal(json['fixed_charge']),
      totalEstimatedAmount: parseNullableDecimal(json['total_estimated_amount']),
      tariffPlanId: json['tariff_plan_id'] as String?,
      tariffPlanName: json['tariff_plan_name'] as String?,
      tariffEffectiveFrom: parseNullableDate(json['tariff_effective_from']),
      tariffSourceReference: json['tariff_source_reference'] as String?,
    );
  }
}
