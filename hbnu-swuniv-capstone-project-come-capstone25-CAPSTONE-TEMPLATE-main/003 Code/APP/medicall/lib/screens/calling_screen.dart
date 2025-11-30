import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/voice_chat_service.dart';
import '../providers/auth_provider.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}

class CallingScreen extends StatefulWidget {
  const CallingScreen({Key? key}) : super(key: key);

  @override
  State<CallingScreen> createState() => _CallingScreenState();
}

class _CallingScreenState extends State<CallingScreen> {
  final List<ChatMessage> _messages = [];
  final ScrollController _scrollController = ScrollController();
  
  bool _isInitializing = true;
  bool _isConnected = false;
  bool _isListening = false;
  bool _isSpeaking = false;
  bool _isProcessing = false;
  String _status = '초기화 중...';
  String? _currentUserInput = '';

  @override
  void initState() {
    super.initState();
    _initializeVoiceChat();
  }

  Future<void> _initializeVoiceChat() async {
    try {
      setState(() {
        _status = 'AI 상담사 연결 중...';
      });

      final success = await VoiceChatService.initialize();
      if (!success) {
        throw Exception('음성 채팅 서비스 초기화 실패');
      }

      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final userId = authProvider.currentUser?.id;
      
      if (userId == null) {
        throw Exception('사용자 정보를 찾을 수 없습니다');
      }

      final sessionData = await VoiceChatService.startConversation(userId);
      if (sessionData == null) {
        throw Exception('대화 세션 시작 실패');
      }

      setState(() {
        _isInitializing = false;
        _isConnected = true;
        _status = 'AI 상담사와 연결됨';
      });

      _addMessage('안녕하세요! AI 응급 상담사입니다. 어떤 응급 상황인지 말씀해 주세요.', false);

      await Future.delayed(const Duration(milliseconds: 500));
      _startListeningLoop();

    } catch (e) {
      setState(() {
        _isInitializing = false;
        _isConnected = false;
        _status = '연결 실패: ${e.toString()}';
      });
      
      _showErrorDialog('초기화 실패', e.toString());
    }
  }

  Future<void> _startListeningLoop() async {
    if (!_isConnected || _isListening || _isSpeaking) return;

    setState(() {
      _isListening = true;
      _status = '음성을 듣고 있습니다... (10초간 무음 시 자동 종료)';
      _currentUserInput = '';
    });

    try {
      final userText = await VoiceChatService.startListening();
      
      setState(() {
        _isListening = false;
        _currentUserInput = userText ?? '';
      });

      if (userText != null && userText.isNotEmpty) {
        _addMessage(userText, true);
        
        setState(() {
          _isProcessing = true;
          _status = 'AI가 답변을 생각하고 있습니다...';
          _currentUserInput = '';
        });

        final responseData = await VoiceChatService.sendMessage(userText);
        
        setState(() {
          _isProcessing = false;
        });

        if (responseData != null) {
          final aiResponse = responseData['ai_response'] as String;
          final isPrank = responseData['is_prank'] as bool? ?? false;
          
          _addMessage(aiResponse, false);
          
          if (isPrank) {
            _addMessage('[경고] 장난 전화가 감지되었습니다. 실제 응급상황에만 이용해 주세요.', false);
          }

          setState(() {
            _isSpeaking = true;
            _status = 'AI 상담사가 답변하고 있습니다...';
          });

          await VoiceChatService.speak(aiResponse);
          await VoiceChatService.waitForSpeechCompletion();

          setState(() {
            _isSpeaking = false;
          });

          await Future.delayed(const Duration(milliseconds: 500));
          _startListeningLoop();

        } else {
          setState(() {
            _status = 'AI 응답을 받지 못했습니다. 다시 말씀해 주세요.';
          });
          
          await Future.delayed(const Duration(seconds: 2));
          _startListeningLoop();
        }
      } else {
        setState(() {
          _status = '음성이 인식되지 않았습니다. 다시 말씀해 주세요.';
          _currentUserInput = '';
        });
        
        await Future.delayed(const Duration(seconds: 2));
        _startListeningLoop();
      }

    } catch (e) {
      setState(() {
        _isListening = false;
        _status = '음성 처리 중 오류가 발생했습니다.';
        _currentUserInput = '';
      });
      
      await Future.delayed(const Duration(seconds: 2));
      if (_isConnected) {
        _startListeningLoop();
      }
    }
  }

