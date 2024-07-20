# -*- coding: utf-8 -*-

import requests, json
import hyperclova_prompt as prompt


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
            # 'Accept': 'text/event-stream' #문자 스트림(실시간 응답) 속성 여부-필요시 주석 해제
        }

        with requests.post(self._host + '/testapp/v1/chat-completions/HCX-003',
                           headers=headers, json=completion_request, stream=False) as r:
            for line in r.iter_lines():
                if line:
                    response_json = line.decode("utf-8")
                    response_dict = json.loads(response_json)
                    print(response_dict['result']['message']['content'])

            # 원본 코드
            # for line in r.iter_lines():
            #     if line:
            #         print(line.decode("utf-8"))



if __name__ == '__main__':
    completion_executor = CompletionExecutor(
        host='https://clovastudio.stream.ntruss.com',
        api_key='NTA0MjU2MWZlZTcxNDJiY3yxnq5hnK4fYMmH64Rn/C9eAew055It0Yp6L7OLRzfe',
        api_key_primary_val='cRbdXrrXjI2tQgnbePLk9FUGUewSgGRMB3OSTmxv',
        request_id='5766f037-af44-4261-8356-25060d1fdbf9'
    )

    preset_text = [{"role":"system","content":prompt.preset},
                    {"role" : "user", "content" : """삼성전자, E:Good, S:Good, G:Bad", 주가: "상승"""}, 
                   ]

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
