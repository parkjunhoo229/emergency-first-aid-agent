import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import 'call_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({Key? key}) : super(key: key);

  @override
  _MainScreenState createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, authProvider, child) {
        if (!authProvider.isInitialized) {
          return const Scaffold(
            body: Center(
              child: CircularProgressIndicator(),
            ),
          );
        }

        final user = authProvider.currentUser;
        
        if (user == null) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        return CallScreen(
          name: user.name,
          gender: user.gender,
          birthYear: user.birthYear.toString(),
          bloodType: user.medicalInfo?.bloodType ?? '미등록',
          baseDiseases: user.medicalInfo?.baseDiseases ?? '',
          medications: user.medicalInfo?.medications ?? '',
          allergies: user.medicalInfo?.allergies ?? '',
        );
      },
    );
  }
} 