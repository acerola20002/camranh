import json
import time
from FlightRadar24 import FlightRadar24API
import datetime

fr_api = FlightRadar24API()

CITY_MAP = {
    "Incheon": "인천", "Busan": "부산", "Daegu": "대구", "Cheongju": "청주",
    "Muan": "무안", "Seoul": "서울", "Ho Chi Minh City": "호치민", "Hanoi": "하노이",
    "Nha Trang": "나트랑", "Da Nang": "다낭", "Kaohsiung": "가오슝", "Changi": "싱가포르",
    "Chengdu": "청두", "Macau": "마카오", "Hong Kong": "홍콩", "Shanghai": "상하이"
}

DOMESTIC_CITIES = ["Ho Chi Minh City", "Hanoi", "Da Nang", "Dalit", "Hai Phong", "Can Tho", "Phu Quoc", "Vinh", "Hue", "Tuy Hoa"]

def translate_status(raw_text, mode):
    status = raw_text
    if mode == 'arrivals':
        status = status.replace("Estimated", "도착예정").replace("Landed", "도착완료")
    else:
        status = status.replace("Estimated", "출발예정").replace("Landed", "이륙완료")
    status = status.replace("Scheduled", "예정").replace("Delayed", "지연")
    status = status.replace("departure", "출발").replace("arrival", "도착")
    return status

def update_data():
    try:
        # [수정] GitHub 서버 시간(UTC)에 7시간을 더해 정확한 베트남 시간을 구함
        now_vn = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
        now_vn_naive = now_vn.replace(tzinfo=None) # 비교를 위해 시간대 정보 제거
        
        raw_data = fr_api.get_airport_details("CXR")
        schedule = raw_data.get('airport', {}).get('pluginData', {}).get('schedule', {})
        
        storage = []

        for mode in ['arrivals', 'departures']:
            data_list = schedule.get(mode, {}).get('data', [])
            for f in data_list:
                flight_info = f.get('flight', {})
                if not flight_info: continue

                port_type = 'origin' if mode == 'arrivals' else 'destination'
                city_raw = flight_info.get('airport', {}).get(port_type, {}).get('position', {}).get('region', {}).get('city', 'Unknown')
                if city_raw in DOMESTIC_CITIES: continue

                t_key = 'arrival' if mode == 'arrivals' else 'departure'
                t_val = flight_info.get('time', {}).get('scheduled', {}).get(t_key)
                
                if t_val:
                    # 항공기 시간을 베트남 현지 시간으로 변환
                    f_time_vn = datetime.datetime.fromtimestamp(t_val, datetime.timezone.utc) + datetime.timedelta(hours=7)
                    f_time_vn_naive = f_time_vn.replace(tzinfo=None)

                    # 현재 베트남 시간보다 1시간 이상 지난 데이터 제외
                    if f_time_vn_naive < (now_vn_naive - datetime.timedelta(hours=1)): continue

                    date_str = f_time_vn_naive.strftime('%m/%d %H:%M')
                    
                    raw_status = flight_info.get('status', {}).get('text', '-')
                    kor_status = translate_status(raw_status, mode)
                    
                    storage.append({
                        "type": "도착" if mode == 'arrivals' else "출발",
                        "time": date_str,
                        "timestamp": t_val,
                        "flight": flight_info.get('identification', {}).get('number', {}).get('default', 'N/A'),
                        "city": CITY_MAP.get(city_raw, city_raw),
                        "status": kor_status
                    })

        if storage:
            final_list = sorted(storage, key=lambda x: x['timestamp'])
            # [수정] 표시되는 업데이트 시간 포맷 변경
            update_info = {"lastUpdate": now_vn.strftime('%Y-%m-%d %H:%M'), "data": final_list}
            
            with open('data.js', 'w', encoding='utf-8') as f:
                f.write(f"const flightInfo = {json.dumps(update_info, ensure_ascii=False, indent=4)};")
            print(f"✅ 베트남 현지 시간({now_vn.strftime('%H:%M')}) 기준 업데이트 완료")

    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    update_data()
