import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'dart:convert';

class VoiceChatService {
  static final SpeechToText _speechToText = SpeechToText();
  static final FlutterTts _flutterTts = FlutterTts();
  static bool _speechEnabled = false;
  static String? _currentSessionId;
  static bool _isInitialized = false;

  static const String baseUrl = 'http://10.0.2.2:5000/api'; // Android
  // static const String baseUrl = 'http://localhost:5000/api'; // iOS

  static Future<bool> initialize() async {
    if (_isInitialized) return true;

    try {
      final connectivityResult = await (Connectivity().checkConnectivity());
      if (connectivityResult == ConnectivityResult.none) {
        throw Exception('인터넷 연결이 필요합니다.');
      }

      final micPermission = await Permission.microphone.request();
      
      if (micPermission != PermissionStatus.granted) {
        throw Exception('마이크 권한이 필요합니다.');
      }

      _speechEnabled = await _speechToText.initialize(
        onError: (error) => print('STT 오류: $error'),
        onStatus: (status) => print('STT 상태: $status'),
      );
      
      if (!_speechEnabled) {
        throw Exception('음성 인식 초기화에 실패했습니다.');
      }

      try {
        await _flutterTts.setLanguage('ko-KR');
        await _flutterTts.setPitch(1.0);
        await _flutterTts.setSpeechRate(0.7);
        await _flutterTts.setVolume(0.9);
        
        await _flutterTts.awaitSpeakCompletion(true);
        
      } catch (e) {
        print('TTS 설정 오류: $e');
      }

      try {
        final engines = await _flutterTts.getEngines;
      } catch (e) {
        print('TTS 엔진 조회 생략: $e');
      }
      
      try {
        final languages = await _flutterTts.getLanguages;
      } catch (e) {
        print('TTS 언어 조회 생략: $e');
      }

      _isInitialized = true;
      return true;

    } catch (e) {
      print('초기화 실패: $e');
      return false;
    }
  }

  static Future<bool> checkConnectivity() async {
    final connectivityResult = await (Connectivity().checkConnectivity());
    return connectivityResult != ConnectivityResult.none;
  }

  static Future<Map<String, dynamic>?> startConversation(int userId) async {
    try {

      final response = await http.post(
        Uri.parse('$baseUrl/chat/start'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'user_id': userId}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          _currentSessionId = data['data']['session_id'];
          return data['data'];
        } else {
          throw Exception(data['message'] ?? '대화 시작 실패');
        }
      } else {
        throw Exception('서버 응답 오류: ${response.statusCode}');
      }
    } catch (e) {
      print('대화 시작 오류: $e');
      return null;
    }
  }

  static Future<String?> startListening() async {
    if (!_speechEnabled || _speechToText.isListening) {
      return null;
    }

    try {
      
      String recognizedText = '';
      String finalText = '';
      bool hasFinalResult = false;
      
      await _speechToText.listen(
        onResult: (result) {
          recognizedText = result.recognizedWords;
          print('STT 인식된 텍스트: $recognizedText (final: ${result.finalResult})');
          
          if (result.finalResult) {
            finalText = result.recognizedWords;
            hasFinalResult = true;
            print('STT 최종 결과 저장: $finalText');
          }
        },
        listenFor: const Duration(seconds: 60),
        pauseFor: const Duration(seconds: 10),
        localeId: 'ko_KR',
        partialResults: true,
        cancelOnError: false,
        listenMode: ListenMode.dictation,
      );

      while (_speechToText.isListening) {
        await Future.delayed(const Duration(milliseconds: 100));
      }

      await _speechToText.stop();
      
      await Future.delayed(const Duration(milliseconds: 800));
      
      final result = hasFinalResult ? finalText : recognizedText;
      
      
      return result.isNotEmpty ? result.trim() : null;

    } catch (e) {
      print('음성 청취 오류: $e');
      await _speechToText.stop();
      return null;
    }
  }

  static Future<void> stopListening() async {
    if (_speechToText.isListening) {
      await _speechToText.stop();
    }
  }

  static Future<Map<String, dynamic>?> sendMessage(String message) async {
    if (_currentSessionId == null) {
      print('세션 ID가 없습니다.');
      return null;
    }

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat/send'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'session_id': _currentSessionId,
          'message': message,
        }),
      ).timeout(const Duration(seconds: 25));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          return data['data'];
        } else {
          throw Exception(data['message'] ?? '메시지 전송 실패');
        }
      } else {
        throw Exception('서버 응답 오류: ${response.statusCode}');
      }
    } catch (e) {
      print('메시지 전송 오류: $e');
      return null;
    }
  }

  static Future<void> speak(String text) async {
    try {
      
      if (!_isInitialized) {
        return;
      }
      
      await _flutterTts.stop();
      
      await Future.delayed(const Duration(milliseconds: 100));
      
      final result = await _flutterTts.speak(text);
      
      await _flutterTts.awaitSpeakCompletion(true);
      
    } catch (e) {
      print('TTS 오류: $e');
    }
  }
  
  static Future<void> stopSpeaking() async {
    try {
      await _flutterTts.stop();
    } catch (e) {
      print('TTS 중단 오류: $e');
    }
  }

  static Future<void> waitForSpeechCompletion() async {
    try {
      await Future.delayed(const Duration(seconds: 1));
    } catch (e) {
      print('TTS 완료 대기 오류: $e');
    }
  }

  static Future<bool> endConversation() async {
    if (_currentSessionId == null) {
      print('세션 ID가 없습니다.');
      return false;
    }

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat/end'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'session_id': _currentSessionId}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          _currentSessionId = null;
          return true;
        }
      }
      
      print('대화 종료 실패');
      return false;

    } catch (e) {
      print('대화 종료 오류: $e');
      _currentSessionId = null;
      return false;
    }
  }

  static Future<void> dispose() async {
    try {
      await stopListening();
      await stopSpeaking();
      await endConversation();
      _isInitialized = false;
    } catch (e) {
      print('dispose 오류: $e');
    }
  }

  static bool get isListening => _speechToText.isListening;
  
  static String? get currentSessionId => _currentSessionId;
  
  static bool get isInitialized => _isInitialized;
} 