import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../models/user_model.dart';
import '../providers/auth_provider.dart';

class RegisterSecondaryScreen extends StatefulWidget {
  final String name;
  final String email;
  final String password;
  final String phone;
  final String gender;
  final String birthYear;

  const RegisterSecondaryScreen({
    Key? key,
    required this.name,
    required this.email,
    required this.password,
    required this.phone,
    required this.gender,
    required this.birthYear,
  }) : super(key: key);

  @override
  _RegisterSecondaryScreenState createState() => _RegisterSecondaryScreenState();
}

class _RegisterSecondaryScreenState extends State<RegisterSecondaryScreen> {
  final _formKey = GlobalKey<FormState>();
  
  final TextEditingController _baseDiseasesController = TextEditingController();
  final TextEditingController _medicationsController = TextEditingController();
  final TextEditingController _allergiesController = TextEditingController();
  final TextEditingController _surgeryHistoryController = TextEditingController();
  final TextEditingController _otherMedicalInfoController = TextEditingController();
  final TextEditingController _emergencyContactNameController = TextEditingController();
  final TextEditingController _emergencyContactPhoneController = TextEditingController();

  String? _selectedBloodType;
  String? _selectedEmergencyContactRelation;
  bool _isLoading = false;
  bool _hasMedicalHistory = false;
  bool _hasAllergies = false;
  bool _hasSurgeryHistory = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Medicall 회원가입 (2/2)'),
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
                    _buildBloodTypeDropdown(),
                    const SizedBox(height: 24),

