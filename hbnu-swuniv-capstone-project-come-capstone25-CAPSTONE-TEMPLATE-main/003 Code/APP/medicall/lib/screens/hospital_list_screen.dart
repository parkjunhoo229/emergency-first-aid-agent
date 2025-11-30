import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:medicall/screens/hospital_detail_screen.dart';
import 'package:medicall/screens/call_screen.dart';
import 'package:medicall/screens/mypage_screen.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import '../providers/auth_provider.dart';
import '../services/geolocator_helper.dart';
import '../services/hospital_service.dart';
import '../models/hospital.dart';
import '../utils/distance_helper.dart';
import 'package:geolocator/geolocator.dart';

class HospitalListScreen extends StatefulWidget {
  const HospitalListScreen({Key? key}) : super(key: key);

  @override
  State<HospitalListScreen> createState() => _HospitalListScreenState();
}

class _HospitalListScreenState extends State<HospitalListScreen> {
  late NLocationOverlay locationOverlay;
  Position? position;
  NaverMapController? mapController;
  bool isLoadingLocation = true;
  bool isLoadingHospitals = false;
  List<Hospital> hospitals = [];
  String? errorMessage;

  final Set<NMarker> hospitalMarkers = {};
  final Set<NInfoWindow> infoWindows = {};

  bool get isLoading => isLoadingLocation || isLoadingHospitals;

  @override
  void initState() {
    super.initState();
    getCurrentLocation();
  }

