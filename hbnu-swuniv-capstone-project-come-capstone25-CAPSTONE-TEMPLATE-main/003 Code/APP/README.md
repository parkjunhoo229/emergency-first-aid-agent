설치 가이드

1. 파이썬 설치
https://www.python.org/downloads/windows 접속(윈도우 기준)
파이썬 설치
이 때, Install Python 3.xx for all users 선택(pip 경로 잡기 쉬움)
==파이썬 설치 후==
환경변수 설정(\bin폴더 등록)

2. MySQL 설치 + DB 생성
https://dev.mysql.com/downloads/mysql/ 접속
8 버전 선택 후 설치
==MySQL 설치 후==
환경변수 설정(\bin폴더 등록)
cmd창에서 mysql -uroot -p{password}로 접속
create database medical;

3. 파이썬 라이브러리 설치
cmd창 열고 Integration 폴더로 이동(cd 명령어 이용)
pip install -r requirements_win.txt
이후 pip install pandas pymysql glob requests

4. 지도 데이터 설정
cmd창에서 excels 폴더로 이동(또는 medical (1))
extract_hospital_data.py를 메모장으로 열어서 db정보 수정
python extract_hospital_data.py로 실행

5. Vscode 설치
https://code.visualstudio.com/Download 접속 후 설치

6. AVD+Flutter 설치
https://codingapple.com/unit/flutter-install-on-windows-and-mac/
https://blog.naver.com/querydb/223925747860
==설치 후==
Android Studio 열어서 AVD 만들기

7. 프로젝트 실행
1)
노트북 Lan선 연결
노트북 핫스팟열기
핸드폰을 핫스팟 wifi 연결

2)
cmd에서 ipconfig로 노트북 lan주소 알아내서
medical > lib> services 의 파일 내부에서 geolocator제외하고 다 수정
'http://      :5000/api'<< 여기에 :5000전에 붙여넣기 

3)(창 2개 띄워야함)
cmd에 cd C:\capston3\integration

4)(창 2개 띄워야함)
가상환경 활성화
.\venv\Scripts\activate 이거 입력하면
(venv) C:\capston3\integration> 이렇게 뜰거임

5)(창 1)
서버실행(창 절대 닫으면 안됨)
python main.py
성공시 INFO:     Application startup complete.<< 메세지뜸
핸드폰으로 아래 주소 접속해서 잘 열렸는지 테스트 가능
http://192.168.137.1:5000/docs

6)(창 2)
서버실행(창 절대 닫으면 안됨)
uvicorn fake_119_server:app --host 0.0.0.0 --port 6000 --reload
신고 오면 여기 콘솔에 payload가 찍힘

7)
비쥬얼 코드에서
cd medicall

8) 
flutter devices 입력 → ex) SM_xxxx 뜨면 핸드폰 연결된거임

9)
flutter run으로 핸드폰에서 실행

