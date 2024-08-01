from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json

class SkillSetFinalAnswerExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def execute(self, skill_set_cot_request):

        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json',
        }

        response = requests.post(
            self._host + '/testapp/v1/skillsets/pxzpzfac/versions/11/final-answer',
            headers=headers,
            data=json.dumps(skill_set_cot_request)
        )

        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line_data = json.loads(line.decode("utf-8"))
                    final_answer_str = line_data.get("result", {}).get("finalAnswer")
                    if final_answer_str:
                        try:
                            final_answer_data = json.loads(final_answer_str)
                            return final_answer_data
                        except json.JSONDecodeError:
                            return None
        return None

app = FastAPI()

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인에서의 접근을 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드를 허용
    allow_headers=["*"],  # 모든 헤더를 허용
)

class QueryRequest(BaseModel):
    query: str

@app.post("/clova_chat")
def clova_chat(request: QueryRequest):

    final_answer_executor = SkillSetFinalAnswerExecutor(
        host='https://clovastudio.stream.ntruss.com',
        api_key='NTA0MjU2MWZlZTcxNDJiYx5nJ9z87DKxlyRynnpD92tzfGHkZUwGbaaySiF5jj/d',
        api_key_primary_val='EJWfdqk0rE2FRZtyWjwqUSBXdXZfZjBpMS0EUACu',
        request_id='cb3bb9b7-88fb-469f-9301-af25338a4ca6'
    )

    request_data = {
        "query": request.query,
        "tokenStream": False,
    }

    final_answer = final_answer_executor.execute(request_data)
    if final_answer:
        return final_answer
    else:
        return {"error": "Failed to retrieve final answer"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
