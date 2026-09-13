import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../models/billing.dart';
import '../services/billing_service.dart';

/// Holds the current billing cycle and bill estimate for whichever meter is
/// currently selected.
class BillingProvider extends ChangeNotifier {
  final BillingApiService _service;

  BillingProvider(ApiClient client) : _service = BillingApiService(client);

  BillingCycle? _cycle;
  BillEstimate? _estimate;
  bool _loading = false;
  String? _error;

  BillingCycle? get cycle => _cycle;
  BillEstimate? get estimate => _estimate;
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
      ]);
      _cycle = results[0] as BillingCycle;
      _estimate = results[1] as BillEstimate;
    } catch (e) {
      _error = e.toString();
      _cycle = null;
      _estimate = null;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Clears everything back to a fresh state - called on logout so a
  /// different user logging in afterwards never briefly sees the previous
  /// user's billing data before their own load completes.
  void reset() {
    _cycle = null;
    _estimate = null;
    _loading = false;
    _error = null;
    notifyListeners();
  }
}
