import '../core/json_helpers.dart';

class SubsidyRule {
  final String id;
  final String ruleName;
  final double consumptionMin;
  final double? consumptionMax;
  final double freeUnits;
  final DateTime effectiveFrom;
  final DateTime? effectiveTo;

  SubsidyRule({
    required this.id,
    required this.ruleName,
    required this.consumptionMin,
    required this.consumptionMax,
    required this.freeUnits,
    required this.effectiveFrom,
    required this.effectiveTo,
  });

  factory SubsidyRule.fromJson(Map<String, dynamic> json) {
    return SubsidyRule(
      id: json['id'] as String,
      ruleName: json['rule_name'] as String,
      consumptionMin: parseDecimal(json['consumption_min']),
      consumptionMax: parseNullableDecimal(json['consumption_max']),
      freeUnits: parseDecimal(json['free_units']),
      effectiveFrom: parseDate(json['effective_from'] as String),
      effectiveTo: parseNullableDate(json['effective_to']),
    );
  }
}

class TariffSlab {
  final String id;
  final String ruleGroup;
  final double fromUnit;
  final double? toUnit;
  final double ratePerUnit;
  final int sortOrder;

  TariffSlab({
    required this.id,
    required this.ruleGroup,
    required this.fromUnit,
    required this.toUnit,
    required this.ratePerUnit,
    required this.sortOrder,
  });

  factory TariffSlab.fromJson(Map<String, dynamic> json) {
    return TariffSlab(
      id: json['id'] as String,
      ruleGroup: json['rule_group'] as String,
      fromUnit: parseDecimal(json['from_unit']),
      toUnit: parseNullableDecimal(json['to_unit']),
      ratePerUnit: parseDecimal(json['rate_per_unit']),
      sortOrder: json['sort_order'] as int,
    );
  }
}

class TariffPlan {
  final String id;
  final String name;
  final String provider;
  final String consumerCategory;
  final DateTime effectiveFrom;
  final DateTime? effectiveTo;
  final String billingFrequency;
  final double fixedCharge;
  final String sourceReference;
  final bool active;
  final List<SubsidyRule> subsidyRules;
  final List<TariffSlab> slabs;

  TariffPlan({
    required this.id,
    required this.name,
    required this.provider,
    required this.consumerCategory,
    required this.effectiveFrom,
    required this.effectiveTo,
    required this.billingFrequency,
    required this.fixedCharge,
    required this.sourceReference,
    required this.active,
    required this.subsidyRules,
    required this.slabs,
  });

  factory TariffPlan.fromJson(Map<String, dynamic> json) {
    return TariffPlan(
      id: json['id'] as String,
      name: json['name'] as String,
      provider: json['provider'] as String,
      consumerCategory: json['consumer_category'] as String,
      effectiveFrom: parseDate(json['effective_from'] as String),
      effectiveTo: parseNullableDate(json['effective_to']),
      billingFrequency: json['billing_frequency'] as String,
      fixedCharge: parseDecimal(json['fixed_charge']),
      sourceReference: json['source_reference'] as String,
      active: json['active'] as bool,
      subsidyRules: (json['subsidy_rules'] as List<dynamic>? ?? [])
          .map((e) => SubsidyRule.fromJson(e as Map<String, dynamic>))
          .toList(),
      slabs: (json['slabs'] as List<dynamic>? ?? [])
          .map((e) => TariffSlab.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
