from fastapi import FastAPI, HTTPException
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
from pydantic import BaseModel
import mysql.connector
import concurrent.futures
import score_config
import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
DB_CONFIG = config.get_db_config()

def load_models():
    try:
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
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        raise HTTPException(status_code=500, detail="Error loading models")

def get_news_articles(company_code):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT news_id, translated_title, translated_body, original_title FROM news WHERE stock_code = %s"
        cursor.execute(query, (company_code,))
        articles = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"Fetched {len(articles)} articles for company code {company_code}")
        return articles
    except mysql.connector.Error as e:
        logger.error(f"Error fetching news articles: {e}")
        raise HTTPException(status_code=500, detail="Error fetching news articles")

def classify_article(nlp_pipeline, article_content):
    try:
        return nlp_pipeline(article_content)
    except Exception as e:
        logger.error(f"Error classifying article: {e}")
        raise HTTPException(status_code=500, detail="Error classifying article")

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

def save_esg_result(news_id, article_title, esg_label, esg_score, stock_code):
    if esg_label is None:
        logger.warning("ESG Label is None, not saving result")
        return  # esg_label이 None일 경우 저장하지 않음
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 중복 확인
        check_query = "SELECT COUNT(*) FROM esg_result WHERE news_id = %s"
        cursor.execute(check_query, (news_id,))
        count = cursor.fetchone()['COUNT(*)']

        if count > 0:
            logger.warning(f"ESG result for news_id {news_id} already exists, not saving result")
        else:
            query = """
                INSERT INTO esg_result (news_id, article_title, esg_label, esg_score, stock_code)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (news_id, article_title, esg_label, esg_score, stock_code))
            conn.commit()
            logger.info(f"Saved ESG result for news_id {news_id}")

        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
        logger.error(f"Error saving ESG result: {e}")
        raise HTTPException(status_code=500, detail="Error saving ESG result")

class ESGRequest(BaseModel):
    company_name: str

# 기업 기사 ESG 분석
@app.post('/esg_analysis')
async def esg_analysis(request: ESGRequest):
    company_name = request.company_name

    company_code = get_company_code(company_name)
    if not company_code:
        logger.warning(f"Company code not found for company name {company_name}")
        raise HTTPException(status_code=404, detail="Company code not found for the given company name.")

    articles = get_news_articles(company_code)

    if not articles:
        logger.warning(f"No articles found for company code {company_code}")
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

                if esg_label == "None":
                    logger.warning(f"ESG Label is None for article {article['news_id']}")
                    continue  # esg_label이 None이면 이 기사 생략

                # Process category, sentiment, and fls models in parallel
                category_result = classify_article(category_nlp, article['translated_body'])
                sentiment_result = classify_article(sentiment_nlp, article['translated_body'])
                fls_result = classify_article(fls_nlp, article['translated_body'])

                esg_category = max(category_result, key=lambda x: x['score'])['label']
                esg_sentiment = max(sentiment_result, key=lambda x: x['score'])['label']
                esg_fls = max(fls_result, key=lambda x: x['score'])['label']

                esg_score = calculate_investment_score(esg_label, esg_category, esg_sentiment, esg_fls)

                # 결과 저장
                save_esg_result(article['news_id'], article['original_title'], esg_label, esg_score, company_code)

                results.append({
                    "기사 ID": article['news_id'],
                    "기사 한글명": article['original_title'],
                    "기사 ESG 분야": esg_label,
                    "기사 ESG 점수": esg_score,
                    "기업 코드": company_code
                })
            except ValueError as ve:
                logger.error(f"ValueError: {ve}")
                continue
            except Exception as exc:
                logger.error(f"Exception: {exc}")
                raise HTTPException(status_code=500, detail=str(exc))

    return results

# 분석 완료된 ESG 결과 불러오기
@app.post('/esg_results')
async def get_esg_results(request: ESGRequest):
    company_name = request.company_name

    company_code = get_company_code(company_name)
    if not company_code:
        logger.warning(f"Company code not found for company name {company_name}")
        raise HTTPException(status_code=404, detail="Company code not found for the given company name.")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM esg_result WHERE stock_code = %s"
        cursor.execute(query, (company_code,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"Fetched {len(results)} esg results for company code {company_code}")
        if not results:
            raise HTTPException(status_code=404, detail="No ESG results found for the given company code.")

        formatted_results = [{
            "기사 ID": result["news_id"],
            "기사 한글명": result["article_title"],
            "기사 ESG 분야": result["esg_label"],
            "기사 ESG 점수": result["esg_score"],
            "기업 코드": result["stock_code"]
        } for result in results]

        return formatted_results
    except mysql.connector.Error as e:
        logger.error(f"Error fetching ESG results: {e}")
        raise HTTPException(status_code=500, detail="Error fetching ESG results")

def get_company_code(company_name):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT stock_code FROM stock_info WHERE stock_name = %s"
        cursor.execute(query, (company_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            logger.info(f"Found stock code {result['stock_code']} for company name {company_name}")
        else:
            logger.warning(f"No stock code found for company name {company_name}")
        return result['stock_code'] if result else None
    except mysql.connector.Error as e:
        logger.error(f"Error fetching company code: {e}")
        raise HTTPException(status_code=500, detail="Error fetching company code")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5002)
