import os
import json
from pathlib import Path

def is_date_key(key):
    # 숫자로만 구성된 키인지 확인
    try:
        int(key[:4])  # 첫 네 글자가 연도 형식인지 (예: '2023')
        int(key[4:])  # 나머지 글자도 숫자인지 확인
        return True
    except ValueError:
        return False

def update_json_files(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    for file_name in json_files:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        updated_data = []
        for item in data:
            new_item = {}
            period_data = {}  # 기간별 데이터를 저장할 딕셔너리

            for k, v in item.items():
                if k.endswith('_1'):
                    new_item['Name'] = v  # '_1'로 끝나는 키를 'Name'으로 이름 변경
                elif is_date_key(k):
                    period_data[k] = v  # 날짜 키는 periodData 내에 저장

            if period_data:
                new_item['periodData'] = period_data  # periodData를 new_item에 추가

            if new_item:  # new_item이 비어 있지 않다면 결과 목록에 추가
                updated_data.append(new_item)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(updated_data, file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    dir_path = Path(__file__).parent / 'stored_fin_data'
    update_json_files(str(dir_path))