  getCurrentLocation() async {
    try {
      setState(() {
        isLoadingLocation = true;
        errorMessage = null;
      });
      
      position = await GeolocatorHelper.getCurrentLocation();
      
      setState(() {
        isLoadingLocation = false;
      });
      
      if (mapController != null && position != null) {
        updateLocationOnMap();
      }
      
      if (position != null) {
        await loadNearbyHospitals();
      }
    } catch (e) {
      setState(() {
        isLoadingLocation = false;
        errorMessage = '위치를 가져올 수 없습니다. 기본 위치를 사용합니다.';
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage!),
            backgroundColor: Colors.orange,
          ),
        );
      }
    }
  }

  Future<void> loadNearbyHospitals() async {
    if (position == null) {
      return;
    }
    
    try {
      setState(() {
        isLoadingHospitals = true;
        errorMessage = null;
      });
      
      List<Hospital> fetchedHospitals = await HospitalService.getNearbyHospitals(
        position!.latitude,
        position!.longitude,
      );
      
      int validCoordinates = 0;
      for (final hospital in fetchedHospitals) {
        if (hospital.lat != null && hospital.lng != null && 
            !hospital.lat!.isNaN && !hospital.lng!.isNaN) {
          validCoordinates++;
        }
      }
      
      fetchedHospitals.sort((a, b) {
        double distanceA = DistanceHelper.getDistanceInMeters(
          position!.latitude,
          position!.longitude,
          a.lat,
          a.lng,
        );
        double distanceB = DistanceHelper.getDistanceInMeters(
          position!.latitude,
          position!.longitude,
          b.lat,
          b.lng,
        );
        return distanceA.compareTo(distanceB);
      });
      
      setState(() {
        hospitals = fetchedHospitals;
        isLoadingHospitals = false;
      });
      
      await addHospitalMarkersToMap();
      
      if (mounted && hospitals.isNotEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('인근 병원 ${hospitals.length}개를 찾았습니다'),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      setState(() {
        isLoadingHospitals = false;
        errorMessage = '병원 정보를 불러올 수 없습니다.';
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('병원 정보를 불러올 수 없습니다: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
            action: SnackBarAction(
              label: '다시 시도',
              textColor: Colors.white,
              onPressed: () {
                loadNearbyHospitals();
              },
            ),
          ),
        );
      }
    }
  }

  Future<void> addHospitalMarkersToMap() async {
    if (mapController == null || hospitals.isEmpty) return;
    
    for (final marker in hospitalMarkers) {
      mapController!.deleteOverlay(marker.info);
    }
    for (final infoWindow in infoWindows) {
      mapController!.deleteOverlay(infoWindow.info);
    }
    hospitalMarkers.clear();
    infoWindows.clear();
    
    int validMarkerCount = 0;
    for (int i = 0; i < hospitals.length; i++) {
      final hospital = hospitals[i];
      
      if (hospital.lat != null && 
          hospital.lng != null && 
          !hospital.lat!.isNaN && 
          !hospital.lng!.isNaN &&
          hospital.lat! >= -90 && 
          hospital.lat! <= 90 &&
          hospital.lng! >= -180 && 
          hospital.lng! <= 180) {
        
        try {
          final marker = NMarker(
            id: 'hospital_${hospital.id}',
            position: NLatLng(hospital.lat!, hospital.lng!),
          );
          
          marker.setSize(const Size(32, 32));
          
          marker.setOnTapListener((NMarker marker) {
            
            final distance = position != null
                ? DistanceHelper.getFormattedDistance(
                    position!.latitude,
                    position!.longitude,
                    hospital.lat,
                    hospital.lng,
                  )
                : '거리 정보 없음';
            
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => HospitalDetailScreen(
                  name: hospital.name,
                  phone: hospital.phone ?? '전화번호 없음',
                  address: hospital.address ?? '주소 정보 없음',
                  distance: distance,
                  lat: hospital.lat,
                  lng: hospital.lng,
                ),
              ),
            );
          });
          
          final infoWindow = NInfoWindow.onMarker(
            id: 'info_${hospital.id}',
            text: hospital.name,
          );
          
          mapController!.addOverlay(marker);
          
          mapController!.addOverlay(infoWindow);
          
          marker.openInfoWindow(infoWindow);
          
          hospitalMarkers.add(marker);
          infoWindows.add(infoWindow);
          validMarkerCount++;
          
        } catch (e) {
          print('[addHospitalMarkersToMap] 마커 추가 실패: ${hospital.name} - $e');
        }
      } else {
        print('[addHospitalMarkersToMap] 유효하지 않은 좌표: ${hospital.name} - lat: ${hospital.lat}, lng: ${hospital.lng}');
      }
    }
  }

  void updateLocationOnMap() {
    if (position != null && mapController != null) {
      if (position!.latitude.isNaN || position!.longitude.isNaN) {
        print('[updateLocationOnMap] 사용자 위치가 NaN입니다: lat=${position!.latitude}, lng=${position!.longitude}');
        return;
      }
      
      try {
        locationOverlay.setPosition(NLatLng(position!.latitude, position!.longitude));
        if (position!.heading != null && !position!.heading!.isNaN) {
          locationOverlay.setBearing(position!.heading!);
        } else {
          locationOverlay.setBearing(0);
        }
        locationOverlay.setIsVisible(true);
        
        mapController!.updateCamera(
          NCameraUpdate.fromCameraPosition(
            NCameraPosition(
              target: NLatLng(position!.latitude, position!.longitude),
              zoom: 15,
            ),
          ),
        );  
      } catch (e) {
        print('[updateLocationOnMap] 지도 업데이트 실패: $e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('주변 병원 찾기'),
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
          Container(
            height: MediaQuery.of(context).size.height * 0.4,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: NaverMap(
                options: NaverMapViewOptions(
                  initialCameraPosition: _getInitialCameraPosition(),
                  mapType: NMapType.basic,
                  activeLayerGroups: [NLayerGroup.building, NLayerGroup.transit],
                  locationButtonEnable: true,
                ),
                onMapReady: (controller) {
                  mapController = controller;
                  locationOverlay = controller.getLocationOverlay();
                  locationOverlay.setIconSize(const Size.square(24));
                  locationOverlay.setCircleRadius(20.0);
                  locationOverlay.setCircleColor(Colors.blue.withOpacity(0.3));
                  locationOverlay.setSubIcon(NOverlayImage.fromAssetImage("assets/sub.png"));
                  locationOverlay.setSubIconSize(const Size(15, 15));
                  locationOverlay.setSubAnchor(const NPoint(0.5, 1));
                  
                  if (position != null) {
                    updateLocationOnMap();
                    if (hospitals.isNotEmpty) {
                      addHospitalMarkersToMap();
                    }
                  }
                },
              ),
            ),
          ),
          Expanded(
            child: isLoading
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const CircularProgressIndicator(),
                        const SizedBox(height: 16),
                        Text(
                          isLoadingLocation 
                              ? '위치 정보를 가져오는 중...' 
                              : isLoadingHospitals 
                                  ? '주변 병원을 검색하는 중...'
                                  : '로딩 중...',
                          style: const TextStyle(
                            fontSize: 16,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  )
                : hospitals.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.local_hospital_outlined,
                              size: 64,
                              color: Colors.grey,
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              '주변 병원을 찾을 수 없습니다.',
                              style: TextStyle(fontSize: 16, color: Colors.grey),
                            ),
                            if (errorMessage != null) ...[
                              const SizedBox(height: 8),
                              Text(
                                errorMessage!,
                                style: const TextStyle(fontSize: 14, color: Colors.orange),
                                textAlign: TextAlign.center,
                              ),
                            ],
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: () {
                                getCurrentLocation();
                              },
                              child: const Text('새로고침'),
                            ),
                          ],
                        ),
                      )
                    : Column(
                        children: [
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            decoration: BoxDecoration(
                              color: Colors.green.withOpacity(0.1),
                              border: Border(
                                bottom: BorderSide(color: Colors.green.withOpacity(0.3)),
                              ),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  '인근 병원 ${hospitals.length}개 발견',
                                  style: const TextStyle(
                                    fontSize: 14,
                                    color: Colors.green,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                TextButton(
                                  onPressed: () {
                                    loadNearbyHospitals();
                                  },
                                  child: const Text(
                                    '새로고침',
                                    style: TextStyle(fontSize: 12),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Expanded(
                            child: ListView.builder(
                              itemCount: hospitals.length,
                              itemBuilder: (context, index) {
                                final hospital = hospitals[index];
                                final distance = position != null
                                    ? DistanceHelper.getFormattedDistance(
                                        position!.latitude,
                                        position!.longitude,
                                        hospital.lat,
                                        hospital.lng,
                                      )
                                    : '거리 정보 없음';
                                
                                return HospitalListItem(
                                  name: hospital.name,
                                  phone: hospital.phone ?? '전화번호 없음',
                                  address: hospital.address ?? '주소 정보 없음',
                                  distance: distance,
                                  lat: hospital.lat,
                                  lng: hospital.lng,
                                );
                              },
                            ),
                          ),
                        ],
                      ),
          ),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        selectedItemColor: Colors.blue,
        currentIndex: 1,
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
          if (index == 0) {
            final authProvider = Provider.of<AuthProvider>(context, listen: false);
            final user = authProvider.currentUser;
            
            if (user != null) {
              Navigator.pushReplacement(
                context,
                MaterialPageRoute(
                  builder: (context) => CallScreen(
                    name: user.name,
                    gender: user.gender,
                    birthYear: user.birthYear.toString(),
                    bloodType: user.medicalInfo?.bloodType ?? '미등록',
                    baseDiseases: user.medicalInfo?.baseDiseases ?? '',
                    medications: user.medicalInfo?.medications ?? '',
                    allergies: user.medicalInfo?.allergies ?? '',
                  ),
                ),
              );
            }
          }
        },
      ),
    );
  }

  NCameraPosition _getInitialCameraPosition() {
    if (position != null && 
        !position!.latitude.isNaN && 
        !position!.longitude.isNaN &&
        position!.latitude >= -90 && 
        position!.latitude <= 90 &&
        position!.longitude >= -180 && 
        position!.longitude <= 180) {
      
      return NCameraPosition(
        target: NLatLng(position!.latitude, position!.longitude),
        zoom: 15,
      );
    } else {
      if (position != null) {
        print('[getInitialCameraPosition] 사용자 위치가 유효하지 않음: lat=${position!.latitude}, lng=${position!.longitude}');
      }
      return const NCameraPosition(
        target: NLatLng(37.5665, 126.9780), //서울시청
        zoom: 10,
      );
    }
  }
}

class HospitalListItem extends StatelessWidget {
  final String name;
  final String phone;
  final String address;
  final String distance;
  final double? lat;
  final double? lng;

  const HospitalListItem({
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
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
      ),
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => HospitalDetailScreen(
                name: name,
                phone: phone,
                address: address,
                distance: distance,
                lat: lat,
                lng: lng,
              ),
            ),
          );
        },
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                name,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF4A6FA5),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.phone, size: 16, color: Colors.grey),
                  const SizedBox(width: 8),
                  Text(
                    phone,
                    style: const TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.location_on, size: 16, color: Colors.grey),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      address,
                      style: const TextStyle(fontSize: 14, color: Colors.grey),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  const Icon(Icons.directions_walk, size: 16, color: Color(0xFF4A6FA5)),
                  const SizedBox(width: 4),
                  Text(
                    distance,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF4A6FA5),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
} 