  void _addMessage(String text, bool isUser) {
    setState(() {
      _messages.add(ChatMessage(
        text: text,
        isUser: isUser,
        timestamp: DateTime.now(),
      ));
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _endCall() async {
    try {
      await VoiceChatService.stopListening();
      await VoiceChatService.stopSpeaking();
      
      setState(() {
        _isConnected = false;
        _isListening = false;
        _isSpeaking = false;
        _isProcessing = false;
        _status = '통화 종료 중...';
      });

      await VoiceChatService.endConversation();
      
      await VoiceChatService.dispose();

      if (mounted) {
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
      }
    }
  }

  void _showErrorDialog(String title, String message) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.pop(context);
            },
            child: const Text('확인'),
          ),
        ],
      ),
    );
  }

  Widget _buildChatMessage(ChatMessage message) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
      child: Row(
        mainAxisAlignment: message.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!message.isUser) ...[
            const CircleAvatar(
              radius: 16,
              backgroundColor: Colors.blue,
              child: Icon(Icons.support_agent, color: Colors.white, size: 16),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: message.isUser ? Colors.blue[600] : Colors.grey[200],
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                message.text,
                style: TextStyle(
                  color: message.isUser ? Colors.white : Colors.black87,
                  fontSize: 14,
                ),
              ),
            ),
          ),
          if (message.isUser) ...[
            const SizedBox(width: 8),
            const CircleAvatar(
              radius: 16,
              backgroundColor: Colors.green,
              child: Icon(Icons.person, color: Colors.white, size: 16),
            ),
          ],
        ],
      ),
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    VoiceChatService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () async {
        await _endCall();
        return false;
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: SafeArea(
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 40,
                      backgroundColor: _isConnected ? Colors.blue : Colors.grey,
                      child: Icon(
                        Icons.support_agent,
                        size: 40,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'AI 응급 상담사',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _status,
                      style: const TextStyle(
                        fontSize: 14,
                        color: Colors.white70,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    if (_isListening)
                      Container(
                        margin: const EdgeInsets.only(top: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.red.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.red, width: 1),
                        ),
                        child: const Text(
                          '음성 인식 중',
                          style: TextStyle(color: Colors.red, fontSize: 12),
                        ),
                      ),
                    if (_currentUserInput != null && _currentUserInput!.isNotEmpty)
                      Container(
                        margin: const EdgeInsets.only(top: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.blue.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.blue, width: 1),
                        ),
                        child: Text(
                          '인식된 내용: "$_currentUserInput"',
                          style: const TextStyle(
                            color: Colors.blue,
                            fontSize: 13,
                            fontStyle: FontStyle.italic,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.95),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.grey[100],
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(16),
                            topRight: Radius.circular(16),
                          ),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.chat, size: 16, color: Colors.grey),
                            const SizedBox(width: 8),
                            const Text(
                              '대화 기록',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: Colors.grey,
                              ),
                            ),
                            const Spacer(),
                            Text(
                              '총 ${_messages.length}개',
                              style: const TextStyle(
                                fontSize: 12,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: _messages.isEmpty
                            ? const Center(
                                child: Text(
                                  '대화를 시작해보세요',
                                  style: TextStyle(
                                    color: Colors.grey,
                                    fontSize: 16,
                                  ),
                                ),
                              )
                            : ListView.builder(
                                controller: _scrollController,
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                itemCount: _messages.length,
                                itemBuilder: (context, index) {
                                  return _buildChatMessage(_messages[index]);
                                },
                              ),
                      ),
                    ],
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    GestureDetector(
                      onTap: _isInitializing ? null : _endCall,
                      child: Container(
                        width: 70,
                        height: 70,
                        decoration: BoxDecoration(
                          color: _isInitializing ? Colors.grey : Colors.red,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: (_isInitializing ? Colors.grey : Colors.red).withOpacity(0.3),
                              spreadRadius: 5,
                              blurRadius: 10,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.call_end,
                          color: Colors.white,
                          size: 30,
                        ),
                      ),
                    ),                    
                    const SizedBox(height: 8),
                    
                    const Text(
                      '통화 종료',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}