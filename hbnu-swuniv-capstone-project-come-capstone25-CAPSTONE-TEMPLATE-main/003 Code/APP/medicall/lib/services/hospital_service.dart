import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/hospital.dart';

class HospitalService {
  static const String baseUrl = 'http://10.0.2.2:5000/api'; // Android
  // static const String baseUrl = 'http://localhost:5000/api'; // iOS

  static Future<List<Hospital>> getNearbyHospitals(double lat, double lng) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/hospitals/nearby'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'lat': lat,
          'lng': lng,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          final hospitalsJson = data['data']['hospitals'] as List;
          return hospitalsJson.map((json) => Hospital.fromJson(json)).toList();
        } else {
          throw Exception(data['message'] ?? '병원 정보를 가져오는데 실패했습니다.');
        }
      } else {
        throw Exception('서버 오류: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('네트워크 오류: $e');
    }
  }
} 