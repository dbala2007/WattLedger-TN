import 'solar_mode.dart';

class Meter {
  final String id;
  final String meterNumber;
  final String? displayName;
  final SolarMode solarMode;
  final bool active;
  final DateTime? billingCycleReferenceDate;
  final int cycleLengthMonths;
  final DateTime? lastAssessmentDate;
  final DateTime? nextExpectedAssessmentDate;

  Meter({
    required this.id,
    required this.meterNumber,
    required this.displayName,
    required this.solarMode,
    required this.active,
    required this.billingCycleReferenceDate,
    required this.cycleLengthMonths,
    required this.lastAssessmentDate,
    required this.nextExpectedAssessmentDate,
  });

  /// Name shown in lists/dropdowns: the display name if one was set,
  /// otherwise the meter number.
  String get label => (displayName != null && displayName!.trim().isNotEmpty) ? displayName! : meterNumber;

  factory Meter.fromJson(Map<String, dynamic> json) {
    return Meter(
      id: json['id'] as String,
      meterNumber: json['meter_number'] as String,
      displayName: json['display_name'] as String?,
      solarMode: SolarMode.fromApi(json['solar_mode'] as String),
      active: json['active'] as bool,
      billingCycleReferenceDate: json['billing_cycle_reference_date'] == null
          ? null
          : DateTime.parse(json['billing_cycle_reference_date'] as String),
      cycleLengthMonths: json['cycle_length_months'] as int,
      lastAssessmentDate:
          json['last_assessment_date'] == null ? null : DateTime.parse(json['last_assessment_date'] as String),
      nextExpectedAssessmentDate: json['next_expected_assessment_date'] == null
          ? null
          : DateTime.parse(json['next_expected_assessment_date'] as String),
    );
  }
}
