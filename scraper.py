import json
import time
from FlightRadar24 import FlightRadar24API
import datetime

fr_api = FlightRadar24API()

# 도시 매핑 리스트 (더 많은 도시와 오타 방지용 보강)
CITY_MAP = {
    "Incheon": "인천", "Busan": "부산", "Daegu": "대구", "Cheongju": "청주",
    "Muan": "무안", "Seoul": "서울", "Ho Chi Minh City": "호치민", "Hanoi": "하노이",
    "Nha Trang": "나트랑", "Da Nang": "다낭", "Kaohsiung": "가오슝", "Changi": "싱가포르",
    "Chengdu": "청두", "Macau": "마카오", "Macau SAR": "마카오", "Hong Kong": "홍콩", 
    "Shanghai": "상하이", "Taipei": "타이베이", "Bangkok": "방콕"
}

# 베트남 국내선 목록 (국제선 전광판이므로 제외 대상)
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
        # 1. 시간 설정: GitHub 서버(UTC) 기준 베트남 시간(UTC+7) 계산
        now_vn = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
        now_vn_naive = now_vn.replace(tzinfo=None)
        
        # 2. 깜라인 공항(CXR) 데이터 가져오기
        raw_data = fr_api.get_airport_details("CXR")
        schedule = raw_data.get('airport', {}).get('pluginData', {}).get('schedule', {})
        
        storage = []

        for mode in ['arrivals', 'departures']:
            data_list = schedule.get(mode, {}).get('data', [])
            for f in data_list:
                flight_info = f.get('flight', {})
                if not flight_info: continue

                # 도착지는 origin, 출발지는 destination 정보를 가져옴
                port_type = 'origin' if mode == 'arrivals' else 'destination'
                city_raw = flight_info.get('airport', {}).get(port_type, {}).get('position', {}).get('region', {}).get('city', 'Unknown')
                
                # [보강] 국내선 제외 및 도시 이름 한글 변환
                if city_raw in DOMESTIC_CITIES: continue

                # [보강] 마카오, 홍콩 등 특수 명칭 예외 처리
                display_city = CITY_MAP.get(city_raw, city_raw)
                if "Macau" in city_raw:
                    display_city = "마카오"
                elif "Hong Kong" in city_raw:
                    display_city = "홍콩"

                t_key = 'arrival' if mode == 'arrivals' else 'departure'
                t_val = flight_info.get('time', {}).get('scheduled', {}).get(t_key)
                
                if t_val:
                    # 항공편 시간을 베트남 현지 시간으로 변환
                    f_time_vn = datetime.datetime.fromtimestamp(t_val, datetime.timezone.utc) + datetime.timedelta(hours=7)
                    f_time_vn_naive = f_time_vn.replace(tzinfo=None)

                    # 현재 베트남 시간보다 1시간 이상 지난 데이터는 목록에서 제외
                    if f_time_vn_naive < (now_vn_naive - datetime.timedelta(hours=1)): continue

                    date_str = f_time_vn_naive.strftime('%m/%d %H:%M')
                    
                    raw_status = flight_info.get('status', {}).get('text', '-')
                    kor_status = translate_status(raw_status, mode)
                    
                    storage.append({
                        "type": "도착" if mode == 'arrivals' else "출발",
                        "time": date_str,
                        "timestamp": t_val,
                        "flight": flight_info.get('identification', {}).get('number', {}).get('default', 'N/A'),
                        "city": display_city,
                        "status": kor_status
                    })

        if storage:
            # 시간순 정렬
            final_list = sorted(storage, key=lambda x: x['timestamp'])
            
            # 최종 JSON 데이터 생성
            update_info = {
                "lastUpdate": now_vn.strftime('%Y-%m-%d %H:%M'), 
                "data": final_list
            }
            
            # data.js 파일로 저장
            with open('data.js', 'w', encoding='utf-8') as f:
                f.write(f"const flightInfo = {json.dumps(update_info, ensure_ascii=False, indent=4)};")
            
            print(f"✅ 업데이트 완료: 베트남 현지 시각 {now_vn.strftime('%Y-%m-%d %H:%M')}")

    except Exception as e:
        print(f"❌ 데이터 업데이트 중 오류 발생: {e}")

if __name__ == "__main__":
    update_data()
