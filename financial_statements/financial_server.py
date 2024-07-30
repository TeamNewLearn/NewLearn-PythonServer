from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import dart_fss as dart
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import json

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

api_key = os.getenv('DART_API_KEY')
dart.set_api_key(api_key=api_key)

# DART에 공시된 회사 리스트 불러오기
corp_list = dart.get_corp_list()

def get_company_code(company_name):
    corp_info = corp_list.find_by_corp_name(company_name, exactly=True)
    if corp_info:
        return corp_info[0].corp_code
    return None

def get_start_date(years):
    today = datetime.today()
    start_date = today - timedelta(days=365 * years)
    return start_date.strftime('%Y%m%d')

class FinancialRequest(BaseModel):
    company_name: str
    period: int

@app.post('/financial_statements')
async def financial_statements(request: FinancialRequest):
    company_name = request.company_name
    period = request.period

    if period not in [3, 5]:
        raise HTTPException(status_code=400, detail='Invalid period. Please choose 3 or 5 years.')

    company_code = get_company_code(company_name)
    if not company_code:
        raise HTTPException(status_code=404, detail='Company not found.')

    start_date = get_start_date(period)

    corp_info = corp_list.find_by_corp_code(company_code)
    fs = corp_info.extract_fs(bgn_de=start_date, report_tp='quarter')
    df_is = fs['is']

    # 컬럼 이름을 간결하게 변환하고 중복 제거
    def simplify_column_name(col):
        if isinstance(col, tuple):
            simplified_name = re.sub(r'\[.*?\]|\(.*?\)|\s\|\s.*', '', col[0])
            simplified_name = re.sub(r'[^a-zA-Z0-9가-힣]', '', simplified_name)  # 특수 문자 제거
            simplified_name = re.sub(r'\s+', ' ', simplified_name).strip()  # 불필요한 공백 제거
            return simplified_name
        return col

    df_is.columns = [simplify_column_name(col) for col in df_is.columns]

    # 중복된 컬럼 이름에 인덱스 추가
    def make_unique(column_names):
        seen = {}
        for idx, name in enumerate(column_names):
            if name in seen:
                seen[name] += 1
                column_names[idx] = f"{name}_{seen[name]}"
            else:
                seen[name] = 0
        return column_names

    df_is.columns = make_unique(df_is.columns.tolist())

    # 특수 기호 및 불필요한 문자 제거 후 데이터 프레임을 JSON으로 변환
    result_json = df_is.to_json(orient='records', force_ascii=False)

    return json.loads(result_json)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
