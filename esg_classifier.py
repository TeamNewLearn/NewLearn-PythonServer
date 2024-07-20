from transformers import BertTokenizer, BertForSequenceClassification, pipeline

# FinBERT 모델 로드
finbert = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-esg', num_labels=4)
tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-esg')
nlp = pipeline("text-classification", model=finbert, tokenizer=tokenizer)

# ESG 관련 기사 판별 함수
def classify_esg_article(article_text):
    results = nlp(article_text)
    return results

# 예시 기사 텍스트
article_text = "Rhonda has been volunteering for several years for a variety of charitable community programs."

# ESG 분류
results = classify_esg_article(article_text)
print(results)

# 결과 처리
def get_esg_label(results):
    label = results[0]['label']
    score = results[0]['score']
    if score < 0.5:
        return 'Non-ESG'
    return label

esg_label = get_esg_label(results)
print(f"ESG Label: {esg_label}")
