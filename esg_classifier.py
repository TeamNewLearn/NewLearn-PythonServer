from transformers import BertTokenizer, BertForSequenceClassification, pipeline
import score_config
from article_translation import fetch_translated_text


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
    return results


def esg_category_model(nlp_pipeline, article_content):
    results = nlp_pipeline(article_content)
    category = max(results, key=lambda x: x['score'])
    return category['label'], category['score']


def esg_sentiment_model(nlp_pipeline, article_content):
    results = nlp_pipeline(article_content)
    sentiment = max(results, key=lambda x: x['score'])
    return sentiment['label'], sentiment['score']


def esg_fls_model(nlp_pipeline, article_content):
    results = nlp_pipeline(article_content)
    fls = max(results, key=lambda x: x['score'])
    return fls['label'], fls['score']


def get_esg_label(results):
    label = max(results, key=lambda x: x['score'])['label']
    return label


# 3. 분석 결과 처리 함수
def calculate_investment_score(esg_label, esg_category, esg_sentiment, esg_fls):
    score = 0

    # ESG 레이블에 따른 기본 점수
    score += score_config.ESG_LABEL_SCORES.get(esg_label, 0)

    # 카테고리에 따른 점수
    score += score_config.CATEGORY_SCORES.get(esg_category, 0)

    # 감정에 따른 점수
    score += score_config.SENTIMENT_SCORES.get(esg_sentiment, 0)

    # FLS에 따른 점수
    score += score_config.FLS_SCORES.get(esg_fls, 0)

    return score


# 4. 전체 프로세스 실행 함수
def process_article(api_url, api_key, article_id):
    # 번역된 텍스트를 API에서 가져오기
    article_content = fetch_translated_text(api_url, api_key, article_id)

    # 모델 로딩 및 파이프라인 설정
    esg_nlp, category_nlp, sentiment_nlp, fls_nlp = load_models()

    # 번역된 텍스트를 ESG 분석 모델에 적용
    results = classify_esg_article(esg_nlp, article_content)
    esg_label = get_esg_label(results)

    if esg_label == 'None':
        return {"result": "Non-ESG"}

    esg_category, category_score = esg_category_model(category_nlp, article_content)
    esg_sentiment, sentiment_score = esg_sentiment_model(sentiment_nlp, article_content)
    esg_fls, fls_score = esg_fls_model(fls_nlp, article_content)

    investment_score = calculate_investment_score(esg_label, esg_category, esg_sentiment, esg_fls)

    return {
        "result": "ESG",
        "label": esg_label,
        "category": esg_category,
        "category_score": category_score,
        "sentiment": esg_sentiment,
        "sentiment_score": sentiment_score,
        "fls": esg_fls,
        "fls_score": fls_score,
        "investment_score": investment_score
    }
