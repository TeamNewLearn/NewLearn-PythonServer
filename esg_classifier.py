from transformers import BertTokenizer, BertForSequenceClassification, pipeline
import score_config

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

    fls_model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-fls', num_labels=3, ignore_mismatched_sizes=True)
    fls_tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-fls')
    fls_nlp = pipeline("text-classification", model=fls_model, tokenizer=fls_tokenizer)

    return esg_nlp, category_nlp, sentiment_nlp, fls_nlp

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

def esg_fls_model(nlp_pipeline, article_text):
    results = nlp_pipeline(article_text)
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
def process_article(article_text):
    esg_nlp, category_nlp, sentiment_nlp, fls_nlp = load_models()

    results = classify_esg_article(esg_nlp, article_text)
    esg_label = get_esg_label(results)

    if esg_label == 'None':
        return {"result": "Non-ESG"}

    esg_category, category_score = esg_category_model(category_nlp, article_text)
    esg_sentiment, sentiment_score = esg_sentiment_model(sentiment_nlp, article_text)
    esg_fls, fls_score = esg_fls_model(fls_nlp, article_text)

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

# 예시 기사 텍스트
article_text = "Climate change is one of the most pressing issues of our time, with far-reaching impacts on ecosystems, weather patterns, and human societies. The burning of fossil fuels, deforestation, and industrial activities have significantly increased the concentration of greenhouse gases in the atmosphere, leading to global warming. This warming has caused glaciers to melt, sea levels to rise, and extreme weather events to become more frequent and severe. To mitigate these effects, it is crucial to transition to renewable energy sources, implement sustainable agricultural practices, and protect natural habitats. Collective action from governments, businesses, and individuals is essential to address the challenges posed by climate change and ensure a sustainable future for generations to come."

# 기사 처리
result = process_article(article_text)
print(result)
