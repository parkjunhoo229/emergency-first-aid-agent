설치 가이드

파이썬 설치
https://www.python.org/downloads/windows 접속(윈도우 기준)
파이썬 설치
이 때, Install Python 3.xx for all users 선택(pip 경로 잡기 쉬움)
==파이썬 설치 후==
환경변수 설정(\bin폴더 등록)

MySQL 설치 + DB 생성
https://dev.mysql.com/downloads/mysql/ 접속
8 버전 선택 후 설치
==MySQL 설치 후==
환경변수 설정(\bin폴더 등록)
cmd창에서 mysql -uroot -p{password}로 접속
create database medical;

파이썬 라이브러리 설치
cmd창 열고 Integration 폴더로 이동(cd 명령어 이용)
pip install -r requirements.txt
이후 pip install pandas pymysql glob requests

지도 데이터 설정
cmd창에서 excels 폴더로 이동(또는 medical (1))
extract_hospital_data.py를 메모장으로 열어서 db정보 수정
python extract_hospital_data.py로 실행

Vscode 설치
https://code.visualstudio.com/Download 접속 후 설치

AVD+Flutter 설치
https://codingapple.com/unit/flutter-install-on-windows-and-mac/
https://blog.naver.com/querydb/223925747860
==설치 후==
Android Studio 열어서 AVD 만들기

프로젝트 실행
백엔드 서버 실행(integration)
cmd창에서 integration 폴더 이동 후 python main.py

vscode에서 medicall 프로젝트 열기
Ctrl+Shift+P로 Palette 열고 select 검색 후 Flutter: Select Device 선택
이 후 6번에서 만든 안드로이드 기기 선택

Vscode 상단의 터미널(또는 Terminal) 눌러서 새 터미널 클릭
Flutter run 입력 후 엔터
