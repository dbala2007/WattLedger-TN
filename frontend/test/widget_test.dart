// The default counter-app smoke test doesn't apply to WattLedger TN, and a
// full widget test would need a mocked backend (the real providers call the
// live API on creation). For now this covers the pure formatting helpers,
// which need no network and are easy to get subtly wrong (currency/units
// display per NFR-007).

import 'package:flutter_test/flutter_test.dart';
import 'package:wattledger_flutter/core/formatters.dart';

void main() {
  test('formatCurrency shows INR symbol and two decimal places', () {
    expect(formatCurrency(1250), '₹1,250.00');
  });

  test('formatUnits shows up to three decimal places with a units suffix', () {
    expect(formatUnits(8.5), '8.5 units');
  });

  test('formatUnitsShort has no units suffix', () {
    expect(formatUnitsShort(300), '300.0');
  });
}
