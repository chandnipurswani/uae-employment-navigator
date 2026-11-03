from navigator.corpus import AR_ARTICLE, ADGM_SECTION, EN_ARTICLE, normalize, split_articles
from navigator.score import REFUSAL_RE, extract_citations, key_fact_score
from navigator.text import arabic_ratio, normalize_for_match

SRC = {"short": "UAE-LL", "unit": "Article"}


def test_split_english_articles_and_exec_reg_restart():
    text = ("Article (29)\nAnnual Leave\nThe worker is entitled to thirty days.\n"
            "Article (30)\nMaternity Leave\nSixty days of leave for the female worker.\n"
            "Article (74)\nPublication\nThis law shall be published in the gazette.\n"
            "Article (1)\nDefinitions\nExecutive regulation definitions go here.\n")
    chunks = split_articles(text, EN_ARTICLE, SRC)
    assert [(c["part"], c["number"]) for c in chunks] == [("law", 29), ("law", 30), ("law", 74), ("exec_reg", 1)]


def test_split_arabic_articles_with_flipped_brackets_and_arabic_digits():
    raw = "المادة )٢٩(\nالإجازة السنوية\nيستحق العامل إجازة سنوية مدتها ثلاثون يوماً.\nالمادة (30)\nإجازة الوضع\nتستحق العاملة إجازة وضع."
    chunks = split_articles(normalize(raw, "ar"), AR_ARTICLE, SRC)
    assert [c["number"] for c in chunks] == [29, 30]


def test_split_adgm_sections():
    text = "21. Vacation leave\n(1) An Employee is entitled to 20 working days.\n22. Carry forward\n(1) Up to 5 days may be carried."
    chunks = split_articles(text, ADGM_SECTION, {"short": "ADGM-ER", "unit": "Section"})
    assert [(c["number"], c["title"]) for c in chunks] == [(21, "Vacation leave"), (22, "Carry forward")]


def test_extract_citations_variants():
    a = "You get 30 days [UAE-LL Art 29]. In ADGM it's 20 working days [ADGM-ER s. 21; ADGM-ER s 22]."
    assert extract_citations(a) == ["UAE-LL Art 29", "ADGM-ER s 21", "ADGM-ER s 22"]


def test_key_facts_match_arabic_indic_digits():
    q = {"key_facts": ["30|ثلاثين"]}
    assert key_fact_score(q, "يستحق العامل ٣٠ يوماً") == 1.0
    assert key_fact_score({"key_facts": ["21", "30"]}, "21 days only") == 0.5


def test_arabic_ratio_ignores_citations():
    assert arabic_ratio("يستحق العامل إجازة [UAE-LL Art 29]") == 1.0
    assert arabic_ratio("You get thirty days") == 0.0


def test_refusal_detection_en_ar():
    assert REFUSAL_RE.search("These documents do not cover DIFC employment.")
    assert REFUSAL_RE.search("هذه الوثائق لا تتضمن معلومات عن الإقامة الذهبية")
    assert not REFUSAL_RE.search("You get 30 days of leave.")


def test_normalize_alef_and_taa_marbuta():
    assert normalize_for_match("إجازة") == normalize_for_match("اجازه")
