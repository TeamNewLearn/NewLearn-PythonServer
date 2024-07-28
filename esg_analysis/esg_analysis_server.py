from flask import Flask, request, jsonify
from esg_classifier import process_article

app = Flask(__name__)

@app.route('/esg_result', methods=['POST'])
def esg_result():
    try:
        data = request.json
        api_url = data['api_url']
        api_key = data['api_key']
        article_id = data['article_id']

        # ESG 분석 수행
        result = process_article(api_url, api_key, article_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
