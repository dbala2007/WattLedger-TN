import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../models/tariff.dart';
import '../services/tariff_service.dart';

class TariffProvider extends ChangeNotifier {
  final TariffApiService _service;

  TariffProvider(ApiClient client) : _service = TariffApiService(client);

  List<TariffPlan> _plans = [];
  bool _loading = false;
  String? _error;

  List<TariffPlan> get plans => _plans;
  bool get loading => _loading;
  String? get error => _error;

  /// Plans newest-effective-first, so the currently-active version is
  /// naturally at the top of the settings list.
  List<TariffPlan> get plansNewestFirst =>
      List<TariffPlan>.from(_plans)..sort((a, b) => b.effectiveFrom.compareTo(a.effectiveFrom));

  Future<void> loadPlans() async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      _plans = await _service.listTariffPlans();
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> createPlan({
    required String name,
    required String provider,
    required String consumerCategory,
    required DateTime effectiveFrom,
    DateTime? effectiveTo,
    required String billingFrequency,
    required double fixedCharge,
    required String sourceReference,
    required List<SubsidyRuleInput> subsidyRules,
    required List<TariffSlabInput> slabs,
  }) async {
    await _service.createTariffPlan(
      name: name,
      provider: provider,
      consumerCategory: consumerCategory,
      effectiveFrom: effectiveFrom,
      effectiveTo: effectiveTo,
      billingFrequency: billingFrequency,
      fixedCharge: fixedCharge,
      sourceReference: sourceReference,
      subsidyRules: subsidyRules,
      slabs: slabs,
    );
    await loadPlans();
  }

  Future<void> updatePlan({
    required String id,
    required String name,
    required String provider,
    required String consumerCategory,
    required DateTime effectiveFrom,
    DateTime? effectiveTo,
    required String billingFrequency,
    required double fixedCharge,
    required String sourceReference,
    required bool active,
    required List<SubsidyRuleInput> subsidyRules,
    required List<TariffSlabInput> slabs,
  }) async {
    await _service.updateTariffPlan(
      id: id,
      name: name,
      provider: provider,
      consumerCategory: consumerCategory,
      effectiveFrom: effectiveFrom,
      effectiveTo: effectiveTo,
      billingFrequency: billingFrequency,
      fixedCharge: fixedCharge,
      sourceReference: sourceReference,
      active: active,
      subsidyRules: subsidyRules,
      slabs: slabs,
    );
    await loadPlans();
  }

  /// Clears everything back to a fresh state - called on logout so a
  /// different user logging in afterwards never briefly sees the previous
  /// user's tariff plans before their own load completes.
  void reset() {
    _plans = [];
    _loading = false;
    _error = null;
    notifyListeners();
  }
}
