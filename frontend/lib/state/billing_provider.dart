import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../models/billing.dart';
import '../services/billing_service.dart';

/// Holds the current billing cycle, bill estimate, past-cycle history and
/// recorded meter reader visits for whichever meter is currently selected.
class BillingProvider extends ChangeNotifier {
  final BillingApiService _service;

  BillingProvider(ApiClient client) : _service = BillingApiService(client);

  BillingCycle? _cycle;
  BillEstimate? _estimate;
  List<PastCycleBill> _history = [];
  List<BillingAssessment> _assessments = [];
  bool _loading = false;
  String? _error;

  BillingCycle? get cycle => _cycle;
  BillEstimate? get estimate => _estimate;
  List<PastCycleBill> get history => _history;

  /// Newest visit first, for display.
  List<BillingAssessment> get assessmentsNewestFirst => _assessments.reversed.toList();
  bool get loading => _loading;
  String? get error => _error;

  Future<void> loadBilling(String meterId) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      // Run both requests together rather than one after another - neither
      // depends on the other's result, so there is no reason to wait twice.
      final results = await Future.wait([
        _service.getCurrentBillingCycle(meterId),
        _service.getBillEstimate(meterId),
        _service.getBillingHistory(meterId),
        _service.listAssessments(meterId),
      ]);
      _cycle = results[0] as BillingCycle;
      _estimate = results[1] as BillEstimate;
      _history = results[2] as List<PastCycleBill>;
      _assessments = results[3] as List<BillingAssessment>;
    } catch (e) {
      _error = e.toString();
      _cycle = null;
      _estimate = null;
      _history = [];
      _assessments = [];
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  // Each change to a visit moves cycle boundaries, so the current cycle,
  // estimate and history are all reloaded afterwards, not patched locally.
  // Errors are rethrown for the screen to show; the reload only runs on
  // success.

  Future<void> recordAssessment(String meterId,
      {required DateTime assessedOn, double? officialBillAmount, String? notes}) async {
    await _service.createAssessment(meterId,
        assessedOn: assessedOn, officialBillAmount: officialBillAmount, notes: notes);
    await loadBilling(meterId);
  }

  Future<void> updateAssessment(String meterId, String assessmentId,
      {required DateTime assessedOn, double? officialBillAmount, String? notes}) async {
    await _service.updateAssessment(meterId, assessmentId,
        assessedOn: assessedOn, officialBillAmount: officialBillAmount, notes: notes);
    await loadBilling(meterId);
  }

  Future<void> deleteAssessment(String meterId, String assessmentId) async {
    await _service.deleteAssessment(meterId, assessmentId);
    await loadBilling(meterId);
  }

  /// Clears everything back to a fresh state - called on logout so a
  /// different user logging in afterwards never briefly sees the previous
  /// user's billing data before their own load completes.
  void reset() {
    _cycle = null;
    _estimate = null;
    _history = [];
    _assessments = [];
    _loading = false;
    _error = null;
    notifyListeners();
  }
}
