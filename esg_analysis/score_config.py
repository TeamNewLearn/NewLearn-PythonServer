# ESG 분석 점수 기준

# ESG 레이블에 따른 기본 점수
ESG_LABEL_SCORES = {
    'Environmental': 50,
    'Social': 50,
    'Governance': 50
}

# 카테고리에 따른 점수
CATEGORY_SCORES = {
    # Environmental
    'Climate Change': 30,
    'Natural Capital': 25,
    'Pollution & Waste': 20,
    # Social
    'Human Capital': 20,
    'Product Liability': 15,
    'Community Relations': 15,
    # Governance
    'Corporate Governance': 30,
    'Business Ethics & Values': 25,
    # Non-ESG
    'Non-ESG': 0
}


# 감정에 따른 점수
SENTIMENT_SCORES = {
    'Positive': 30,
    'Neutral': 10,
    'Negative': -20
}

# FLS에 따른 점수
FLS_SCORES = {
    'Specific-FLS': 40,
    'Non-specific FLS': 20,
    'Not-FLS': 0
}

# ESG 분류 모델과 카테고리 분류 모델 일치할 경우 추가 점수
CATEGORY_MATCH_BONUS = 10
