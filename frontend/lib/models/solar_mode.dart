/// Mirrors app.models.enums.SolarMode on the backend - keep these two in
/// sync if the backend enum ever changes.
enum SolarMode {
  none('NONE', 'No solar'),
  onGrid('ON_GRID', 'On-grid solar'),
  offGrid('OFF_GRID', 'Off-grid solar');

  final String apiValue;
  final String label;

  const SolarMode(this.apiValue, this.label);

  static SolarMode fromApi(String value) {
    return SolarMode.values.firstWhere(
      (mode) => mode.apiValue == value,
      orElse: () => throw FormatException('Unknown solar_mode: $value'),
    );
  }

  bool get requiresSolarReading => this != SolarMode.none;
}
