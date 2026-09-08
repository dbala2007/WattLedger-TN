import '../core/api_client.dart';
import '../core/json_helpers.dart';
import '../models/reading.dart';

/// Talks to the backend's readings endpoints. Mirrors backend/app/api/readings.py.
class ReadingApiService {
  final ApiClient client;

  ReadingApiService(this.client);

  Future<List<MeterReading>> listReadings(String meterId, {DateTime? startDate, DateTime? endDate}) async {
    final query = <String, String>{};
    if (startDate != null) query['start_date'] = formatDateForApi(startDate);
    if (endDate != null) query['end_date'] = formatDateForApi(endDate);

    final json = await client.get('/meters/$meterId/readings', query: query);
    return (json as List<dynamic>).map((e) => MeterReading.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<MeterReading> createReading(
    String meterId, {
    required DateTime readingDate,
    required double ebUnits,
    double? solarUnits,
    String? notes,
  }) async {
    final json = await client.post('/meters/$meterId/readings', {
      'reading_date': formatDateForApi(readingDate),
      'eb_units': ebUnits,
      'solar_units': solarUnits,
      'notes': notes,
    });
    return MeterReading.fromJson(json as Map<String, dynamic>);
  }

  Future<MeterReading> updateReading(String readingId, {double? ebUnits, double? solarUnits, String? notes}) async {
    final body = <String, dynamic>{};
    if (ebUnits != null) body['eb_units'] = ebUnits;
    if (solarUnits != null) body['solar_units'] = solarUnits;
    if (notes != null) body['notes'] = notes;

    final json = await client.patch('/readings/$readingId', body);
    return MeterReading.fromJson(json as Map<String, dynamic>);
  }

  Future<void> deleteReading(String readingId) async {
    await client.delete('/readings/$readingId');
  }
}
