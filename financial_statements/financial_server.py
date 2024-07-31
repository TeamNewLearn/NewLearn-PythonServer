from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import dart_fss as dart
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import json
import sys
from pathlib import Path
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from company_code_list import company_codes

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from company_code_list import company_codes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

api_key='698e1025376cfbf1631574822d5744a07b1c30ea'
dart.set_api_key(api_key=api_key)

corp_list = dart.get_corp_list()

def get_company_code(company_stock_code):
    corp_info = corp_list.find_by_stock_code(company_stock_code)
    print(corp_info)
    return corp_info if corp_info else None

def get_start_date(years):
    today = datetime.today()
    start_date = today - timedelta(days=365 * years)
    return start_date.strftime('%Y%m%d')

def error_handle(err):
    if isinstance(err, dart.errors.NoDataReceived):
        raise HTTPException(status_code=404, detail="요청한 기업의 재무 데이터가 존재하지 않습니다.")
    elif isinstance(err, dart.errors.APIKeyError):
        raise HTTPException(status_code=401, detail="등록되지 않은 API 키입니다.")
    elif isinstance(err, dart.errors.TemporaryLocked):
        raise HTTPException(status_code=429, detail="임시적으로 API 사용이 제한되었습니다.")
    elif isinstance(err, dart.errors.OverQueryLimit):
        raise HTTPException(status_code=429, detail="쿼리 한도를 초과하였습니다.")
    elif isinstance(err, dart.errors.InvalidField):
        raise HTTPException(status_code=400, detail="유효하지 않은 필드입니다.")
    elif isinstance(err, dart.errors.ServiceClose):
        raise HTTPException(status_code=503, detail="현재 서비스가 종료되었습니다.")
    elif isinstance(err, dart.errors.UnknownError):
        raise HTTPException(status_code=500, detail="알 수 없는 오류가 발생했습니다.")
    else:
        raise HTTPException(status_code=500, detail=f"서버에서 알 수 없는 오류가 발생했습니다: {str(err)}")

def simplify_column_name(col):
    if isinstance(col, tuple):
        simplified_name = re.sub(r'\[.*?\]|\(.*?\)|\s\|\s.*', '', col[0])
        simplified_name = re.sub(r'[^a-zA-Z0-9가-힣]', '', simplified_name)
        simplified_name = re.sub(r'\s+', ' ', simplified_name).strip()
        return simplified_name
    return col

def make_unique(column_names):
    seen = {}
    for idx, name in enumerate(column_names):
        if name in seen:
            seen[name] += 1
            column_names[idx] = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
    return column_names

# 재무제표 저장
@app.get('/save_financial_statements')
async def financial_statements():
    output_dir = os.path.join(os.path.dirname(__file__), 'stored_fin_data')
    os.makedirs(output_dir, exist_ok=True)

    for code in company_codes:
        corp_info = get_company_code(code)
        if not corp_info:
            continue

        for period in [1, 3]:
            # start_date = get_start_date(period)
            start_date = '20240101'
            end_date = '20240731'
            try:
                fs = corp_info.extract_fs(bgn_de=start_date, end_de=end_date, report_tp='annual', lang='ko',
                                          last_report_only=True, dataset='web') # annual / half / quarter
                try:
                    df_statement = fs['is']
                    if df_statement is None:
                        raise KeyError
                except KeyError:
                    df_statement = fs['cis']
                    if df_statement is None:
                        raise HTTPException(status_code=404, detail="포괄 손익계산서 데이터가 비어있습니다.")

                df_statement.columns = [simplify_column_name(col) for col in df_statement.columns]
                df_statement.columns = make_unique(df_statement.columns.tolist())
                result_json = df_statement.to_json(orient='records', force_ascii=False)
                
                file_path = os.path.join(output_dir, f"{code}_{period+2}.json")
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(result_json)
            except Exception as e:
                error_handle(e)
                continue

    return {"message": "Financial statements have been processed and saved."}



# API 요청 파라미터 정의
class FinancialRequest(BaseModel):
    company_stock_code: str
    period: int

@app.post('/financial_statements')
async def get_financial_statement(data: FinancialRequest):
    if data.period not in [3, 5]:
        raise HTTPException(status_code=400, detail='유효하지 않은 기간입니다. 3년 또는 5년을 선택해 주세요.')

    file_path = os.path.join(os.path.dirname(__file__), 'stored_fin_data', f"{data.company_stock_code}_{data.period}.json")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = json.load(file)
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="해당 파일을 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일을 읽는 중 오류가 발생했습니다: {str(e)}")



if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
