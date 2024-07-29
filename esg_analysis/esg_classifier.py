from fastapi import FastAPI, HTTPException
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
from pydantic import BaseModel
import mysql.connector
import concurrent.futures
import score_config
import config
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

app = FastAPI()

# 데이터베이스 설정
DB_CONFIG = config.get_db_config()

def load_models():
    esg_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-esg', num_labels=4)
    esg_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-esg')
    esg_nlp = pipeline("text-classification", model=esg_model, tokenizer=esg_tokenizer, truncation=True, max_length=512)

    category_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-esg-9-categories', num_labels=9)
    category_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-esg-9-categories')
    category_nlp = pipeline("text-classification", model=category_model, tokenizer=category_tokenizer, truncation=True, max_length=512)

    sentiment_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-tone', num_labels=3)
    sentiment_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-tone')
    sentiment_nlp = pipeline("text-classification", model=sentiment_model, tokenizer=sentiment_tokenizer, truncation=True, max_length=512)

    fls_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-fls', num_labels=3, ignore_mismatched_sizes=True)
    fls_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-fls')
    fls_nlp = pipeline("text-classification", model=fls_model, tokenizer=fls_tokenizer, truncation=True, max_length=512)

    return esg_nlp, category_nlp, sentiment_nlp, fls_nlp

def get_news_articles(company_code):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    query = "SELECT news_id, translated_title, translated_body, original_title FROM news WHERE stock_code = %s"
    cursor.execute(query, (company_code,))
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    return articles

def classify_article(nlp_pipeline, article_content):
    return nlp_pipeline(article_content)

def calculate_investment_score(esg_label, esg_category, esg_sentiment, esg_fls):
    score = 0
    score += score_config.ESG_LABEL_SCORES.get(esg_label, 0)
    score += score_config.CATEGORY_SCORES.get(esg_category, 0)
    category_label_mapping = {
        'Climate Change': 'Environmental',
        'Natural Capital': 'Environmental',
        'Pollution & Waste': 'Environmental',
        'Human Capital': 'Social',
        'Product Liability': 'Social',
        'Community Relations': 'Social',
        'Corporate Governance': 'Governance',
        'Business Ethics & Values': 'Governance'
    }
    if category_label_mapping.get(esg_category) == esg_label:
        score += score_config.CATEGORY_MATCH_BONUS
    score += score_config.SENTIMENT_SCORES.get(esg_sentiment, 0)
    score += score_config.FLS_SCORES.get(esg_fls, 0)
    return score

def save_esg_result(news_id, article_title, esg_label, esg_score):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    query = """
        INSERT INTO esg_result (news_id, article_title, esg_label, esg_score)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (news_id, article_title, esg_label, esg_score))
    conn.commit()
    cursor.close()
    conn.close()

class ESGRequest(BaseModel):
    company_name: str

@app.post('/esg_analysis')
async def esg_analysis(request: ESGRequest):
    company_name = request.company_name

    # 회사 코드를 변환하는 로직 추가
    company_code = get_company_code(company_name)
    if not company_code:
        raise HTTPException(status_code=404, detail="Company code not found for the given company name.")

    articles = get_news_articles(company_code)

    if not articles:
        raise HTTPException(status_code=404, detail=f"No articles found for the given company code: {company_code}")

    esg_nlp, category_nlp, sentiment_nlp, fls_nlp = load_models()

    results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(classify_article, esg_nlp, article['translated_body']): article for article in articles}

        for future in concurrent.futures.as_completed(futures):
            article = futures[future]
            try:
                esg_results = future.result()
                esg_label = max(esg_results, key=lambda x: x['score'])['label']

                # Process category, sentiment, and fls models in parallel
                category_result = classify_article(category_nlp, article['translated_body'])
                sentiment_result = classify_article(sentiment_nlp, article['translated_body'])
                fls_result = classify_article(fls_nlp, article['translated_body'])

                esg_category = max(category_result, key=lambda x: x['score'])['label']
                esg_sentiment = max(sentiment_result, key=lambda x: x['score'])['label']
                esg_fls = max(fls_result, key=lambda x: x['score'])['label']

                esg_score = calculate_investment_score(esg_label, esg_category, esg_sentiment, esg_fls)

                # 결과 저장
                save_esg_result(article['news_id'], article['original_title'], esg_label, esg_score)

                results.append({
                    "기사 ID": article['news_id'],
                    "기사 한글명": article['original_title'],
                    "기사 ESG 분야": esg_label,
                    "기사 ESG 점수": esg_score
                })
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc))

    return results

def get_company_code(company_name):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    query = "SELECT stock_code FROM stock_info WHERE stock_name = %s"
    cursor.execute(query, (company_name,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['stock_code'] if result else None

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
