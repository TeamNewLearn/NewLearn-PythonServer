from transformers import BertTokenizer, BertForSequenceClassification, pipeline
import score_config
from article_translation import fetch_article
import concurrent.futures

# 1. 모델 로딩 및 파이프라인 설정
def load_models():
    esg_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-esg', num_labels=4)
    esg_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-esg')
    esg_nlp = pipeline("text-classification", model=esg_model, tokenizer=esg_tokenizer)

    category_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-esg-9-categories', num_labels=9)
    category_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-esg-9-categories')
    category_nlp = pipeline("text-classification", model=category_model, tokenizer=category_tokenizer)

    sentiment_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-tone', num_labels=3)
    sentiment_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-tone')
    sentiment_nlp = pipeline("text-classification", model=sentiment_model, tokenizer=sentiment_tokenizer)

    fls_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-fls', num_labels=3,
                                                              ignore_mismatched_sizes=True)
    fls_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-fls')
    fls_nlp = pipeline("text-classification", model=fls_model, tokenizer=fls_tokenizer)

    return esg_nlp, category_nlp, sentiment_nlp, fls_nlp

# 2. ESG 관련 함수
def classify_esg_article(nlp_pipeline, article_content):
    results = nlp_pipeline(article_content)
    if not results:
        raise ValueError("Data is insufficient.")
    return results

def esg_category_model(nlp_pipeline, article_content):
    results = nlp_pipeline(article_content)
    if not results:
        raise ValueError("Data is insufficient.")

    best_result = max(results, key=lambda x: x['score'])
    return best_result['label'], best_result['score']

def esg_sentiment_model(nlp_pipeline, article_content):
    results = nlp_pipeline(article_content)
    if not results:
        raise ValueError("Data is insufficient.")

    best_result = max(results, key=lambda x: x['score'])
    return best_result['label'], best_result['score']

def esg_fls_model(nlp_pipeline, article_content):
    results = nlp_pipeline(article_content)
    if not results:
        raise ValueError("Data is insufficient.")

    best_result = max(results, key=lambda x: x['score'])
    return best_result['label'], best_result['score']

def get_esg_label(results):
    if not results:
        raise ValueError("Data is insufficient.")

    best_result = max(results, key=lambda x: x['score'])
    return best_result['label']

# 3. 분석 결과 처리 함수
def calculate_investment_score(esg_label, esg_category, esg_sentiment, esg_fls):
    score = 0

    # ESG 레이블에 따른 점수
    score += score_config.ESG_LABEL_SCORES.get(esg_label, 0)

    # 카테고리에 따른 점수
    score += score_config.CATEGORY_SCORES.get(esg_category, 0)

    # ESG 레이블과 카테고리 일치 시 추가 점수
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

    # 감정에 따른 점수
    score += score_config.SENTIMENT_SCORES.get(esg_sentiment, 0)

    # FLS에 따른 점수
    score += score_config.FLS_SCORES.get(esg_fls, 0)

    return score

# 4. 전체 프로세스 실행 함수
def process_article(api_url, api_key, article_id):
    try:
        article_content = fetch_article(api_url, article_id, api_key)
        if not article_content:
            raise ValueError("Data is insufficient.")
    except Exception as e:
        return {"result": str(e)}

    # 모델 로딩 및 파이프라인 설정
    esg_nlp, category_nlp, sentiment_nlp, fls_nlp = load_models()

    print("Loaded models successfully.")

    # 번역된 텍스트를 ESG 분석 모델에 적용
    try:
        results = classify_esg_article(esg_nlp, article_content['content'])
        print("ESG Classification Results:", results)
        esg_label = get_esg_label(results)
        print("ESG Label:", esg_label)
    except ValueError as e:
        return {"result": str(e)}

    # None 레이블이 반환될 경우 분석 중지
    if esg_label == 'None':
        return {"result": "Non-ESG"}

    # 병렬 처리
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(esg_category_model, category_nlp, article_content['content']): 'category',
            executor.submit(esg_sentiment_model, sentiment_nlp, article_content['content']): 'sentiment',
            executor.submit(esg_fls_model, fls_nlp, article_content['content']): 'fls'
        }
        try:
            results = {}
            for future in concurrent.futures.as_completed(futures):
                model_name = futures[future]
                results[model_name] = future.result()
            print("Parallel Model Results:", results)
        except ValueError as e:
            return {"result": str(e)}

    esg_category, category_score = results['category']
    esg_sentiment, sentiment_score = results['sentiment']
    esg_fls, fls_score = results['fls']

    investment_score = calculate_investment_score(esg_label, esg_category, esg_sentiment, esg_fls)

    return {
        "result": "ESG",
        "label": esg_label,
        "category": esg_category,
        "sentiment": esg_sentiment,
        "fls": esg_fls,
        "investment_score": investment_score
    }

# 테스트 실행
if __name__ == "__main__":
    api_url = "your_api_url"
    api_key = "your_api_key"
    article_id = "article_id"
    result = process_article(api_url, api_key, article_id)
    print(result)
