import 'package:geolocator/geolocator.dart';

class GeolocatorHelper {
  static Future<Position> getCurrentLocation() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('위치 서비스가 비활성화되어 있습니다. 설정에서 위치 서비스를 활성화해주세요.');
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        throw Exception('위치 권한이 거부되었습니다.');
      }
    }
    
    if (permission == LocationPermission.deniedForever) {
      throw Exception('위치 권한이 영구적으로 거부되었습니다. 설정에서 권한을 허용해주세요.');
    }

    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 10,
          timeLimit: Duration(seconds: 15),
        ),
      ).timeout(
        const Duration(seconds: 20),
        onTimeout: () {
          throw Exception('위치 가져오기 시간이 초과되었습니다. AVD의 경우 Extended Controls > Location에서 위치를 설정해주세요.');
        },
      );
      
      if (position.latitude.isNaN || position.longitude.isNaN) {
        throw Exception('위치 데이터가 유효하지 않습니다 (NaN). AVD Extended Controls에서 위치를 다시 설정해주세요.');
      }
      
      if (position.latitude < -90 || position.latitude > 90 || 
          position.longitude < -180 || position.longitude > 180) {
        throw Exception('위치 데이터가 유효하지 않습니다 (범위 초과). lat: ${position.latitude}, lng: ${position.longitude}');
      }
      
      return position;
    } catch (e) {
      throw Exception('위치를 가져오는 중 오류가 발생했습니다: $e');
    }
  }
}