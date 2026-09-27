import '../core/api_client.dart';
import '../core/json_helpers.dart';
import '../models/billing.dart';

/// Talks to the backend's billing-cycle, bill-estimate, billing-history
/// and assessment (meter reader visit) endpoints.
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

  /// Completed past cycles, newest first, each with its full breakdown.
  Future<List<PastCycleBill>> getBillingHistory(String meterId) async {
    final json = await client.get('/meters/$meterId/billing-history') as List<dynamic>;
    return json.map((e) => PastCycleBill.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<BillingAssessment>> listAssessments(String meterId) async {
    final json = await client.get('/meters/$meterId/assessments') as List<dynamic>;
    return json.map((e) => BillingAssessment.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<BillingAssessment> createAssessment(
    String meterId, {
    required DateTime assessedOn,
    double? officialBillAmount,
    String? notes,
  }) async {
    final json = await client.post(
      '/meters/$meterId/assessments',
      _assessmentBody(assessedOn, officialBillAmount, notes),
    );
    return BillingAssessment.fromJson(json as Map<String, dynamic>);
  }

  /// Full replace - a null [officialBillAmount] or [notes] clears it.
  Future<BillingAssessment> updateAssessment(
    String meterId,
    String assessmentId, {
    required DateTime assessedOn,
    double? officialBillAmount,
    String? notes,
  }) async {
    final json = await client.put(
      '/meters/$meterId/assessments/$assessmentId',
      _assessmentBody(assessedOn, officialBillAmount, notes),
    );
    return BillingAssessment.fromJson(json as Map<String, dynamic>);
  }

  Future<void> deleteAssessment(String meterId, String assessmentId) =>
      client.delete('/meters/$meterId/assessments/$assessmentId');

  Map<String, dynamic> _assessmentBody(DateTime assessedOn, double? officialBillAmount, String? notes) {
    return {
      'assessed_on': formatDateForApi(assessedOn),
      // Sent as a string so the backend's Decimal gets the exact value.
      'official_bill_amount': officialBillAmount?.toStringAsFixed(2),
      'notes': (notes == null || notes.trim().isEmpty) ? null : notes.trim(),
    };
  }
}
