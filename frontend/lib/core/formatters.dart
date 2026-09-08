import 'package:intl/intl.dart';

/// India-friendly display formatting - NFR-007 requires INR currency, kWh
/// units, and India-style dates rather than the ISO/US defaults.
final DateFormat _displayDateFormat = DateFormat('dd MMM yyyy');
final NumberFormat _currencyFormat = NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 2);
final NumberFormat _unitsFormat = NumberFormat('#,##0.0##');

String formatDisplayDate(DateTime date) => _displayDateFormat.format(date);

String formatCurrency(double amount) => _currencyFormat.format(amount);

String formatUnits(double units) => '${_unitsFormat.format(units)} units';

String formatUnitsShort(double units) => _unitsFormat.format(units);
