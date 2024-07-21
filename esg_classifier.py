from transformers import BertTokenizer, BertForSequenceClassification, pipeline

# 1. ESG 보고서 여부 모델 로드
esg_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-esg', num_labels=4)
esg_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-esg')
esg_nlp = pipeline("text-classification", model=esg_model, tokenizer=esg_tokenizer)

# 2. ESG 9 카테고리 모델 로드
category_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-esg-9-categories', num_labels=9)
category_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-esg-9-categories')
category_nlp = pipeline("text-classification", model=category_model, tokenizer=category_tokenizer)

# 3. ESG 긍/부정 모델 로드
sentiment_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-tone', num_labels=3)
sentiment_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-tone')
sentiment_nlp = pipeline("text-classification", model=sentiment_model, tokenizer=sentiment_tokenizer)

# ESG 관련 기사 판별 함수
def classify_esg_article(article_text):
    results = esg_nlp(article_text)
    return results

# ESG 카테고리 분석 함수
def esg_category_model(article_text):
    results = category_nlp(article_text)
    # 결과 중 가장 확률이 높은 카테고리 선택
    category = max(results, key=lambda x: x['score'])
    return category['label'], category['score']

# 긍/부정 분석 함수
def esg_sentiment_model(article_text):
    results = sentiment_nlp(article_text)
    # 결과 중 가장 확률이 높은 감정 분석
    sentiment = max(results, key=lambda x: x['score'])
    return sentiment['label'], sentiment['score']

# 결과 처리 함수
def get_esg_label(results):
    # ESG 모델 결과 중 가장 확률이 높은 라벨 선택
    label = max(results, key=lambda x: x['score'])['label']
    return label

# 가치투자 점수 계산 함수
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

# 전체 프로세스 실행 함수
def process_article(article_text):
    # 1. ESG 보고서에 해당하는지 분류
    results = classify_esg_article(article_text)
    esg_label = get_esg_label(results)

    if esg_label == 'None':
        print("This article is not related to ESG.")
        return {"result": "Non-ESG"}

    # 2. ESG 카테고리 모델
    esg_category, category_score = esg_category_model(article_text)

    # 3. ESG 긍/부정 모델
    esg_sentiment, sentiment_score = esg_sentiment_model(article_text)

    # 가치투자 점수 계산(고도화 필요)
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
