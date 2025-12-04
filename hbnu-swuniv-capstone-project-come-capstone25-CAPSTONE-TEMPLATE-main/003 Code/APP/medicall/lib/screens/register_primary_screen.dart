import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:medicall/screens/register_secondary_screen.dart';
import '../providers/auth_provider.dart';

class RegisterPrimaryScreen extends StatefulWidget {
  const RegisterPrimaryScreen({Key? key}) : super(key: key);

  @override
  _RegisterPrimaryScreenState createState() => _RegisterPrimaryScreenState();
}

class _RegisterPrimaryScreenState extends State<RegisterPrimaryScreen> {
  final _formKey = GlobalKey<FormState>();
  
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _birthYearController = TextEditingController();

  String? _selectedGender;
  bool _isLoading = false;
  bool _isEmailChecked = false;
  bool _isEmailAvailable = false;
  String? _emailCheckMessage;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Medicall 회원가입 (1/2)'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _buildTextField(
                    controller: _nameController,
                    label: '이름',
                    icon: Icons.person,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return '이름을 입력해주세요';
                      }
                      if (value.length < 2) {
                        return '이름은 최소 2자 이상이어야 합니다';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),

                  _buildEmailField(),
                  const SizedBox(height: 16),

                  _buildTextField(
                    controller: _passwordController,
                    label: '비밀번호',
                    icon: Icons.lock,
                    obscureText: true,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return '비밀번호를 입력해주세요';
                      }
                      if (value.length < 8) {
                        return '비밀번호는 최소 8자 이상이어야 합니다';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),

                  _buildTextField(
                    controller: _confirmPasswordController,
                    label: '비밀번호 확인',
                    icon: Icons.lock_outline,
                    obscureText: true,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return '비밀번호를 다시 입력해주세요';
                      }
                      if (value != _passwordController.text) {
                        return '비밀번호가 일치하지 않습니다';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),

                  _buildTextField(
                    controller: _phoneController,
                    label: '전화번호',
                    icon: Icons.phone,
                    keyboardType: TextInputType.phone,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(11),
                    ],
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return '전화번호를 입력해주세요';
                      }
                      if (value.length != 11) {
                        return '올바른 전화번호 형식을 입력해주세요 (11자리)';
                      }
                      if (!value.startsWith('010')) {
                        return '010으로 시작하는 전화번호를 입력해주세요';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),

                  _buildGenderDropdown(),
                  const SizedBox(height: 16),

                  _buildTextField(
                    controller: _birthYearController,
                    label: '출생연도',
                    icon: Icons.calendar_today,
                    keyboardType: TextInputType.number,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(4),
                    ],
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return '출생연도를 입력해주세요';
                      }
                      int? year = int.tryParse(value);
                      if (year == null || year < 1900 || year > DateTime.now().year) {
                        return '올바른 출생연도를 입력해주세요';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 32),

                  Consumer<AuthProvider>(
                    builder: (context, authProvider, child) {
                      if (authProvider.errorMessage != null) {
                        WidgetsBinding.instance.addPostFrameCallback((_) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(authProvider.errorMessage!),
                              backgroundColor: Colors.red,
                              behavior: SnackBarBehavior.floating,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                          );
                          authProvider.clearError();
                        });
                      }

                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        height: 50,
                        child: ElevatedButton(
                          onPressed: (_isLoading || authProvider.isLoading) ? null : _handleNextStep,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF4A6FA5),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                            elevation: 4,
                          ),
                          child: (_isLoading || authProvider.isLoading)
                              ? const CircularProgressIndicator(color: Colors.white)
                              : const Text(
                                  '다음 단계',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    bool obscureText = false,
    TextInputType? keyboardType,
    List<TextInputFormatter>? inputFormatters,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        filled: true,
        fillColor: const Color(0xFFF8F9FA),
      ),
      validator: validator,
    );
  }

  Widget _buildEmailField() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(
                  labelText: '이메일',
                  prefixIcon: const Icon(Icons.email),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                  filled: true,
                  fillColor: const Color(0xFFF8F9FA),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return '이메일을 입력해주세요';
                  }
                  final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
                  if (!emailRegex.hasMatch(value)) {
                    return '올바른 이메일 형식을 입력해주세요';
                  }
                  if (!_isEmailChecked || !_isEmailAvailable) {
                    return '이메일 중복 확인을 해주세요';
                  }
                  return null;
                },
                onChanged: (value) {
                  setState(() {
                    _isEmailChecked = false;
                    _isEmailAvailable = false;
                    _emailCheckMessage = null;
                  });
                },
              ),
            ),
            const SizedBox(width: 8),
            Consumer<AuthProvider>(
              builder: (context, authProvider, child) {
                return ElevatedButton(
                  onPressed: authProvider.isLoading ? null : _checkEmail,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF4A6FA5),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: authProvider.isLoading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Text(
                          '중복확인',
                          style: TextStyle(color: Colors.white),
                        ),
                );
              },
            ),
          ],
        ),
        if (_emailCheckMessage != null) ...[
          const SizedBox(height: 4),
          Text(
            _emailCheckMessage!,
            style: TextStyle(
              fontSize: 12,
              color: _isEmailAvailable ? Colors.green : Colors.red,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildGenderDropdown() {
    return DropdownButtonFormField<String>(
      value: _selectedGender,
      decoration: InputDecoration(
        labelText: '성별',
        prefixIcon: const Icon(Icons.wc),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        filled: true,
        fillColor: const Color(0xFFF8F9FA),
      ),
      items: ['남성', '여성']
          .map((gender) => DropdownMenuItem(
                value: gender,
                child: Text(gender),
              ))
          .toList(),
      onChanged: (value) {
        setState(() {
          _selectedGender = value;
        });
      },
      validator: (value) {
        if (value == null) {
          return '성별을 선택해주세요';
        }
        return null;
      },
    );
  }

  Future<void> _checkEmail() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      setState(() {
        _emailCheckMessage = '이메일을 입력해주세요';
        _isEmailChecked = false;
        _isEmailAvailable = false;
      });
      return;
    }

    final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    if (!emailRegex.hasMatch(email)) {
      setState(() {
        _emailCheckMessage = '올바른 이메일 형식을 입력해주세요';
        _isEmailChecked = false;
        _isEmailAvailable = false;
      });
      return;
    }

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final isAvailable = await authProvider.checkEmailAvailability(email);
    
    setState(() {
      _isEmailChecked = true;
      _isEmailAvailable = isAvailable;
      _emailCheckMessage = isAvailable 
          ? '사용 가능한 이메일입니다' 
          : '이미 사용 중인 이메일입니다';
    });
  }

  void _handleNextStep() async {
    if (_formKey.currentState!.validate()) {
      setState(() {
        _isLoading = true;
      });

      try {
        if (mounted) {
          final password = _passwordController.text;
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => RegisterSecondaryScreen(
                name: _nameController.text,
                email: _emailController.text,
                password: password,
                phone: _phoneController.text,
                gender: _selectedGender!,
                birthYear: _birthYearController.text,
              ),
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('오류가 발생했습니다: ${e.toString()}'),
              backgroundColor: Colors.red,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          );
        }
      } finally {
        if (mounted) {
          setState(() {
            _isLoading = false;
          });
        }
      }
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _phoneController.dispose();
    _birthYearController.dispose();
    super.dispose();
  }
}