from transformers import BertTokenizer, BertForSequenceClassification, pipeline

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

    return esg_nlp, category_nlp, sentiment_nlp

# 2. ESG 관련 함수
def classify_esg_article(nlp_pipeline, article_text):
    results = nlp_pipeline(article_text)
    return results

def esg_category_model(nlp_pipeline, article_text):
    results = nlp_pipeline(article_text)
    category = max(results, key=lambda x: x['score'])
    return category['label'], category['score']

def esg_sentiment_model(nlp_pipeline, article_text):
    results = nlp_pipeline(article_text)
    sentiment = max(results, key=lambda x: x['score'])
    return sentiment['label'], sentiment['score']

def get_esg_label(results):
    label = max(results, key=lambda x: x['score'])['label']
    return label

# 3. 분석 결과 처리 함수
def calculate_investment_score(esg_label, esg_category, esg_sentiment):
    score = 0
    if esg_label in ['Environmental', 'Social', 'Governance']:
        score += 50  # 기본 점수
    if esg_category in ['Climate Change', 'Corporate Governance', 'Human Capital']:
        score += 20  # 중요 카테고리
    if esg_sentiment == 'Positive':
        score += 30  # 긍정적인 감정
    elif esg_sentiment == 'Neutral':
        score += 10  # 중립적인 감정
    elif esg_sentiment == 'Negative':
        score -= 20  # 부정적인 감정
    return score

# 4. 전체 프로세스 실행 함수
def process_article(article_text):
    esg_nlp, category_nlp, sentiment_nlp = load_models()

    results = classify_esg_article(esg_nlp, article_text)
    esg_label = get_esg_label(results)

    if esg_label == 'None':
        return {"result": "Non-ESG"}

    esg_category, category_score = esg_category_model(category_nlp, article_text)
    esg_sentiment, sentiment_score = esg_sentiment_model(sentiment_nlp, article_text)

    investment_score = calculate_investment_score(esg_label, esg_category, esg_sentiment)

    return {
        "result": "ESG",
        "label": esg_label,
        "category": esg_category,
        "category_score": category_score,
        "sentiment": esg_sentiment,
        "sentiment_score": sentiment_score,
        "investment_score": investment_score
    }

# 예시 기사 텍스트
article_text = "Rhonda has been volunteering for several years for a variety of charitable community programs."

# 기사 처리
result = process_article(article_text)
print(result)
