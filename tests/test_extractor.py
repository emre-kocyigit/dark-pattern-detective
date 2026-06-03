from agent.tools.extractor import extract, ExtractionResult

SAMPLE_EN = """
Only 2 items left! Offer ends in 10 minutes.
Subscribe now and get a free trial. Auto-renews monthly.
Accept all cookies or manage preferences.
Cancel anytime. Hurry, selling fast!
"""

SAMPLE_TR = """
Sadece 2 ürün kaldı! Kampanya bitiyor.
Şimdi abone ol, ücretsiz deneme kazan. Otomatik yenileme.
Tümünü kabul et veya tercihleri yönet.
"""

SAMPLE_EMPTY = "Welcome to our website. Browse our products."


def test_extract_returns_model():
    result = extract(SAMPLE_EN)
    assert isinstance(result, ExtractionResult)


def test_extract_method_set():
    result = extract(SAMPLE_EN)
    assert result.extraction_method in ["llm", "fallback", "hybrid"]


def test_extract_english_urgency():
    result = extract(SAMPLE_EN)
    assert len(result.urgency_texts) > 0


def test_extract_turkish_urgency():
    result = extract(SAMPLE_TR)
    assert len(result.urgency_texts) > 0


def test_extract_empty_text():
    result = extract(SAMPLE_EMPTY)
    assert isinstance(result, ExtractionResult)
    assert result.extraction_method in ["llm", "fallback", "hybrid"]


def test_extract_consent_detected():
    result = extract(SAMPLE_EN)
    assert len(result.consent_accept) > 0