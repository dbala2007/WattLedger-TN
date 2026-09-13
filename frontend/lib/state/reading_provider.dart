import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../models/reading.dart';
import '../services/reading_service.dart';

/// Holds the reading history for whichever meter is currently selected.
class ReadingProvider extends ChangeNotifier {
  final ReadingApiService _service;

  ReadingProvider(ApiClient client) : _service = ReadingApiService(client);

  List<MeterReading> _readings = [];
  bool _loading = false;
  String? _error;
  String? _loadedForMeterId;

  List<MeterReading> get readings => _readings;
  bool get loading => _loading;
  String? get error => _error;

  /// Readings sorted newest-first, the order a history screen wants.
  List<MeterReading> get readingsNewestFirst =>
      List<MeterReading>.from(_readings)..sort((a, b) => b.readingDate.compareTo(a.readingDate));

  Future<void> loadReadings(String meterId) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      _readings = await _service.listReadings(meterId);
      _loadedForMeterId = meterId;
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<MeterReading> addReading(
    String meterId, {
    required DateTime readingDate,
    required double ebUnits,
    double? solarUnits,
    String? notes,
  }) async {
    final created = await _service.createReading(
      meterId,
      readingDate: readingDate,
      ebUnits: ebUnits,
      solarUnits: solarUnits,
      notes: notes,
    );
    await loadReadings(meterId);
    return created;
  }

  Future<void> editReading(String readingId, {double? ebUnits, double? solarUnits, String? notes}) async {
    await _service.updateReading(readingId, ebUnits: ebUnits, solarUnits: solarUnits, notes: notes);
    if (_loadedForMeterId != null) {
      await loadReadings(_loadedForMeterId!);
    }
  }

  Future<void> removeReading(String readingId) async {
    await _service.deleteReading(readingId);
    if (_loadedForMeterId != null) {
      await loadReadings(_loadedForMeterId!);
    }
  }

  /// Clears everything back to a fresh state - called on logout so a
  /// different user logging in afterwards never briefly sees the previous
  /// user's readings before their own load completes.
  void reset() {
    _readings = [];
    _loading = false;
    _error = null;
    _loadedForMeterId = null;
    notifyListeners();
  }
}
