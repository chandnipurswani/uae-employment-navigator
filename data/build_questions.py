"""Source of truth for the 40-question test set -> writes data/questions.jsonl.

Every item starts with status="draft". `python -m navigator.verify_gold` promotes items to
"auto_verified" when each key fact is found in the cited article of the official text;
a human read-through then sets "verified" (see docs/RUNBOOK.md).

key_facts: list of alternatives-groups. Each group is "a|b|c" = any one of these must appear.
"""
import json
from pathlib import Path

Q = []


def q(id, lang, kind, juris, question, gold, cites, facts, dialect=False, note=""):
    Q.append(dict(id=id, lang=lang, dialect=dialect, type=kind, jurisdiction=juris,
                  question=question, gold_answer=gold, gold_citations=cites,
                  key_facts=facts, status="draft", note=note))


# ------------------------------------------------------------------ English (20)
q("E01", "en", "factual", "mainland",
  "I've worked for my company in Dubai for just over a year. How many days of annual leave am I entitled to?",
  "At least 30 days of paid annual leave for each year of service.",
  ["UAE-LL Art 29"], ["30"])
q("E02", "en", "factual", "mainland",
  "I joined my employer 8 months ago. Am I entitled to any annual leave yet?",
  "Yes. Between six months and one year of service, you earn 2 days of leave for each month worked.",
  ["UAE-LL Art 29"], ["2|two"])
q("E03", "en", "factual", "mainland",
  "What is the longest probation period my employer can put me on?",
  "Up to 6 months from the start of work. You can only be put on probation once with the same employer.",
  ["UAE-LL Art 9"], ["6|six"])
q("E04", "en", "factual", "mainland",
  "Can my employer end my contract while I'm still on probation? How much notice do they have to give me?",
  "Yes. The employer can terminate during probation but must give written notice at least 14 days before the termination date.",
  ["UAE-LL Art 9"], ["14|fourteen"])
q("E05", "en", "factual", "mainland",
  "How is end-of-service gratuity calculated for a mainland private-sector employee?",
  "Based on basic wage: 21 days' wage for each of the first five years, and 30 days' wage for each additional year. Partial years count pro rata after one year of service. Total gratuity cannot exceed two years' wage.",
  ["UAE-LL Art 51"], ["21", "30"])
q("E06", "en", "factual", "mainland",
  "How much paid sick leave do I get after my probation ends?",
  "Up to 90 days a year: the first 15 days on full pay, the next 30 on half pay, and the rest unpaid.",
  ["UAE-LL Art 31"], ["15|fifteen", "30|thirty"])
q("E07", "en", "factual", "mainland",
  "How long is maternity leave under the UAE Labour Law, and is it paid?",
  "60 days in total: 45 days on full pay and 15 days on half pay.",
  ["UAE-LL Art 30"], ["45", "15"])
q("E08", "en", "factual", "mainland",
  "My wife just had a baby. How many days of parental leave can I take, and by when?",
  "5 working days of paid parental leave, taken within 6 months of the child's birth.",
  ["UAE-LL Art 32"], ["5|five", "6|six"])
q("E09", "en", "factual", "mainland",
  "If I work overtime, how much extra should I be paid?",
  "Normal hourly wage plus at least 25%. Overtime between 10 pm and 4 am is paid at least 50% extra.",
  ["UAE-LL Art 19"], ["25"])
q("E10", "en", "factual", "mainland",
  "My contract just ended. How long does my employer have to pay my final dues?",
  "Within 14 days of the end of the contract.",
  ["UAE-LL Art 53"], ["14|fourteen"])
q("E11", "en", "factual", "mainland",
  "My recruiter wants me to pay a fee to get the job. Is that allowed?",
  "No. Employers (and those recruiting for them) may not charge workers recruitment or employment fees or costs, directly or indirectly.",
  ["UAE-LL Art 6"], [])
q("E12", "en", "factual", "mainland",
  "My contract has a non-compete clause. How long can it last after I leave?",
  "At most 2 years after the contract ends. It must also be limited in place and type of work.",
  ["UAE-LL Art 10"], ["2|two"])
q("E13", "en", "factual", "adgm",
  "I work for a company registered in ADGM. How much annual leave do I get?",
  "20 working days of paid vacation leave per year (excluding public holidays). It accrues monthly in the first year.",
  ["ADGM-ER s 21"], ["20|twenty"])
q("E14", "en", "factual", "adgm",
  "What are the sick leave rules for ADGM employees?",
  "Up to 60 working days in any 12-month period: the first 10 working days on full pay, the next 20 on half pay, the remaining 30 unpaid.",
  ["ADGM-ER s 29", "ADGM-ER s 30"], ["60|sixty", "10|ten"])
q("E15", "en", "factual", "adgm",
  "I'm about to become a father and my employer is in ADGM. Do I get paternity leave?",
  "Yes. 5 working days of paid paternity leave, taken within 2 months of the birth (or adoption of a child under 5).",
  ["ADGM-ER s 34"], ["5|five"])
