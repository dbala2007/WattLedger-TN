import '../core/api_client.dart';
import '../core/json_helpers.dart';
import '../models/billing.dart';

/// Talks to the backend's billing-cycle and bill-estimate endpoints.
/// Mirrors backend/app/api/billing.py.
class BillingApiService {
  final ApiClient client;

  BillingApiService(this.client);

  Future<BillingCycle> getCurrentBillingCycle(String meterId, {DateTime? asOf}) async {
    final query = asOf == null ? null : {'as_of': formatDateForApi(asOf)};
    final json = await client.get('/meters/$meterId/billing-cycle/current', query: query);
    return BillingCycle.fromJson(json as Map<String, dynamic>);
  }

  Future<BillEstimate> getBillEstimate(String meterId, {DateTime? asOf}) async {
    final query = asOf == null ? null : {'as_of': formatDateForApi(asOf)};
    final json = await client.get('/meters/$meterId/bill-estimate', query: query);
    return BillEstimate.fromJson(json as Map<String, dynamic>);
  }
}
