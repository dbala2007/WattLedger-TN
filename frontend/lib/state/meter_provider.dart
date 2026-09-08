import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../models/meter.dart';
import '../models/solar_mode.dart';
import '../services/meter_service.dart';

/// Holds the list of meters and which one is currently selected, so every
/// screen (dashboard, reading entry, history, billing) agrees on "which
/// meter am I looking at" without passing it through every widget by hand.
class MeterProvider extends ChangeNotifier {
  final MeterApiService _service;

  MeterProvider(ApiClient client) : _service = MeterApiService(client);

  List<Meter> _meters = [];
  Meter? _selected;
  bool _loading = false;
  String? _error;

  List<Meter> get meters => _meters;
  Meter? get selected => _selected;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> loadMeters() async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      _meters = await _service.listMeters();
      if (_selected == null && _meters.isNotEmpty) {
        _selected = _meters.first;
      } else if (_selected != null) {
        // Keep the selection in sync with the freshly-loaded copy (e.g.
        // after an edit) rather than pointing at stale data.
        final match = _meters.where((m) => m.id == _selected!.id);
        _selected = match.isEmpty ? (_meters.isEmpty ? null : _meters.first) : match.first;
      }
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void selectMeter(Meter meter) {
    _selected = meter;
    notifyListeners();
  }

  Future<Meter> createMeter({
    required String meterNumber,
    String? displayName,
    SolarMode solarMode = SolarMode.none,
    DateTime? billingCycleReferenceDate,
    int cycleLengthMonths = 2,
  }) async {
    final created = await _service.createMeter(
      meterNumber: meterNumber,
      displayName: displayName,
      solarMode: solarMode,
      billingCycleReferenceDate: billingCycleReferenceDate,
      cycleLengthMonths: cycleLengthMonths,
    );
    await loadMeters();
    _selected = created;
    notifyListeners();
    return created;
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
    final updated = await _service.updateMeter(
      id,
      displayName: displayName,
      solarMode: solarMode,
      active: active,
      billingCycleReferenceDate: billingCycleReferenceDate,
      cycleLengthMonths: cycleLengthMonths,
      lastAssessmentDate: lastAssessmentDate,
      nextExpectedAssessmentDate: nextExpectedAssessmentDate,
    );
    await loadMeters();
    return updated;
  }
}
