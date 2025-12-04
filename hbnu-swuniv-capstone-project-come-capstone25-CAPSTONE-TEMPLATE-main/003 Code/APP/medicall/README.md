# Medicall 프로젝트 설치 / 실행 가이드 (Windows 기준)

이 문서는 Medicall 프로젝트를 백엔드(Integration), 119 서버, Flutter 앱까지 전체 실행 환경을 구축하는 방법을 설명합니다.

## 1. 파이썬 설치
1. https://www.python.org/downloads/windows 접속
2. Python 3.xx 설치
3. Install Python 3.xx for all users 옵션 선택

### 설치 후
- 시스템 환경변수에 Python 설치 경로(\Scripts, in)가 등록되어 있는지 확인

## 2. MySQL 설치 + DB 생성
1. https://dev.mysql.com/downloads/mysql 접속
2. MySQL 8.x 버전 다운로드 및 설치

### 설치 후
```
mysql -uroot -p{password}
```
이후:
```sql
create database medical;
```

## 3. 파이썬 라이브러리 설치
```
cd C:\capston3\integration
pip install -r requirements_win.txt
pip install pandas pymysql glob requests
```

## 4. 지도 데이터 설정
```
cd excels  # 또는 medical (1)
```
- extract_hospital_data.py 파일의 DB 정보 수정
```
python extract_hospital_data.py
```

## 5. VS Code 설치
https://code.visualstudio.com/Download

## 6. AVD + Flutter 설치
- Flutter 및 AVD 설치 가이드 참고:
  - https://codingapple.com/unit/flutter-install-on-windows-and-mac/
  - https://blog.naver.com/querydb/223925747860

## 7. 프로젝트 실행

### 1) 네트워크 설정
- 노트북 LAN 연결
- 노트북 핫스팟 활성화
- 스마트폰을 해당 핫스팟에 연결

### 2) Flutter API URL 설정
```
ipconfig
```
- medical/lib/services 내부 파일에서 geolocator 제외 모든 URL 수정:

```
http://<노트북_IP>:5000/api
예) http://192.168.137.1:5000/api
```

### 3) Integration 서버 준비 (창 1, 창 2 필요)
```
cd C:\capston3\integration
```

### 4) 가상환경 활성화 (두 창 모두)
```
.env\Scriptsctivate
```

### 5) 백엔드 서버 실행 (창 1)
```
python main.py
```
성공 메시지:
```
INFO:     Application startup complete.
```

접속 테스트:
```
http://192.168.137.1:5000/docs
```

### 6) 119 서버 실행 (창 2)
```
uvicorn fake_119_server:app --host 0.0.0.0 --port 6000 --reload
```

## 8. Flutter 앱 실행
```
cd medicall
flutter devices
flutter run
```

