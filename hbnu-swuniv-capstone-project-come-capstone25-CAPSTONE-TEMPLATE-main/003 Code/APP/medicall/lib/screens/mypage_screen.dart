import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../main.dart';

class MyPageScreen extends StatefulWidget {
  const MyPageScreen({
    Key? key,
    required this.name,
    required this.email,
    required this.phone,
    required this.gender,
    required this.birthYear,
    required this.bloodType,
    this.baseDiseases = '',
    this.medications = '',
    this.allergies = '',
    this.surgeryHistory = '',
    this.otherMedicalInfo = '',
    required this.emergencyContactRelation,
    required this.emergencyContactName,
    required this.emergencyContactPhone,
  }) : super(key: key);

  final String name;
  final String email;
  final String phone;
  final String gender;
  final String birthYear;
  final String bloodType;
  final String baseDiseases;
  final String medications;
  final String allergies;
  final String surgeryHistory;
  final String otherMedicalInfo;
  final String emergencyContactRelation;
  final String emergencyContactName;
  final String emergencyContactPhone;

  @override
  _MyPageScreenState createState() => _MyPageScreenState();
}

class _MyPageScreenState extends State<MyPageScreen> {
  late TextEditingController _nameController;
  late TextEditingController _emailController;
  late TextEditingController _phoneController;
  late TextEditingController _birthYearController;
  late TextEditingController _baseDiseasesController;
  late TextEditingController _medicationsController;
  late TextEditingController _allergiesController;
  late TextEditingController _surgeryHistoryController;
  late TextEditingController _otherMedicalInfoController;
  late TextEditingController _emergencyContactNameController;
  late TextEditingController _emergencyContactPhoneController;

