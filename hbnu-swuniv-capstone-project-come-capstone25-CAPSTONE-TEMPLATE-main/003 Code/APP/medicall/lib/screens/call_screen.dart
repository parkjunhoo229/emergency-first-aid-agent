import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:medicall/screens/calling_screen.dart';
import 'package:medicall/screens/mypage_screen.dart';
import 'package:medicall/screens/hospital_list_screen.dart';
import '../providers/auth_provider.dart';

class CallScreen extends StatelessWidget {
  final String name;
  final String gender;
  final String birthYear;
  final String bloodType;
  final String baseDiseases;
  final String medications;
  final String allergies;

  const CallScreen({
    Key? key,
    required this.name,
    required this.gender,
    required this.birthYear,
    required this.bloodType,
    this.baseDiseases = '',
    this.medications = '',
    this.allergies = '',
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('응급 통화'),
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            onPressed: () {
              final authProvider = Provider.of<AuthProvider>(context, listen: false);
              final user = authProvider.currentUser;
              
              if (user != null) {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => MyPageScreen(
                      name: user.name,
                      email: user.email,
                      phone: user.phone,
                      gender: user.gender,
                      birthYear: user.birthYear.toString(),
                      bloodType: user.medicalInfo?.bloodType ?? '미등록',
                      baseDiseases: user.medicalInfo?.baseDiseases ?? '',
                      medications: user.medicalInfo?.medications ?? '',
                      allergies: user.medicalInfo?.allergies ?? '',
                      surgeryHistory: user.medicalInfo?.surgeryHistory ?? '',
                      otherMedicalInfo: user.medicalInfo?.otherMedicalInfo ?? '',
                      emergencyContactRelation: user.medicalInfo?.emergencyContactRelation ?? '',
                      emergencyContactName: user.medicalInfo?.emergencyContactName ?? '',
                      emergencyContactPhone: user.medicalInfo?.emergencyContactPhone ?? '',
                    ),
                  ),
                );
              }
            },
            tooltip: '내 정보 수정',
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Card(
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
                      '내 의료 정보',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _buildInfoRow('이름', name),
                    _buildInfoRow('성별', gender),
                    _buildInfoRow('출생연도', birthYear),
                    _buildInfoRow('혈액형', bloodType),
                    if (baseDiseases.isNotEmpty) _buildInfoRow('기저질환', baseDiseases),
                    if (medications.isNotEmpty) _buildInfoRow('복용약', medications),
                    if (allergies.isNotEmpty) _buildInfoRow('알레르기', allergies),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton.icon(
                          icon: const Icon(Icons.edit),
                          label: const Text('정보 수정'),
                          onPressed: () {
                            final authProvider = Provider.of<AuthProvider>(context, listen: false);
                            final user = authProvider.currentUser;
                            
                            if (user != null) {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => MyPageScreen(
                                    name: user.name,
                                    email: user.email,
                                    phone: user.phone,
                                    gender: user.gender,
                                    birthYear: user.birthYear.toString(),
                                    bloodType: user.medicalInfo?.bloodType ?? '미등록',
                                    baseDiseases: user.medicalInfo?.baseDiseases ?? '',
                                    medications: user.medicalInfo?.medications ?? '',
                                    allergies: user.medicalInfo?.allergies ?? '',
                                    surgeryHistory: user.medicalInfo?.surgeryHistory ?? '',
                                    otherMedicalInfo: user.medicalInfo?.otherMedicalInfo ?? '',
                                    emergencyContactRelation: user.medicalInfo?.emergencyContactRelation ?? '',
                                    emergencyContactName: user.medicalInfo?.emergencyContactName ?? '',
                                    emergencyContactPhone: user.medicalInfo?.emergencyContactPhone ?? '',
                                  ),
                                ),
                              );
                            }
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),

          const Spacer(),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 24.0),
            child: Column(
              children: [
                const Text(
                  '응급 상황 시 통화 버튼을 눌러주세요',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: () {
                    _startEmergencyCall(context);
                  },
                  child: Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(
                      color: Colors.red,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.red.withOpacity(0.3),
                          spreadRadius: 10,
                          blurRadius: 20,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.call,
                      color: Colors.white,
                      size: 60,
                    ),
                  ),
                ),
              ],
            ),
          ),

          const Spacer(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        selectedItemColor: Colors.blue,
        currentIndex: 0,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.call),
            label: '응급 통화 걸기',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.local_hospital),
            label: '주변 병원 찾기',
          ),
        ],
        onTap: (index) {
          if (index == 1) {
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                builder: (context) => const HospitalListScreen(),
              ),
            );
          }
        },
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.black54,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _startEmergencyCall(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('응급 통화 연결 중'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: const [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('AI 응급 상담사와 연결 중입니다. 잠시만 기다려주세요...'),
          ],
        ),
      ),
    );

    Future.delayed(const Duration(seconds: 2), () {
      Navigator.pop(context);
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => const CallingScreen(),
        ),
      );
    });
  }
}

AppBar buildAppBar(String title) {
  return AppBar(
    title: Text(title),
    backgroundColor: Colors.blue[700],
    elevation: 0,
  );
}

Widget buildFormField({
  required String label,
  required TextEditingController controller,
  String? hint,
  bool obscureText = false,
  TextInputType? keyboardType,
  String? Function(String?)? validator,
}) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 16.0),
    child: TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        filled: true,
        fillColor: Colors.grey[50],
      ),
      validator: validator,
    ),
  );
}

Widget buildSubmitButton(String text, VoidCallback onPressed) {
  return ElevatedButton(
    onPressed: onPressed,
    style: ElevatedButton.styleFrom(
      backgroundColor: Colors.blue[700],
      padding: const EdgeInsets.symmetric(vertical: 16),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
      ),
    ),
    child: Text(
      text,
      style: const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.bold,
      ),
    ),
  );
}