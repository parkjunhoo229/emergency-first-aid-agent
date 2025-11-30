import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:medicall/screens/register_primary_screen.dart';
import 'package:medicall/providers/auth_provider.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  bool _obscurePassword = true;
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    );
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeIn,
      ),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Center(
              child: SingleChildScrollView(
                child: FadeTransition(
                  opacity: _fadeAnimation,
                  child: Consumer<AuthProvider>(
                    builder: (context, authProvider, child) {
                      return Form(
                        key: _formKey,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const Text(
                              'Medicall',
                              style: TextStyle(
                                fontSize: 48,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF4A6FA5),
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              '최고의 응급 상황 도우미',
                              style: TextStyle(
                                fontSize: 16,
                                color: Color(0xFF6B8DBD),
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 48),

                            if (authProvider.errorMessage != null)
                              Container(
                                margin: const EdgeInsets.only(bottom: 16),
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: Colors.red.shade50,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: Colors.red.shade200),
                                ),
                                child: Row(
                                  children: [
                                    Icon(Icons.error, color: Colors.red.shade600, size: 20),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        authProvider.errorMessage!,
                                        style: TextStyle(color: Colors.red.shade700),
                                      ),
                                    ),
                                    IconButton(
                                      icon: const Icon(Icons.close, size: 18),
                                      onPressed: () => authProvider.clearError(),
                                      padding: EdgeInsets.zero,
                                      constraints: const BoxConstraints(),
                                    ),
                                  ],
                                ),
                              ),

                            Card(
                              elevation: 4,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              color: Colors.white.withOpacity(0.9),
                              child: Padding(
                                padding: const EdgeInsets.all(16.0),
                                child: Column(
                                  children: [
                                    TextFormField(
                                      controller: _emailController,
                                      decoration: InputDecoration(
                                        labelText: '이메일',
                                        hintText: 'your.email@example.com',
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        prefixIcon: const Icon(Icons.email),
                                        filled: true,
                                        fillColor: Colors.white.withOpacity(0.7),
                                      ),
                                      keyboardType: TextInputType.emailAddress,
                                      autofillHints: const [AutofillHints.email],
                                      validator: (value) {
                                        if (value == null || value.isEmpty) {
                                          return '이메일을 입력해주세요';
                                        }
                                        final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
                                        if (!emailRegex.hasMatch(value)) {
                                          return '올바른 이메일 형식을 입력해주세요';
                                        }
                                        return null;
                                      },
                                    ),
                                    const SizedBox(height: 16),
                                    TextFormField(
                                      controller: _passwordController,
                                      decoration: InputDecoration(
                                        labelText: '비밀번호',
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        prefixIcon: const Icon(Icons.lock),
                                        suffixIcon: IconButton(
                                          icon: Icon(
                                            _obscurePassword ? Icons.visibility : Icons.visibility_off,
                                          ),
                                          onPressed: () {
                                            setState(() {
                                              _obscurePassword = !_obscurePassword;
                                            });
                                          },
                                        ),
                                        filled: true,
                                        fillColor: Colors.white.withOpacity(0.7),
                                      ),
                                      obscureText: _obscurePassword,
                                      autofillHints: const [AutofillHints.password],
                                      validator: (value) {
                                        if (value == null || value.isEmpty) {
                                          return '비밀번호를 입력해주세요';
                                        }
                                        return null;
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 24),

                            AnimatedContainer(
                              duration: const Duration(milliseconds: 300),
                              height: 50,
                              child: ElevatedButton(
                                onPressed: authProvider.isLoading ? null : _handleLogin,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF4A6FA5),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  elevation: 4,
                                ),
                                child: authProvider.isLoading
                                    ? const CircularProgressIndicator(color: Colors.white)
                                    : const Text(
                                        '로그인',
                                        style: TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.white,
                                        ),
                                      ),
                              ),
                            ),
                            const SizedBox(height: 16),

                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Text('계정이 없으신가요?'),
                                TextButton(
                                  onPressed: () {
                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) => const RegisterPrimaryScreen(),
                                      ),
                                    );
                                  },
                                  child: const Text(
                                    '회원가입',
                                    style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: Colors.blue,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _handleLogin() async {
    if (_formKey.currentState!.validate()) {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      
      final success = await authProvider.login(
        _emailController.text.trim(),
        _passwordController.text,
      );

      if (success && mounted) {
        Navigator.pushReplacementNamed(context, '/main');
      }
    }
  }
}