                    Card(
                      elevation: 4,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              '의료 정보',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: Colors.black87,
                              ),
                            ),
                            const SizedBox(height: 16),
                            
                            Row(
                              children: [
                                const Text('기저질환이 있습니까?'),
                                const Spacer(),
                                Switch(
                                  value: _hasMedicalHistory,
                                  onChanged: (value) {
                                    setState(() {
                                      _hasMedicalHistory = value;
                                      if (!value) {
                                        _baseDiseasesController.clear();
                                      }
                                    });
                                  },
                                  activeColor: const Color(0xFF4A6FA5),
                                ),
                              ],
                            ),
                            if (_hasMedicalHistory) ...[
                              const SizedBox(height: 8),
                              _buildTextField(
                                controller: _baseDiseasesController,
                                label: '기저질환',
                                icon: Icons.medical_services,
                                maxLines: 2,
                              ),
                            ],
                            const SizedBox(height: 16),

                            Row(
                              children: [
                                const Text('알레르기가 있습니까?'),
                                const Spacer(),
                                Switch(
                                  value: _hasAllergies,
                                  onChanged: (value) {
                                    setState(() {
                                      _hasAllergies = value;
                                      if (!value) {
                                        _allergiesController.clear();
                                      }
                                    });
                                  },
                                  activeColor: const Color(0xFF4A6FA5),
                                ),
                              ],
                            ),
                            if (_hasAllergies) ...[
                              const SizedBox(height: 8),
                              _buildTextField(
                                controller: _allergiesController,
                                label: '알레르기',
                                icon: Icons.warning,
                                maxLines: 2,
                              ),
                            ],
                            const SizedBox(height: 16),

                            Row(
                              children: [
                                const Text('수술 이력이 있습니까?'),
                                const Spacer(),
                                Switch(
                                  value: _hasSurgeryHistory,
                                  onChanged: (value) {
                                    setState(() {
                                      _hasSurgeryHistory = value;
                                      if (!value) {
                                        _surgeryHistoryController.clear();
                                      }
                                    });
                                  },
                                  activeColor: const Color(0xFF4A6FA5),
                                ),
                              ],
                            ),
                            if (_hasSurgeryHistory) ...[
                              const SizedBox(height: 8),
                              _buildTextField(
                                controller: _surgeryHistoryController,
                                label: '수술 이력',
                                icon: Icons.medical_services,
                                maxLines: 2,
                              ),
                            ],
                            const SizedBox(height: 16),

                            _buildTextField(
                              controller: _medicationsController,
                              label: '복용약',
                              icon: Icons.medication,
                              maxLines: 2,
                            ),
                            const SizedBox(height: 16),

                            _buildTextField(
                              controller: _otherMedicalInfoController,
                              label: '기타 의료 정보',
                              icon: Icons.info,
                              maxLines: 3,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),

                    Card(
                      elevation: 4,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              '비상 연락처',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: Colors.black87,
                              ),
                            ),
                            const SizedBox(height: 16),
                            _buildEmergencyContactRelationDropdown(),
                            const SizedBox(height: 16),
                            _buildTextField(
                              controller: _emergencyContactNameController,
                              label: '이름',
                              icon: Icons.person,
                            ),
                            const SizedBox(height: 16),
                            _buildTextField(
                              controller: _emergencyContactPhoneController,
                              label: '전화번호',
                              icon: Icons.phone,
                              keyboardType: TextInputType.phone,
                              inputFormatters: [
                                FilteringTextInputFormatter.digitsOnly,
                                LengthLimitingTextInputFormatter(11),
                              ],
                              validator: (value) {
                                if (value != null && value.isNotEmpty) {
                                  if (value.length != 11) {
                                    return '올바른 전화번호 형식을 입력해주세요 (11자리)';
                                  }
                                  if (!value.startsWith('010')) {
                                    return '010으로 시작하는 전화번호를 입력해주세요';
                                  }
                                }
                                return null;
                              },
                            ),
                          ],
                        ),
                      ),
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
                            onPressed: (_isLoading || authProvider.isLoading) ? null : _handleComplete,
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
                                    '가입 완료',
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
    int maxLines = 1,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      maxLines: maxLines,
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

  Widget _buildBloodTypeDropdown() {
    return DropdownButtonFormField<String>(
      value: _selectedBloodType,
      decoration: InputDecoration(
        labelText: '혈액형',
        prefixIcon: const Icon(Icons.bloodtype),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        filled: true,
        fillColor: const Color(0xFFF8F9FA),
      ),
      items: ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
          .map((type) => DropdownMenuItem(
                value: type,
                child: Text(type),
              ))
          .toList(),
      onChanged: (value) {
        setState(() {
          _selectedBloodType = value;
        });
      },
      validator: (value) {
        if (value == null) {
          return '혈액형을 선택해주세요';
        }
        return null;
      },
    );
  }

  Widget _buildEmergencyContactRelationDropdown() {
    return DropdownButtonFormField<String>(
      value: _selectedEmergencyContactRelation,
      decoration: InputDecoration(
        labelText: '관계',
        prefixIcon: const Icon(Icons.people),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        filled: true,
        fillColor: const Color(0xFFF8F9FA),
      ),
      items: ['부모', '배우자', '자녀', '형제', '친구', '기타']
          .map((relation) => DropdownMenuItem(
                value: relation,
                child: Text(relation),
              ))
          .toList(),
      onChanged: (value) {
        setState(() {
          _selectedEmergencyContactRelation = value;
        });
      },
    );
  }

  void _handleComplete() async {
    if (_formKey.currentState!.validate()) {
      setState(() {
        _isLoading = true;
      });

      try {
        final authProvider = Provider.of<AuthProvider>(context, listen: false);
        
        final registerRequest = RegisterRequest(
          name: widget.name,
          email: widget.email,
          password: widget.password,
          phone: widget.phone,
          gender: widget.gender,
          birthYear: widget.birthYear,
          bloodType: _selectedBloodType!,
          baseDiseases: _hasMedicalHistory ? _baseDiseasesController.text : null,
          medications: _medicationsController.text.isNotEmpty ? _medicationsController.text : null,
          allergies: _hasAllergies ? _allergiesController.text : null,
          surgeryHistory: _hasSurgeryHistory ? _surgeryHistoryController.text : null,
          otherMedicalInfo: _otherMedicalInfoController.text.isNotEmpty ? _otherMedicalInfoController.text : null,
          emergencyContactName: _emergencyContactNameController.text.isNotEmpty ? _emergencyContactNameController.text : null,
          emergencyContactPhone: _emergencyContactPhoneController.text.isNotEmpty ? _emergencyContactPhoneController.text : null,
          emergencyContactRelation: _selectedEmergencyContactRelation,
        );

        final success = await authProvider.register(registerRequest);
        
        if (success && mounted) {
          _showSuccessDialog();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('회원가입 중 오류가 발생했습니다: ${e.toString()}'),
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

  void _showSuccessDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(15),
          ),
          title: Row(
            children: [
              Icon(
                Icons.check_circle,
                color: Colors.green,
                size: 30,
              ),
              const SizedBox(width: 10),
              const Text(
                '회원가입 완료',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          content: const Text(
            'Medicall에 오신 것을 환영합니다!\n회원가입이 성공적으로 완료되었습니다.',
            style: TextStyle(fontSize: 16),
          ),
          actions: [
            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pop();
                Navigator.of(context).pushNamedAndRemoveUntil(
                  '/main',
                  (Route<dynamic> route) => false,
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4A6FA5),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: const Text(
                '확인',
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
        );
      },
    );
  }

  @override
  void dispose() {
    _baseDiseasesController.dispose();
    _medicationsController.dispose();
    _allergiesController.dispose();
    _surgeryHistoryController.dispose();
    _otherMedicalInfoController.dispose();
    _emergencyContactNameController.dispose();
    _emergencyContactPhoneController.dispose();
    super.dispose();
  }
}