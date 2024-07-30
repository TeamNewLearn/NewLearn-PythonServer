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
        logger.error(f"모델 로딩 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="모델 로딩 중 오류 발생")

def get_news_articles(company_stock_code):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT news_id, translated_title, translated_body, original_title FROM news WHERE stock_code = %s"
        cursor.execute(query, (company_stock_code,))
        articles = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"기업 코드 {company_stock_code}에 대해 {len(articles)}개의 기사를 가져왔습니다.")
        return articles
    except mysql.connector.Error as e:
        logger.error(f"뉴스 기사 가져오기 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="뉴스 기사 가져오기 중 오류 발생")

def classify_article(nlp_pipeline, article_content):
    try:
        return nlp_pipeline(article_content)
    except Exception as e:
        logger.error(f"기사 분류 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="기사 분류 중 오류 발생")

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
        logger.warning("ESG 라벨이 None입니다. 결과를 저장하지 않습니다.")
        return  # esg_label이 None일 경우 저장하지 않음
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 중복 확인
        check_query = "SELECT COUNT(*) FROM esg_result WHERE news_id = %s"
        cursor.execute(check_query, (news_id,))
        count = cursor.fetchone()['COUNT(*)']

        if count > 0:
            logger.warning(f"뉴스 ID {news_id}에 대한 ESG 결과가 이미 존재합니다. 결과를 저장하지 않습니다.")
        else:
            query = """
                INSERT INTO esg_result (news_id, article_title, esg_label, esg_score, stock_code)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (news_id, article_title, esg_label, esg_score, stock_code))
            conn.commit()
            logger.info(f"뉴스 ID {news_id}에 대한 ESG 결과를 저장했습니다.")

        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
        logger.error(f"ESG 결과 저장 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="ESG 결과 저장 중 오류 발생")

class ESGRequest(BaseModel):
    company_stock_code: str

# 기업 기사 ESG 분석
@app.post('/esg_analysis')
async def esg_analysis(request: ESGRequest):
    company_stock_code = request.company_stock_code

    articles = get_news_articles(company_stock_code)

    if not articles:
        logger.warning(f"기업 코드 {company_stock_code}에 대한 기사를 찾을 수 없습니다.")
        raise HTTPException(status_code=404, detail=f"기업 코드 {company_stock_code}에 대한 기사를 찾을 수 없습니다.")

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
                    logger.warning(f"기사 {article['news_id']}에 대한 ESG 라벨이 None입니다.")
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
                save_esg_result(article['news_id'], article['original_title'], esg_label, esg_score, company_stock_code)

                results.append({
                    "기사 ID": article['news_id'],
                    "기사 한글명": article['original_title'],
                    "기사 ESG 분야": esg_label,
                    "기사 ESG 점수": esg_score,
                    "기업 코드": company_stock_code
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
    company_stock_code = request.company_stock_code

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM esg_result WHERE stock_code = %s"
        cursor.execute(query, (company_stock_code,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"기업 코드 {company_stock_code}에 대해 {len(results)}개의 ESG 결과를 가져왔습니다.")
        if not results:
            raise HTTPException(status_code=404, detail="기업 코드에 대한 ESG 결과를 찾을 수 없습니다.")

        formatted_results = [{
            "기사 ID": result["news_id"],
            "기사 한글명": result["article_title"],
            "기사 ESG 분야": result["esg_label"],
            "기사 ESG 점수": result["esg_score"],
            "기업 코드": result["stock_code"]
        } for result in results]

        return formatted_results
    except mysql.connector.Error as e:
        logger.error(f"ESG 결과 가져오기 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="ESG 결과 가져오기 중 오류 발생")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5002)
