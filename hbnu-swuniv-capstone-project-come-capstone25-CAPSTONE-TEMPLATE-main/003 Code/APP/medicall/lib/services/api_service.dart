import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../models/user_model.dart';

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:5000/api'; // Android
  // static const String baseUrl = 'http://localhost:5000/api'; // iOS
  
  static const Duration timeout = Duration(seconds: 30);

  static Map<String, String> get headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  static Future<ApiResponse<Map<String, dynamic>>> healthCheck() async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/health'),
            headers: headers,
          )
          .timeout(timeout);

      final Map<String, dynamic> responseData = json.decode(response.body);
      
      return ApiResponse.fromJson(
        responseData,
        (data) => data as Map<String, dynamic>,
      );
    } on SocketException {
      throw ApiException('인터넷 연결을 확인해주세요.');
    } on HttpException {
      throw ApiException('서버 연결에 실패했습니다.');
    } catch (e) {
      throw ApiException('알 수 없는 오류가 발생했습니다: ${e.toString()}');
    }
  }

  static Future<ApiResponse<Map<String, dynamic>>> checkEmail(String email) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/check-email'),
            headers: headers,
            body: json.encode({'email': email}),
          )
          .timeout(timeout);

      final Map<String, dynamic> responseData = json.decode(response.body);
      
      return ApiResponse.fromJson(
        responseData,
        (data) => data as Map<String, dynamic>,
      );
    } on SocketException {
      throw ApiException('인터넷 연결을 확인해주세요.');
    } on HttpException {
      throw ApiException('서버 연결에 실패했습니다.');
    } catch (e) {
      throw ApiException('이메일 확인 중 오류가 발생했습니다: ${e.toString()}');
    }
  }

  static Future<ApiResponse<Map<String, dynamic>>> register(RegisterRequest request) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/register'),
            headers: headers,
            body: json.encode(request.toJson()),
          )
          .timeout(timeout);

      final Map<String, dynamic> responseData = json.decode(response.body);
      
      return ApiResponse.fromJson(
        responseData,
        (data) => data as Map<String, dynamic>,
      );
    } on SocketException {
      throw ApiException('인터넷 연결을 확인해주세요.');
    } on HttpException {
      throw ApiException('서버 연결에 실패했습니다.');
    } catch (e) {
      throw ApiException('회원가입 중 오류가 발생했습니다: ${e.toString()}');
    }
  }

  static Future<ApiResponse<Map<String, dynamic>>> login(LoginRequest request) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/login'),
            headers: headers,
            body: json.encode(request.toJson()),
          )
          .timeout(timeout);

      final Map<String, dynamic> responseData = json.decode(response.body);
      
      return ApiResponse.fromJson(
        responseData,
        (data) => data as Map<String, dynamic>,
      );
    } on SocketException {
      throw ApiException('인터넷 연결을 확인해주세요.');
    } on HttpException {
      throw ApiException('서버 연결에 실패했습니다.');
    } catch (e) {
      throw ApiException('로그인 중 오류가 발생했습니다: ${e.toString()}');
    }
  }

  static Future<ApiResponse<Map<String, dynamic>>> getUser(int userId) async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/user/$userId'),
            headers: headers,
          )
          .timeout(timeout);

      final Map<String, dynamic> responseData = json.decode(response.body);
      
      return ApiResponse.fromJson(
        responseData,
        (data) => data as Map<String, dynamic>,
      );
    } on SocketException {
      throw ApiException('인터넷 연결을 확인해주세요.');
    } on HttpException {
      throw ApiException('서버 연결에 실패했습니다.');
    } catch (e) {
      throw ApiException('사용자 정보 조회 중 오류가 발생했습니다: ${e.toString()}');
    }
  }

  static Future<ApiResponse<Map<String, dynamic>>> updateUser(
    int userId, 
    Map<String, dynamic> updateData
  ) async {
    try {
      final response = await http
          .put(
            Uri.parse('$baseUrl/user/$userId'),
            headers: headers,
            body: json.encode(updateData),
          )
          .timeout(timeout);

      final Map<String, dynamic> responseData = json.decode(response.body);
      
      return ApiResponse.fromJson(
        responseData,
        (data) => data as Map<String, dynamic>,
      );
    } on SocketException {
      throw ApiException('인터넷 연결을 확인해주세요.');
    } on HttpException {
      throw ApiException('서버 연결에 실패했습니다.');
    } catch (e) {
      throw ApiException('사용자 정보 수정 중 오류가 발생했습니다: ${e.toString()}');
    }
  }

  static void _handleResponse(http.Response response) {
    if (response.statusCode >= 400) {
      final Map<String, dynamic> errorData = json.decode(response.body);
      throw ApiException(errorData['message'] ?? '서버 오류가 발생했습니다.');
    }
  }
}

class ApiException implements Exception {
  final String message;
  
  ApiException(this.message);
  
  @override
  String toString() => message;
} 