q("E16", "en", "comparison", "both",
  "Do I get more annual leave on the mainland or at an ADGM company?",
  "Mainland Labour Law: 30 days per year of service. ADGM: 20 working days. 20 working days is about 4 weeks, so the mainland figure is higher on paper, but the units differ (calendar days vs working days).",
  ["UAE-LL Art 29", "ADGM-ER s 21"], ["30", "20"])
q("E17", "en", "comparison", "both",
  "Compare maternity leave on the mainland versus in ADGM.",
  "Mainland: 60 days (45 full pay + 15 half pay). ADGM: 65 working days (33 full pay + 32 half pay), with 12 months' continuous service required.",
  ["UAE-LL Art 30", "ADGM-ER s 32"], ["60", "65"])
q("E18", "en", "comparison", "both",
  "If my employer lets me go during probation, how much notice do I get on the mainland vs in ADGM?",
  "Mainland: at least 14 days' written notice. ADGM: either party can end employment during probation on 1 week's notice.",
  ["UAE-LL Art 9", "ADGM-ER s 8"], ["14|fourteen", "7|week|seven"])
q("E19", "en", "unanswerable", "none",
  "How many days of annual leave does a DIFC employee get?",
  "The provided documents cover the UAE Labour Law and ADGM, not the DIFC Employment Law. The assistant should say so and point to the DIFC Employment Law / DIFC authorities.",
  [], [], note="DIFC not in corpus")
q("E20", "en", "unanswerable", "none",
  "What salary do I need to qualify for a UAE Golden Visa?",
  "Not covered by these employment documents. The assistant should decline and point to ICP / GDRFA official sources.",
  [], [], note="residency law not in corpus")

# ------------------------------------------------------------------ Arabic (20)
q("A01", "ar", "factual", "mainland",
  "كم عدد أيام الإجازة السنوية التي يستحقها العامل بعد إكمال سنة في القطاع الخاص؟",
  "يستحق العامل إجازة سنوية مدفوعة الأجر لا تقل عن 30 يوماً عن كل سنة خدمة.",
  ["UAE-LL Art 29"], ["30|ثلاثين|ثلاثون"])
q("A02", "ar", "factual", "mainland",
  "ما هي المدة القصوى لفترة التجربة؟",
  "لا تزيد فترة التجربة على 6 أشهر من تاريخ مباشرة العمل، ولا يجوز وضع العامل تحت التجربة أكثر من مرة لدى صاحب العمل نفسه.",
  ["UAE-LL Art 9"], ["6|ستة|ست"])
q("A03", "ar", "factual", "mainland",
  "كيف تُحسب مكافأة نهاية الخدمة للعامل في القطاع الخاص؟",
  "على أساس الأجر الأساسي: أجر 21 يوماً عن كل سنة من السنوات الخمس الأولى، وأجر 30 يوماً عن كل سنة تزيد على ذلك، وبما لا يتجاوز مجموع المكافأة أجر سنتين.",
  ["UAE-LL Art 51"], ["21|واحد وعشرين", "30|ثلاثين"])
q("A04", "ar", "factual", "mainland",
  "ما هي مدة الإجازة المرضية وكيف تُدفع بعد انتهاء فترة التجربة؟",
  "حتى 90 يوماً في السنة: أول 15 يوماً بأجر كامل، ثم 30 يوماً بنصف أجر، وما يليها بدون أجر.",
  ["UAE-LL Art 31"], ["15|خمسة عشر", "30|ثلاثين"])
q("A05", "ar", "factual", "mainland",
  "كم مدة إجازة الوضع للعاملة؟",
  "60 يوماً: 45 يوماً بأجر كامل و15 يوماً بنصف أجر.",
  ["UAE-LL Art 30"], ["60|ستين|ستون", "45|خمسة وأربعين"])
q("A06", "ar", "factual", "mainland",
  "ما الحد الأقصى لساعات العمل العادية؟",
  "8 ساعات في اليوم أو 48 ساعة في الأسبوع.",
  ["UAE-LL Art 17"], ["8|ثماني|ثمان", "48"])
q("A07", "ar", "factual", "mainland",
  "ما أقصى مدة يجوز أن يمتد إليها شرط عدم المنافسة بعد انتهاء العقد؟",
  "لا تزيد على سنتين من تاريخ انتهاء العقد، ويجب أن يكون محدداً من حيث المكان ونوع العمل.",
  ["UAE-LL Art 10"], ["2|سنتين|سنتان"])
q("A08", "ar", "factual", "mainland",
  "كم يوماً إجازة حداد يستحق العامل عند وفاة زوجته؟",
  "5 أيام في حالة وفاة الزوج أو الزوجة.",
  ["UAE-LL Art 32"], ["5|خمسة|خمس"])
q("A09", "ar", "factual", "mainland",
  "مرحبا، توني رزقت بولد والحمدلله، كم يوم إجازة يعطوني الشركة؟",
  "تستحق إجازة والدية مدفوعة الأجر مدتها 5 أيام عمل، تؤخذ خلال 6 أشهر من تاريخ ولادة الطفل.",
  ["UAE-LL Art 32"], ["5|خمسة|خمس"], dialect=True)
