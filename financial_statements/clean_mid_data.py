import os
import json
from pathlib import Path

def remove_intermediate_period_data(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    for file_name in json_files:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # 수정된 데이터를 준비
        updated_data = []
        for item in data:
            if 'periodData' in item:
                sorted_keys = sorted(item['periodData'].keys())  # 키를 시간 순으로 정렬
                if len(sorted_keys) > 2:
                    # 첫 번째와 마지막 키만 유지
                    first_key = sorted_keys[0]
                    last_key = sorted_keys[-1]
                    item['periodData'] = {
                        first_key: item['periodData'][first_key],
                        last_key: item['periodData'][last_key]
                    }
            updated_data.append(item)

        # 수정된 데이터를 파일에 다시 쓰기
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(updated_data, file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    dir_path = Path(__file__).parent / 'stored_fin_data'
    remove_intermediate_period_data(str(dir_path))
