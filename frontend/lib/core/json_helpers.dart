// The backend serializes Decimal fields (eb_units, rates, etc.) as JSON
// strings, e.g. "12500.400" - not bare numbers - so precision survives the
// trip exactly. These helpers convert them back to Dart doubles for
// display/editing, and back to strings when sending values to the API.

double? parseNullableDecimal(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.parse(value);
  throw FormatException('Cannot parse decimal value: $value');
}

double parseDecimal(dynamic value) {
  final parsed = parseNullableDecimal(value);
  if (parsed == null) {
    throw const FormatException('Expected a decimal value but got null.');
  }
  return parsed;
}

DateTime parseDate(String value) => DateTime.parse(value);

DateTime? parseNullableDate(dynamic value) {
  if (value == null) return null;
  return DateTime.parse(value as String);
}

/// Formats a date as YYYY-MM-DD, the format the backend's `date` fields
/// expect in JSON request bodies.
String formatDateForApi(DateTime date) {
  final y = date.year.toString().padLeft(4, '0');
  final m = date.month.toString().padLeft(2, '0');
  final d = date.day.toString().padLeft(2, '0');
  return '$y-$m-$d';
}
