from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import dart_fss as dart
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import json
import sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

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


# 회사 코드 조회 함수
def get_company_code(company_stock_code):
    corp_info = corp_list.find_by_stock_code(company_stock_code)
    return corp_info if corp_info else None


def get_start_date(years):
    today = datetime.today()
    start_date = today - timedelta(days=365 * years)
    return start_date.strftime('%Y%m%d')


# DART API 에러 처리
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
        # dart_fss 라이브러리 외의 일반적인 예외 처리
        raise HTTPException(status_code=500, detail=f"서버에서 알 수 없는 오류가 발생했습니다: {str(err)}")


# API 요청 파라미터 정의
class FinancialRequest(BaseModel):
    company_stock_code: str
    period: int


# 재무제표 호출 API 정의
@app.post('/financial_statements')
async def financial_statements(request: FinancialRequest):
    company_stock_code = request.company_stock_code
    period = request.period

    if period not in [3, 5]:
        raise HTTPException(status_code=400, detail='유효하지 않은 기간입니다. 3년 또는 5년을 선택해 주세요.')

    company_code = get_company_code(company_stock_code)
    if not company_code:
        raise HTTPException(status_code=404, detail='해당 기업을 찾을 수 없습니다.')

    start_date = get_start_date(period)
    try:
        fs = company_code.extract_fs(bgn_de=start_date,
                                     report_tp='quarter')  # 기존 corp_info.extract_fs에서 company_code.extract_fs로 변경
    except (dart.errors.NoDataReceived, dart.errors.APIKeyError, dart.errors.TemporaryLocked,
            dart.errors.OverQueryLimit, dart.errors.InvalidField, dart.errors.ServiceClose,
            dart.errors.UnknownError, RuntimeError) as e:
        error_handle(e)

    try:
        df_statement = fs['is']
        if df_statement is None:
            raise KeyError  # Trigger the switch to 'cis' if 'is' is empty
    except KeyError:
        df_statement = fs['cis']
        if df_statement is None:
            raise HTTPException(status_code=404, detail="포괄 손익계산서 데이터가 비어있습니다.")

    df_statement.columns = [simplify_column_name(col) for col in df_statement.columns]

    df_statement.columns = make_unique(df_statement.columns.tolist())

    result_json = df_statement.to_json(orient='records', force_ascii=False)
    return json.loads(result_json)


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


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
