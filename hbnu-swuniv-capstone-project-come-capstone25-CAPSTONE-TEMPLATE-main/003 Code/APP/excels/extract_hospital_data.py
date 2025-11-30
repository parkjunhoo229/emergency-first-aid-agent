import pandas as pd
import pymysql
import os
import glob
import requests
from pathlib import Path

client_id = '1wckuw9fvb'
client_secret = 'yBoawuYXwXW5KjvNoi0QyusX43Jc0MzTpJjHpynQ'

def extract_hospital_data():
    
    excel_pattern = 'emergency_rooms_*.xlsx'
    excel_files = glob.glob(excel_pattern)
    
    excel_files = [f for f in excel_files if not os.path.basename(f).startswith('~')]
    
    print(f"발견된 엑셀 파일 수: {len(excel_files)}")
    
    all_hospitals = []
    
    for excel_file in excel_files:
        print(f"처리 중: {excel_file}")
        
        try:
            df = pd.read_excel(excel_file, header=None)
            
            for idx in range(1, len(df)):
                hospital_name = df.iloc[idx, 1]
                phone = df.iloc[idx, 3]
                address = df.iloc[idx, 4]
                
                if pd.notna(hospital_name) and pd.notna(phone) and pd.notna(address):
                    region = excel_file.replace('emergency_rooms_', '').replace('_all.xlsx', '')
                    
                    hospital_data = {
                        'name': str(hospital_name).strip(),
                        'phone': str(phone).strip(),
                        'address': str(address).strip(),
                        'region': region
                    }

                    lat, lng = geocode_address(address)
                    hospital_data['lat'] = lat
                    hospital_data['lng'] = lng
                    
                    all_hospitals.append(hospital_data)
                    
        except Exception as e:
            print(f"파일 {excel_file} 처리 중 오류 발생: {e}")
            continue
    
    print(f"총 추출된 병원 수: {len(all_hospitals)}")
    
    try:
        conn = pymysql.connect(host='127.0.0.1', user='root', password='0164', db='medicall', charset='utf8mb4')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hospitals (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                region TEXT,
                lat FLOAT,
                lng FLOAT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        cursor.execute('DELETE FROM hospitals')
        
        for hospital in all_hospitals:
            cursor.execute('''
                INSERT INTO hospitals (name, phone, address, region, lat, lng)
                VALUES (%s, %s, %s, %s, %s, %s);
            ''', (hospital['name'], hospital['phone'], hospital['address'], hospital['region'], hospital['lat'], hospital['lng']))
        
        conn.commit()
        print(f"데이터베이스에 {len(all_hospitals)}개의 병원 데이터가 저장되었습니다.")
        
        cursor.execute('SELECT COUNT(*) FROM hospitals')
        count = cursor.fetchone()[0]
        print(f"데이터베이스 총 레코드 수: {count}")
        
    except Exception as e:
        print(f"데이터베이스 처리 중 오류 발생: {e}")
    finally:
        if conn:
            conn.close()

def geocode_address(address):
    global client_id, client_secret
    url = f"https://maps.apigw.ntruss.com/map-geocode/v2/geocode?query={address}"
    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_secret
        }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['addresses']:
            location = data['addresses'][0]
            return location['y'], location['x']
        else:
            return None, None
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None, None

if __name__ == "__main__":
    extract_hospital_data() 