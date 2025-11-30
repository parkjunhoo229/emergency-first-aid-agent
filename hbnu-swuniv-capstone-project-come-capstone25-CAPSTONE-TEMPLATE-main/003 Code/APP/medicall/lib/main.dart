import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:medicall/screens/intro_screen.dart';
import 'package:medicall/screens/login_screen.dart';
import 'package:medicall/screens/main_screen.dart' as main_screen;
import 'package:medicall/screens/mypage_screen.dart';
import 'package:medicall/screens/call_screen.dart';
import 'package:medicall/screens/register_primary_screen.dart';
import 'package:medicall/screens/hospital_list_screen.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'providers/auth_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await FlutterNaverMap().init(
      clientId: '8wjof4ifxn',
      onAuthFailed: (ex) => switch (ex) {
            NQuotaExceededException(:final message) =>
              print("사용량 초과 (message: $message)"),
            NUnauthorizedClientException() ||
            NClientUnspecifiedException() ||
            NAnotherAuthFailedException() =>
              print("인증 실패: $ex"),
          });
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context){
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
      ],
      child: MaterialApp(
        title: 'Medicall',
        home: const AppRouter(),
        routes: {
          '/intro': (context) => intro(),
          '/login': (context) => login(),
          '/main': (context) => const main_screen.MainScreen(),
          '/register': (context) => register(),
          '/mypage': (context) => mypage(),
          '/call': (context) => call(),
          '/hospital': (context) => hospitalFinder(),
        },
      ),
    );
  }

  Widget intro(){
    return IntroScreen();
  }

  Widget login(){
    return LoginScreen();
  }

  Widget mypage(){
    return MyPageScreen(
      name: '',
      email: '',
      phone: '',
      gender: '',
      birthYear: '',
      bloodType: '',
      emergencyContactRelation: '',
      emergencyContactName: '',
      emergencyContactPhone: '',
    );
  }

  Widget register(){
    return RegisterPrimaryScreen();
  }

  Widget call(){
    return CallScreen(
      name: '이름',
      gender: '성별',
      birthYear: '생년월일',
      bloodType: '혈액형',
    );
  }

  Widget hospitalFinder() {
    return const HospitalListScreen();
  }
}

class AppRouter extends StatefulWidget {
  const AppRouter({Key? key}) : super(key: key);

  @override
  _AppRouterState createState() => _AppRouterState();
}

class _AppRouterState extends State<AppRouter> {
  bool _isCheckingConnection = true;
  bool _isOnline = false;

  @override
  void initState() {
    super.initState();
    _checkConnectivityAndInitialize();
  }

  Future<void> _checkConnectivityAndInitialize() async {
    try {
      final connectivityResult = await (Connectivity().checkConnectivity());
      
      setState(() {
        _isOnline = connectivityResult != ConnectivityResult.none;
        _isCheckingConnection = false;
      });

      if (_isOnline) {
        if (mounted) {
          Provider.of<AuthProvider>(context, listen: false).initialize();
        }
      }
    } catch (e) {
      print('연결 상태 확인 중 오류: $e');
      setState(() {
        _isOnline = false;
        _isCheckingConnection = false;
      });
    }
  }

  Future<void> _retryConnection() async {
    setState(() {
      _isCheckingConnection = true;
    });
    
    await _checkConnectivityAndInitialize();
  }

  @override
  Widget build(BuildContext context) {
    if (_isCheckingConnection) {
      return const SplashScreen();
    }

    if (!_isOnline) {
      return OfflineScreen(onRetry: _retryConnection);
    }

    return Consumer<AuthProvider>(
      builder: (context, authProvider, child) {
        if (!authProvider.isInitialized) {
          return const SplashScreen();
        }
        
        if (authProvider.isAuthenticated) {
          return const main_screen.MainScreen();
        } else {
          return const IntroScreen();
        }
      },
    );
  }
}

class SplashScreen extends StatelessWidget {
  const SplashScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFF4A6FA5),
              Color(0xFF6B8DBD),
            ],
          ),
        ),
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Medicall',
                style: TextStyle(
                  fontSize: 48,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              SizedBox(height: 16),
              Text(
                '최고의 응급 상황 도우미',
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.white70,
                ),
              ),
              SizedBox(height: 48),
              CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class OfflineScreen extends StatelessWidget {
  final VoidCallback onRetry;
  
  const OfflineScreen({Key? key, required this.onRetry}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFF4A6FA5),
              Color(0xFF6B8DBD),
            ],
          ),
        ),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.wifi_off,
                  size: 80,
                  color: Colors.white,
                ),
                const SizedBox(height: 24),
                const Text(
                  '인터넷 연결 필요',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Medicall 앱을 사용하려면 인터넷 연결이 필요합니다.\n'
                  'Wi-Fi 또는 모바일 데이터를 활성화한 후 다시 시도해주세요.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white70,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 48),
                ElevatedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh, color: Colors.blue),
                  label: const Text(
                    '다시 시도',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.blue,
                    ),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(25),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  '응급 상황 시에는 112(경찰), 119(소방서), 1339(응급의료정보센터)로 직접 전화하세요.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white60,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
