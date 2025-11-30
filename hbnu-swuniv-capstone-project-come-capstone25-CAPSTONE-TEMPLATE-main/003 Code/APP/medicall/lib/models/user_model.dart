class User {
  final int id;
  final String name;
  final String email;
  final String phone;
  final String gender;
  final int birthYear;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;
  final MedicalInfo? medicalInfo;

  User({
    required this.id,
    required this.name,
    required this.email,
    required this.phone,
    required this.gender,
    required this.birthYear,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
    this.medicalInfo,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      name: json['name'],
      email: json['email'],
      phone: json['phone'],
      gender: json['gender'],
      birthYear: json['birth_year'],
      isActive: json['is_active'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      medicalInfo: json['medical_info'] != null 
          ? MedicalInfo.fromJson(json['medical_info'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'phone': phone,
      'gender': gender,
      'birth_year': birthYear,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'medical_info': medicalInfo?.toJson(),
    };
  }
}

class MedicalInfo {
  final int id;
  final String bloodType;
  final String baseDiseases;
  final String medications;
  final String allergies;
  final String surgeryHistory;
  final String otherMedicalInfo;
  final String emergencyContactName;
  final String emergencyContactPhone;
  final String emergencyContactRelation;
  final DateTime createdAt;
  final DateTime updatedAt;

  MedicalInfo({
    required this.id,
    required this.bloodType,
    required this.baseDiseases,
    required this.medications,
    required this.allergies,
    required this.surgeryHistory,
    required this.otherMedicalInfo,
    required this.emergencyContactName,
    required this.emergencyContactPhone,
    required this.emergencyContactRelation,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MedicalInfo.fromJson(Map<String, dynamic> json) {
    return MedicalInfo(
      id: json['id'],
      bloodType: json['blood_type'],
      baseDiseases: json['base_diseases'] ?? '',
      medications: json['medications'] ?? '',
      allergies: json['allergies'] ?? '',
      surgeryHistory: json['surgery_history'] ?? '',
      otherMedicalInfo: json['other_medical_info'] ?? '',
      emergencyContactName: json['emergency_contact_name'] ?? '',
      emergencyContactPhone: json['emergency_contact_phone'] ?? '',
      emergencyContactRelation: json['emergency_contact_relation'] ?? '',
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'blood_type': bloodType,
      'base_diseases': baseDiseases,
      'medications': medications,
      'allergies': allergies,
      'surgery_history': surgeryHistory,
      'other_medical_info': otherMedicalInfo,
      'emergency_contact_name': emergencyContactName,
      'emergency_contact_phone': emergencyContactPhone,
      'emergency_contact_relation': emergencyContactRelation,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}

class RegisterRequest {
  final String name;
  final String email;
  final String password;
  final String phone;
  final String gender;
  final String birthYear;
  final String bloodType;
  final String? baseDiseases;
  final String? medications;
  final String? allergies;
  final String? surgeryHistory;
  final String? otherMedicalInfo;
  final String? emergencyContactName;
  final String? emergencyContactPhone;
  final String? emergencyContactRelation;

  RegisterRequest({
    required this.name,
    required this.email,
    required this.password,
    required this.phone,
    required this.gender,
    required this.birthYear,
    required this.bloodType,
    this.baseDiseases,
    this.medications,
    this.allergies,
    this.surgeryHistory,
    this.otherMedicalInfo,
    this.emergencyContactName,
    this.emergencyContactPhone,
    this.emergencyContactRelation,
  });

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'email': email,
      'password': password,
      'phone': phone,
      'gender': gender,
      'birth_year': birthYear,
      'blood_type': bloodType,
      'base_diseases': baseDiseases ?? '',
      'medications': medications ?? '',
      'allergies': allergies ?? '',
      'surgery_history': surgeryHistory ?? '',
      'other_medical_info': otherMedicalInfo ?? '',
      'emergency_contact_name': emergencyContactName ?? '',
      'emergency_contact_phone': emergencyContactPhone ?? '',
      'emergency_contact_relation': emergencyContactRelation ?? '',
    };
  }
}

class LoginRequest {
  final String email;
  final String password;

  LoginRequest({
    required this.email,
    required this.password,
  });

  Map<String, dynamic> toJson() {
    return {
      'email': email,
      'password': password,
    };
  }
}

class ApiResponse<T> {
  final bool success;
  final String message;
  final T? data;
  final DateTime timestamp;

  ApiResponse({
    required this.success,
    required this.message,
    this.data,
    required this.timestamp,
  });

  factory ApiResponse.fromJson(Map<String, dynamic> json, T? Function(dynamic)? fromJsonT) {
    return ApiResponse<T>(
      success: json['success'],
      message: json['message'],
      data: json['data'] != null && fromJsonT != null ? fromJsonT(json['data']) : json['data'],
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
} 