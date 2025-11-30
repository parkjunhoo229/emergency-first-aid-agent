class Hospital {
  final int id;
  final String name;
  final String? phone;
  final String? address;
  final String? region;
  final double? lat;
  final double? lng;
  final DateTime? createdAt;

  Hospital({
    required this.id,
    required this.name,
    this.phone,
    this.address,
    this.region,
    this.lat,
    this.lng,
    this.createdAt,
  });

  factory Hospital.fromJson(Map<String, dynamic> json) {
    return Hospital(
      id: json['id'] as int,
      name: json['name'] as String,
      phone: json['phone'] as String?,
      address: json['address'] as String?,
      region: json['region'] as String?,
      lat: _parseDouble(json['lat']),
      lng: _parseDouble(json['lng']),
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at'])
          : null,
    );
  }

  static double? _parseDouble(dynamic value) {
    if (value == null) return null;
    
    try {
      if (value is double) {
        return value.isFinite ? value : null;
      } else if (value is int) {
        return value.toDouble();
      } else if (value is String) {
        final parsed = double.tryParse(value);
        return (parsed != null && parsed.isFinite) ? parsed : null;
      }
    } catch (e) {
      print('[Hospital.fromJson] 좌표 파싱 오류: $value - $e');
    }
    
    return null;
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'phone': phone,
      'address': address,
      'region': region,
      'lat': lat,
      'lng': lng,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  @override
  String toString() {
    return 'Hospital{id: $id, name: $name, address: $address}';
  }
} 