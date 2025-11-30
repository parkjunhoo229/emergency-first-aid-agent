import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';

class HospitalDetailScreen extends StatelessWidget {
  final String name;
  final String phone;
  final String address;
  final String distance;
  final double? lat;
  final double? lng;

  const HospitalDetailScreen({
    Key? key,
    required this.name,
    required this.phone,
    required this.address,
    required this.distance,
    this.lat,
    this.lng,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final hasValidCoords = lat != null &&
        lng != null &&
        lat! >= -90 &&
        lat! <= 90 &&
        lng! >= -180 &&
        lng! <= 180;

    final defaultPosition = const NLatLng(37.5666, 126.979);
    final hospitalPosition = hasValidCoords ? NLatLng(lat!, lng!) : defaultPosition;

    return Scaffold(
      appBar: AppBar(
        title: const Text('병원 상세 정보'),
      ),
      body: Column(
        children: [
          Container(
            height: MediaQuery.of(context).size.height * 0.4,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Stack(
                children: [
                  NaverMap(
                    options: NaverMapViewOptions(
                      initialCameraPosition: NCameraPosition(
                        target: hospitalPosition,
                        zoom: hasValidCoords ? 15 : 10,
                        bearing: 0,
                        tilt: 0,
                      ),
                      mapType: NMapType.basic,
                      activeLayerGroups: [NLayerGroup.building, NLayerGroup.transit],
                    ),
                    onMapReady: (controller) {
                      if (hasValidCoords) {
                        final marker = NMarker(
                          id: 'hospital_location',
                          position: hospitalPosition,
                        );
                        controller.addOverlay(marker);
                      }
                    },
                  ),
                  if (!hasValidCoords)
                    Positioned.fill(
                      child: Container(
                        color: Colors.black.withOpacity(0.15),
                        alignment: Alignment.center,
                        child: const Text(
                          '병원 좌표 정보를 불러올 수 없습니다.',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF4A6FA5),
                    ),
                  ),
                  const SizedBox(height: 12),
                  _buildInfoSection(
                    icon: Icons.phone,
                    title: '연락처',
                    content: phone,
                  ),
                  const SizedBox(height: 16),
                  _buildInfoSection(
                    icon: Icons.location_on,
                    title: '주소',
                    content: address,
                  ),
                  const SizedBox(height: 16),
                  _buildInfoSection(
                    icon: Icons.directions_walk,
                    title: '현재 위치로부터의 거리',
                    content: distance,
                  ),
                  const SizedBox(height: 32),
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton.icon(
                      onPressed: () async {
                        final hospitalInfo = '$name\n$address\n$phone';
                        
                        try {
                          await Clipboard.setData(ClipboardData(text: hospitalInfo));
                          
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('병원 정보가 클립보드에 복사되었습니다.'),
                                backgroundColor: Colors.green,
                                duration: Duration(seconds: 2),
                              ),
                            );
                          }
                        } catch (e) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('복사 중 오류가 발생했습니다: $e'),
                                backgroundColor: Colors.red,
                                duration: const Duration(seconds: 3),
                              ),
                            );
                          }
                        }
                      },
                      icon: const Icon(Icons.share, color: Colors.white),
                      label: const Text(
                        '공유하기',
                        style: TextStyle(
                          fontSize: 16,
                          color: Colors.white,
                        ),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4A6FA5),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoSection({
    required IconData icon,
    required String title,
    required String content,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 20, color: const Color(0xFF4A6FA5)),
            const SizedBox(width: 8),
            Text(
              title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Color(0xFF4A6FA5),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.only(left: 28),
          child: Text(
            content,
            style: const TextStyle(
              fontSize: 16,
              color: Colors.black87,
            ),
          ),
        ),
      ],
    );
  }
} 