import '../core/api_client.dart';
import '../core/json_helpers.dart';
import '../models/meter.dart';
import '../models/solar_mode.dart';

/// Talks to the backend's /meters endpoints. Mirrors backend/app/api/meters.py.
class MeterApiService {
  final ApiClient client;

  MeterApiService(this.client);

  Future<List<Meter>> listMeters({bool activeOnly = false}) async {
    final json = await client.get('/meters', query: {'active_only': activeOnly.toString()});
    return (json as List<dynamic>).map((e) => Meter.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Meter> getMeter(String id) async {
    final json = await client.get('/meters/$id');
    return Meter.fromJson(json as Map<String, dynamic>);
  }

  Future<Meter> createMeter({
    required String meterNumber,
    String? displayName,
    SolarMode solarMode = SolarMode.none,
    DateTime? billingCycleReferenceDate,
    int cycleLengthMonths = 2,
  }) async {
    final json = await client.post('/meters', {
      'meter_number': meterNumber,
      'display_name': displayName,
      'solar_mode': solarMode.apiValue,
      'billing_cycle_reference_date':
          billingCycleReferenceDate == null ? null : formatDateForApi(billingCycleReferenceDate),
      'cycle_length_months': cycleLengthMonths,
    });
    return Meter.fromJson(json as Map<String, dynamic>);
  }

  Future<Meter> updateMeter(
    String id, {
    String? displayName,
    SolarMode? solarMode,
    bool? active,
    DateTime? billingCycleReferenceDate,
    int? cycleLengthMonths,
    DateTime? lastAssessmentDate,
    DateTime? nextExpectedAssessmentDate,
  }) async {
    final body = <String, dynamic>{};
    if (displayName != null) body['display_name'] = displayName;
    if (solarMode != null) body['solar_mode'] = solarMode.apiValue;
    if (active != null) body['active'] = active;
    if (billingCycleReferenceDate != null) {
      body['billing_cycle_reference_date'] = formatDateForApi(billingCycleReferenceDate);
    }
    if (cycleLengthMonths != null) body['cycle_length_months'] = cycleLengthMonths;
    if (lastAssessmentDate != null) body['last_assessment_date'] = formatDateForApi(lastAssessmentDate);
    if (nextExpectedAssessmentDate != null) {
      body['next_expected_assessment_date'] = formatDateForApi(nextExpectedAssessmentDate);
    }

    final json = await client.patch('/meters/$id', body);
    return Meter.fromJson(json as Map<String, dynamic>);
  }
}
