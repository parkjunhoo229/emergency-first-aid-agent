import 'package:geolocator/geolocator.dart';

class DistanceHelper {
  static String getFormattedDistance(
    double userLat,
    double userLng,
    double? hospitalLat,
    double? hospitalLng,
  ) {
    if (hospitalLat == null || hospitalLng == null) {
      return '거리 정보 없음';
    }

    try {
      double distanceInMeters = Geolocator.distanceBetween(
        userLat,
        userLng,
        hospitalLat,
        hospitalLng,
      );

      if (distanceInMeters < 1000) {
        return '${distanceInMeters.round()}m';
      } else {
        double distanceInKm = distanceInMeters / 1000;
        return '${distanceInKm.toStringAsFixed(1)}km';
      }
    } catch (e) {
      return '거리 계산 오류';
    }
  }

  static double getDistanceInMeters(
    double userLat,
    double userLng,
    double? hospitalLat,
    double? hospitalLng,
  ) {
    if (hospitalLat == null || hospitalLng == null) {
      return double.infinity;
    }

    try {
      return Geolocator.distanceBetween(
        userLat,
        userLng,
        hospitalLat,
        hospitalLng,
      );
    } catch (e) {
      return double.infinity;
    }
  }
} 