import '../core/json_helpers.dart';

class MeterReading {
  final String id;
  final String meterId;
  final DateTime readingDate;
  final double ebUnits;
  final double? ebBalance;
  final double? solarUnits;
  final double? solarBalance;
  final String? notes;

  MeterReading({
    required this.id,
    required this.meterId,
    required this.readingDate,
    required this.ebUnits,
    required this.ebBalance,
    required this.solarUnits,
    required this.solarBalance,
    required this.notes,
  });

  factory MeterReading.fromJson(Map<String, dynamic> json) {
    return MeterReading(
      id: json['id'] as String,
      meterId: json['meter_id'] as String,
      readingDate: parseDate(json['reading_date'] as String),
      ebUnits: parseDecimal(json['eb_units']),
      ebBalance: parseNullableDecimal(json['eb_balance']),
      solarUnits: parseNullableDecimal(json['solar_units']),
      solarBalance: parseNullableDecimal(json['solar_balance']),
      notes: json['notes'] as String?,
    );
  }
}