  late String _selectedGender;
  late String _selectedBloodType;
  String? _selectedEmergencyContactRelation;
  bool _isEditing = false;
  bool _hasChanges = false;

  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _initializeControllers();
  }

  void _initializeControllers() {
    _nameController = TextEditingController(text: widget.name);
    _emailController = TextEditingController(text: widget.email);
    _phoneController = TextEditingController(text: widget.phone);
    _birthYearController = TextEditingController(text: widget.birthYear);
    _baseDiseasesController = TextEditingController(text: widget.baseDiseases);
    _medicationsController = TextEditingController(text: widget.medications);
    _allergiesController = TextEditingController(text: widget.allergies);
    _surgeryHistoryController = TextEditingController(text: widget.surgeryHistory);
    _otherMedicalInfoController = TextEditingController(text: widget.otherMedicalInfo);
    _emergencyContactNameController = TextEditingController(text: widget.emergencyContactName);
    _emergencyContactPhoneController = TextEditingController(text: widget.emergencyContactPhone);

    _selectedGender = widget.gender;
    
    final validBloodTypes = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-', '미등록'];
    _selectedBloodType = validBloodTypes.contains(widget.bloodType) ? widget.bloodType : '미등록';
    
    final validRelations = ['부모', '배우자', '자녀', '형제', '친구', '기타'];
    _selectedEmergencyContactRelation = validRelations.contains(widget.emergencyContactRelation) 
        ? widget.emergencyContactRelation 
        : (widget.emergencyContactRelation.isNotEmpty ? '기타' : null);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('마이페이지'),
        backgroundColor: Colors.blue[700],
        actions: [
          IconButton(
            icon: Icon(_isEditing ? Icons.close : Icons.edit),
            onPressed: _toggleEditing,
            tooltip: _isEditing ? '편집 취소' : '정보 수정',
          ),
          if (_isEditing)
            IconButton(
              icon: const Icon(Icons.save),
              onPressed: _hasChanges ? _saveChanges : null,
              tooltip: '변경사항 저장',
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: ListView(
            children: [
              _buildProfileCard(),
              const SizedBox(height: 24),
              
              _buildInfoCard(
                title: '개인 정보',
                children: [
                  _buildTextField(_nameController, '이름', enabled: _isEditing),
                  _buildTextField(_emailController, '이메일', enabled: _isEditing),
                  _buildTextField(_phoneController, '전화번호', enabled: _isEditing),
                  _buildGenderDropdown(),
                  _buildTextField(_birthYearController, '출생연도', enabled: _isEditing),
                ],
              ),
              const SizedBox(height: 24),

              _buildInfoCard(
                title: '의료 정보',
                children: [
                  _buildBloodTypeDropdown(),
                  _buildTextField(_baseDiseasesController, '기저질환', enabled: _isEditing),
                  _buildTextField(_medicationsController, '복용약', enabled: _isEditing),
                  _buildTextField(_allergiesController, '알레르기', enabled: _isEditing),
                  _buildTextField(_surgeryHistoryController, '수술 이력', enabled: _isEditing),
                  _buildTextField(_otherMedicalInfoController, '기타 의료 정보', enabled: _isEditing),
                ],
              ),
              const SizedBox(height: 24),

              _buildInfoCard(
                title: '비상 연락처',
                children: [
                  _buildEmergencyContactRelationDropdown(),
                  _buildTextField(_emergencyContactNameController, '이름', enabled: _isEditing),
                  _buildTextField(_emergencyContactPhoneController, '전화번호', enabled: _isEditing),
                ],
              ),
              const SizedBox(height: 32),

              Card(
                elevation: 4,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton.icon(
                          onPressed: _handleLogout,
                          icon: const Icon(Icons.logout, color: Colors.white),
                          label: const Text(
                            '로그아웃',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red[600],
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                            elevation: 4,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProfileCard() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            CircleAvatar(
              radius: 50,
              backgroundColor: Colors.blue[100],
              child: Text(
                widget.name[0],
                style: TextStyle(
                  fontSize: 40,
                  fontWeight: FontWeight.bold,
                  color: Colors.blue[700],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              widget.name,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              widget.email,
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard({
    required String title,
    required List<Widget> children,
  }) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Colors.black87,
              ),
            ),
            const SizedBox(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _buildTextField(
    TextEditingController controller,
    String label, {
    bool enabled = true,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: TextFormField(
        controller: controller,
        enabled: enabled,
        decoration: InputDecoration(
          labelText: label,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          filled: true,
          fillColor: enabled ? Colors.grey[50] : Colors.grey[100],
        ),
        onChanged: (_) => _checkChanges(),
      ),
    );
  }

  Widget _buildGenderDropdown() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: DropdownButtonFormField<String>(
        value: _selectedGender,
        decoration: InputDecoration(
          labelText: '성별',
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          filled: true,
          fillColor: _isEditing ? Colors.grey[50] : Colors.grey[100],
        ),
        items: ['남성', '여성']
            .map((gender) => DropdownMenuItem(
                  value: gender,
                  child: Text(gender),
                ))
            .toList(),
        onChanged: _isEditing
            ? (value) {
                setState(() {
                  _selectedGender = value!;
                  _checkChanges();
                });
              }
            : null,
      ),
    );
  }

  Widget _buildBloodTypeDropdown() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: DropdownButtonFormField<String>(
        value: _selectedBloodType,
        decoration: InputDecoration(
          labelText: '혈액형',
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          filled: true,
          fillColor: _isEditing ? Colors.grey[50] : Colors.grey[100],
        ),
        items: ['미등록', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
            .map((type) => DropdownMenuItem(
                  value: type,
                  child: Text(type),
                ))
            .toList(),
        onChanged: _isEditing
            ? (value) {
                setState(() {
                  _selectedBloodType = value!;
                  _checkChanges();
                });
              }
            : null,
      ),
    );
  }

  Widget _buildEmergencyContactRelationDropdown() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: DropdownButtonFormField<String>(
        value: _selectedEmergencyContactRelation,
        decoration: InputDecoration(
          labelText: '관계',
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          filled: true,
          fillColor: _isEditing ? Colors.grey[50] : Colors.grey[100],
        ),
        hint: const Text('관계를 선택해주세요'),
        items: ['부모', '배우자', '자녀', '형제', '친구', '기타']
            .map((relation) => DropdownMenuItem(
                  value: relation,
                  child: Text(relation),
                ))
            .toList(),
        onChanged: _isEditing
            ? (value) {
                setState(() {
                  _selectedEmergencyContactRelation = value;
                  _checkChanges();
                });
              }
            : null,
      ),
    );
  }

  void _toggleEditing() {
    setState(() {
      if (_isEditing) {
        _initializeControllers();
        _hasChanges = false;
      }
      _isEditing = !_isEditing;
    });
  }

  void _checkChanges() {
    bool hasChanges = _nameController.text != widget.name ||
        _emailController.text != widget.email ||
        _phoneController.text != widget.phone ||
        _selectedGender != widget.gender ||
        _birthYearController.text != widget.birthYear ||
        _selectedBloodType != widget.bloodType ||
        _baseDiseasesController.text != widget.baseDiseases ||
        _medicationsController.text != widget.medications ||
        _allergiesController.text != widget.allergies ||
        _surgeryHistoryController.text != widget.surgeryHistory ||
        _otherMedicalInfoController.text != widget.otherMedicalInfo ||
        (_selectedEmergencyContactRelation ?? '') != widget.emergencyContactRelation ||
        _emergencyContactNameController.text != widget.emergencyContactName ||
        _emergencyContactPhoneController.text != widget.emergencyContactPhone;

    setState(() {
      _hasChanges = hasChanges;
    });
  }

  void _saveChanges() async {
    if (_formKey.currentState!.validate()) {
      try {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (BuildContext context) {
            return const AlertDialog(
              content: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(width: 16),
                  Text('정보를 업데이트하는 중...'),
                ],
              ),
            );
          },
        );

        final authProvider = Provider.of<AuthProvider>(context, listen: false);
        final currentUser = authProvider.currentUser;
        
        if (currentUser == null) {
          Navigator.of(context).pop();
          throw Exception('사용자 정보를 찾을 수 없습니다.');
        }

        Map<String, dynamic> updateData = {
          'name': _nameController.text.trim(),
          'phone': _phoneController.text.trim(),
          'gender': _selectedGender,
          'birth_year': int.parse(_birthYearController.text.trim()),
          'blood_type': _selectedBloodType,
          'base_diseases': _baseDiseasesController.text.trim(),
          'medications': _medicationsController.text.trim(),
          'allergies': _allergiesController.text.trim(),
          'surgery_history': _surgeryHistoryController.text.trim(),
          'other_medical_info': _otherMedicalInfoController.text.trim(),
          'emergency_contact_name': _emergencyContactNameController.text.trim(),
          'emergency_contact_phone': _emergencyContactPhoneController.text.trim(),
          'emergency_contact_relation': _selectedEmergencyContactRelation ?? '',
        };

        final success = await authProvider.updateUser(updateData);
        
        if (mounted) {
          Navigator.of(context).pop();
        }

        if (success) {
          setState(() {
            _isEditing = false;
            _hasChanges = false;
          });

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: const Text('정보가 성공적으로 수정되었습니다'),
                backgroundColor: Colors.green,
                behavior: SnackBarBehavior.floating,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            );
          }
        } else {
          throw Exception(authProvider.errorMessage ?? '업데이트에 실패했습니다.');
        }
      } catch (e) {
        if (mounted && Navigator.canPop(context)) {
          Navigator.of(context).pop();
        }

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('정보 업데이트 실패: ${e.toString()}'),
              backgroundColor: Colors.red,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              duration: const Duration(seconds: 4),
            ),
          );
        }
      }
    }
  }

  void _handleLogout() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(15),
          ),
          title: const Text(
            '로그아웃',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          content: const Text('정말 로그아웃하시겠습니까?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('취소'),
            ),
            ElevatedButton(
              onPressed: () async {
                Navigator.of(context).pop();
                
                final authProvider = Provider.of<AuthProvider>(context, listen: false);
                await authProvider.logout();
                
                if (mounted) {
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (context) => const AppRouter()),
                    (Route<dynamic> route) => false,
                  );
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red[600],
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: const Text(
                '로그아웃',
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
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _birthYearController.dispose();
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