q("A10", "ar", "factual", "mainland",
  "لو اشتغلت بعد الساعة عشر بالليل، كم الزيادة اللي لي على الأجر؟",
  "العمل الإضافي بين الساعة 10 مساءً و4 صباحاً يُدفع بزيادة لا تقل عن 50% من الأجر.",
  ["UAE-LL Art 19"], ["50|خمسين"], dialect=True)
q("A11", "ar", "factual", "mainland",
  "خلص عقدي مع الشركة، متى لازم يعطوني مستحقاتي؟",
  "خلال 14 يوماً من تاريخ انتهاء العقد.",
  ["UAE-LL Art 53"], ["14|أربعة عشر|اربعة عشر"], dialect=True)
q("A12", "ar", "factual", "adgm",
  "أنا أشتغل في شركة في سوق أبوظبي العالمي، في رمضان كم تنقص ساعات الدوام؟",
  "تُخفَّض ساعات العمل اليومية العادية للموظفين المسلمين بنسبة 25% خلال رمضان دون خصم من الأجر.",
  ["ADGM-ER s 17"], ["25|ربع"], dialect=True)
q("A13", "ar", "factual", "adgm",
  "كيف تُحسب مكافأة نهاية الخدمة لموظف في سوق أبوظبي العالمي؟",
  "بعد سنة من الخدمة المستمرة: أجر أساسي 21 يوماً عن كل سنة من السنوات الخمس الأولى، و30 يوماً عن كل سنة إضافية، مع استثناءات لمن هم مشمولون بأنظمة التقاعد.",
  ["ADGM-ER s 61"], ["21", "30"])
q("A14", "ar", "factual", "adgm",
  "إذا أردت الاستقالة من شركة في سوق أبوظبي العالمي بعد سنة من العمل، ما مدة الإشعار المطلوبة؟",
  "30 يوماً تقويمياً كحد أدنى عند الخدمة لثلاثة أشهر فأكثر، ما لم ينص العقد على مدة أطول.",
  ["ADGM-ER s 56"], ["30|ثلاثين"])
q("A15", "ar", "comparison", "both",
  "قارن بين الإجازة المرضية في قانون العمل الاتحادي وفي سوق أبوظبي العالمي.",
  "الاتحادي: حتى 90 يوماً سنوياً (15 بأجر كامل، 30 بنصف أجر، الباقي بدون أجر). سوق أبوظبي العالمي: حتى 60 يوم عمل خلال 12 شهراً (10 بأجر كامل، 20 بنصف أجر، 30 بدون أجر).",
  ["UAE-LL Art 31", "ADGM-ER s 29", "ADGM-ER s 30"], ["90|تسعين", "60|ستين"])
q("A16", "ar", "comparison", "both",
  "ما الفرق في إجازة الأبوة بين البر الرئيسي وسوق أبوظبي العالمي؟",
  "كلاهما 5 أيام عمل مدفوعة. في البر الرئيسي تؤخذ خلال 6 أشهر من الولادة، وفي سوق أبوظبي العالمي خلال شهرين.",
  ["UAE-LL Art 32", "ADGM-ER s 34"], ["5|خمسة|خمس"])
q("A17", "ar", "comparison", "both",
  "شو الفرق في الإجازة السنوية بين الشركات في البر الرئيسي والشركات في سوق أبوظبي العالمي؟",
  "البر الرئيسي: 30 يوماً عن كل سنة خدمة. سوق أبوظبي العالمي: 20 يوم عمل في السنة.",
  ["UAE-LL Art 29", "ADGM-ER s 21"], ["30|ثلاثين", "20|عشرين"], dialect=True)
q("A18", "ar", "unanswerable", "none",
  "ما هي نسبة التوطين المطلوبة من الشركات الخاصة في عام 2027؟",
  "الوثائق المتاحة لا تحدد نسبة التوطين لسنة بعينها. يجب أن يوضح المساعد ذلك ويحيل إلى وزارة الموارد البشرية والتوطين.",
  [], [], note="targets set by Cabinet decisions not in corpus")
q("A19", "ar", "unanswerable", "none",
  "كم نسبة اشتراك المعاشات التي تُخصم من راتب الموظف المواطن؟",
  "غير مذكورة في هذه الوثائق (تنظمها قوانين المعاشات والتأمينات الاجتماعية). يجب الاعتذار والإحالة إلى الهيئة العامة للمعاشات والتأمينات الاجتماعية.",
  [], [], note="pension law not in corpus")
q("A20", "ar", "unanswerable", "none",
  "كم لازم يكون راتبي عشان آخذ الإقامة الذهبية؟",
  "غير مذكور في وثائق قانون العمل. يجب الاعتذار والإحالة إلى الهيئة الاتحادية للهوية والجنسية.",
  [], [], dialect=True, note="residency law not in corpus")

if __name__ == "__main__":
    assert len(Q) == 40 and len({x["id"] for x in Q}) == 40
    out = Path(__file__).parent / "questions.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for x in Q:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    from collections import Counter
    print(len(Q), "questions ->", out)
    print(Counter((x["lang"], x["type"]) for x in Q), "dialect:", sum(x["dialect"] for x in Q))
