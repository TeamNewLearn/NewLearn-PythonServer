# -*- coding: utf-8 -*-

import requests


class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def execute(self, completion_request):
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        with requests.post(self._host + '/testapp/v1/chat-completions/HCX-003',
                           headers=headers, json=completion_request, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    print(line.decode("utf-8"))


if __name__ == '__main__':
    completion_executor = CompletionExecutor(
        host='https://clovastudio.stream.ntruss.com',
        api_key='NTA0MjU2MWZlZTcxNDJiY3yxnq5hnK4fYMmH64Rn/C9eAew055It0Yp6L7OLRzfe',
        api_key_primary_val='cRbdXrrXjI2tQgnbePLk9FUGUewSgGRMB3OSTmxv',
        request_id='5766f037-af44-4261-8356-25060d1fdbf9'
    )

    preset_text = [{"role":"system","content":"당신은 주식의 ESG 보고서, 주식 분석 결과를 전달받고 이를 해석하는 주식 투자 전문가입니다.\n\nESG 보고서와 주식의 시계열 모델을 이용하여 판단하고 2가지 모두 좋을 때 투자하라고 권유하면 됩니다.\n\n투자할 때는 왜 그런지 이유를 설명해야 합니다.\n또한 응답을 줄 때 JSON 형태로 출력해줘야 합니다.\n\n{\n\"투자 판단\": \"Good\",\n\"이유\": \"String\"\n}\n와 같은 형식으로 주어야 합니다."}]

    request_data = {
        'messages': preset_text,
        'topP': 0.8,
        'topK': 0,
        'maxTokens': 642,
        'temperature': 0.5,
        'repeatPenalty': 5.0,
        'stopBefore': [],
        'includeAiFilters': True,
        'seed': 0
    }

    print(preset_text)
    completion_executor.execute(request_data)
