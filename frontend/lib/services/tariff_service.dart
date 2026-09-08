import '../core/api_client.dart';
import '../core/json_helpers.dart';
import '../models/tariff.dart';

/// Input shape for creating one subsidy rule as part of a new tariff plan.
class SubsidyRuleInput {
  final String ruleName;
  final double consumptionMin;
  final double? consumptionMax;
  final double freeUnits;
  final DateTime effectiveFrom;
  final DateTime? effectiveTo;

  SubsidyRuleInput({
    required this.ruleName,
    required this.consumptionMin,
    required this.consumptionMax,
    required this.freeUnits,
    required this.effectiveFrom,
    this.effectiveTo,
  });

  Map<String, dynamic> toJson() => {
        'rule_name': ruleName,
        'consumption_min': consumptionMin,
        'consumption_max': consumptionMax,
        'free_units': freeUnits,
        'effective_from': formatDateForApi(effectiveFrom),
        'effective_to': effectiveTo == null ? null : formatDateForApi(effectiveTo!),
      };
}

/// Input shape for creating one slab as part of a new tariff plan.
class TariffSlabInput {
  final String ruleGroup;
  final double fromUnit;
  final double? toUnit;
  final double ratePerUnit;
  final int sortOrder;

  TariffSlabInput({
    required this.ruleGroup,
    required this.fromUnit,
    required this.toUnit,
    required this.ratePerUnit,
    required this.sortOrder,
  });

  Map<String, dynamic> toJson() => {
        'rule_group': ruleGroup,
        'from_unit': fromUnit,
        'to_unit': toUnit,
        'rate_per_unit': ratePerUnit,
        'sort_order': sortOrder,
      };
}

/// Talks to the backend's /tariffs endpoints. Mirrors backend/app/api/tariffs.py.
class TariffApiService {
  final ApiClient client;

  TariffApiService(this.client);

  Future<List<TariffPlan>> listTariffPlans({String? consumerCategory}) async {
    final query = consumerCategory == null ? null : {'consumer_category': consumerCategory};
    final json = await client.get('/tariffs', query: query);
    return (json as List<dynamic>).map((e) => TariffPlan.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<TariffPlan> getTariffPlan(String id) async {
    final json = await client.get('/tariffs/$id');
    return TariffPlan.fromJson(json as Map<String, dynamic>);
  }

  Future<TariffPlan> createTariffPlan({
    required String name,
    String provider = 'TANGEDCO',
    String consumerCategory = 'DOMESTIC',
    required DateTime effectiveFrom,
    DateTime? effectiveTo,
    String billingFrequency = 'BI_MONTHLY',
    double fixedCharge = 0,
    required String sourceReference,
    bool active = true,
    required List<SubsidyRuleInput> subsidyRules,
    required List<TariffSlabInput> slabs,
  }) async {
    final json = await client.post('/tariffs', {
      'name': name,
      'provider': provider,
      'consumer_category': consumerCategory,
      'effective_from': formatDateForApi(effectiveFrom),
      'effective_to': effectiveTo == null ? null : formatDateForApi(effectiveTo),
      'billing_frequency': billingFrequency,
      'fixed_charge': fixedCharge,
      'source_reference': sourceReference,
      'active': active,
      'subsidy_rules': subsidyRules.map((r) => r.toJson()).toList(),
      'slabs': slabs.map((s) => s.toJson()).toList(),
    });
    return TariffPlan.fromJson(json as Map<String, dynamic>);
  }

  /// Replaces an existing plan's fields, subsidy rules, and slabs. Unlike
  /// updateMeter this isn't a partial patch - the full set of fields, rules,
  /// and slabs must be sent, same shape as createTariffPlan.
  Future<TariffPlan> updateTariffPlan({
    required String id,
    required String name,
    String provider = 'TANGEDCO',
    String consumerCategory = 'DOMESTIC',
    required DateTime effectiveFrom,
    DateTime? effectiveTo,
    String billingFrequency = 'BI_MONTHLY',
    double fixedCharge = 0,
    required String sourceReference,
    bool active = true,
    required List<SubsidyRuleInput> subsidyRules,
    required List<TariffSlabInput> slabs,
  }) async {
    final json = await client.patch('/tariffs/$id', {
      'name': name,
      'provider': provider,
      'consumer_category': consumerCategory,
      'effective_from': formatDateForApi(effectiveFrom),
      'effective_to': effectiveTo == null ? null : formatDateForApi(effectiveTo),
      'billing_frequency': billingFrequency,
      'fixed_charge': fixedCharge,
      'source_reference': sourceReference,
      'active': active,
      'subsidy_rules': subsidyRules.map((r) => r.toJson()).toList(),
      'slabs': slabs.map((s) => s.toJson()).toList(),
    });
    return TariffPlan.fromJson(json as Map<String, dynamic>);
  }
}
