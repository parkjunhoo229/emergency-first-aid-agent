import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/user_model.dart';
import '../services/api_service.dart';

class AuthProvider with ChangeNotifier {
  User? _currentUser;
  bool _isLoading = false;
  bool _isInitialized = false;
  bool _isFirstVisit = true;
  String? _errorMessage;

  User? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  bool get isFirstVisit => _isFirstVisit;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _currentUser != null;

  static const String _userKey = 'current_user';
  static const String _emailKey = 'saved_email';
  static const String _firstVisitKey = 'first_visit';

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void _setError(String? error) {
    _errorMessage = error;
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  //앱 시작 시 초기화
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      _setLoading(true);
      final prefs = await SharedPreferences.getInstance();
      
      _isFirstVisit = prefs.getBool(_firstVisitKey) ?? true;
      
      final userJson = prefs.getString(_userKey);
      
      if (userJson != null) {
        final userData = json.decode(userJson);
        _currentUser = User.fromJson(userData);
        
        await refreshUser();
      }
    } catch (e) {
      print('초기화 중 오류: $e');
      await _clearStoredUser();
    } finally {
      _isInitialized = true;
      _setLoading(false);
    }
  }

  //사용자 정보 저장
  Future<void> _saveUser(User user) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final userJson = json.encode(user.toJson());
      await prefs.setString(_userKey, userJson);
    } catch (e) {
      print('사용자 정보 저장 중 오류: $e');
    }
  }

  Future<void> _clearStoredUser() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_userKey);
    } catch (e) {
      print('사용자 정보 제거 중 오류: $e');
    }
  }

  //이메일 저장
  Future<void> _saveEmail(String email) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_emailKey, email);
    } catch (e) {
      print('이메일 저장 중 오류: $e');
    }
  }

  //저장된 이메일 가져오기
  Future<String?> getSavedEmail() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(_emailKey);
    } catch (e) {
      print('이메일 가져오기 중 오류: $e');
      return null;
    }
  }

  //이메일 중복 확인
  Future<bool> checkEmailAvailability(String email) async {
    try {
      _setLoading(true);
      _setError(null);

      final response = await ApiService.checkEmail(email);
      
      if (response.success && response.data != null) {
        return response.data!['available'] as bool;
      } else {
        _setError(response.message);
        return false;
      }
    } catch (e) {
      _setError(e.toString());
      return false;
    } finally {
      _setLoading(false);
    }
  }

  //회원가입
  Future<bool> register(RegisterRequest request) async {
    try {
      _setLoading(true);
      _setError(null);

      final response = await ApiService.register(request);
      
      if (response.success && response.data != null) {
        final userData = response.data!['user'] as Map<String, dynamic>;
        _currentUser = User.fromJson(userData);
        
        await _saveUser(_currentUser!);
        await _saveEmail(request.email);
        
        notifyListeners();
        return true;
      } else {
        _setError(response.message);
        return false;
      }
    } catch (e) {
      _setError(e.toString());
      return false;
    } finally {
      _setLoading(false);
    }
  }

  //로그인
  Future<bool> login(String email, String password) async {
    try {
      _setLoading(true);
      _setError(null);

      final request = LoginRequest(email: email, password: password);
      final response = await ApiService.login(request);
      
      if (response.success && response.data != null) {
        final userData = response.data!['user'] as Map<String, dynamic>;
        _currentUser = User.fromJson(userData);
        
        await _saveUser(_currentUser!);
        await _saveEmail(email);
        
        notifyListeners();
        return true;
      } else {
        _setError(response.message);
        return false;
      }
    } catch (e) {
      _setError(e.toString());
      return false;
    } finally {
      _setLoading(false);
    }
  }

  //로그아웃
  Future<void> logout() async {
    _currentUser = null;
    _errorMessage = null;
    await _clearStoredUser();
    
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_firstVisitKey, true);
      _isFirstVisit = true;
    } catch (e) {
      print('첫 방문 상태 재설정 중 오류: $e');
    }
    
    notifyListeners();
  }

  //사용자 정보 새로고침
  Future<bool> refreshUser() async {
    if (_currentUser == null) return false;

    try {
      _setLoading(true);
      _setError(null);

      final response = await ApiService.getUser(_currentUser!.id);
      
      if (response.success && response.data != null) {
        final userData = response.data!['user'] as Map<String, dynamic>;
        _currentUser = User.fromJson(userData);
        
        await _saveUser(_currentUser!);
        
        notifyListeners();
        return true;
      } else {
        _setError(response.message);
        return false;
      }
    } catch (e) {
      _setError(e.toString());
      return false;
    } finally {
      _setLoading(false);
    }
  }

  //사용자 정보 업데이트
  Future<bool> updateUser(Map<String, dynamic> updateData) async {
    if (_currentUser == null) return false;

    try {
      _setLoading(true);
      _setError(null);

      final response = await ApiService.updateUser(_currentUser!.id, updateData);
      
      if (response.success && response.data != null) {
        final userData = response.data!['user'] as Map<String, dynamic>;
        _currentUser = User.fromJson(userData);
        
        await _saveUser(_currentUser!);
        
        notifyListeners();
        return true;
      } else {
        _setError(response.message);
        return false;
      }
    } catch (e) {
      _setError(e.toString());
      return false;
    } finally {
      _setLoading(false);
    }
  }

  //첫 방문 완료 처리
  Future<void> completeFirstVisit() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_firstVisitKey, false);
      _isFirstVisit = false;
      notifyListeners();
    } catch (e) {
      print('첫 방문 완료 처리 중 오류: $e');
    }
  }
} 