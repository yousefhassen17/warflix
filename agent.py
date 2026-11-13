import os
import json
import feedparser
from datetime import datetime
from google import genai
from google.genai import types

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/arabic/rss.xml",
    "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9"
]

def fetch_latest_news():
    news_items = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            news_items.append(f"- {entry.title}: {entry.get('summary', '')}")
    return "\n".join(news_items)

def get_working_model(client):
    # قائمة بأحدث موديلات جوجل بالترتيب + سحب تلقائي من حسابك
    preferred = [
        "gemini-3-flash-preview",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    try:
        available = [m.name.replace("models/", "") for m in client.models.list() if "gemini" in m.name]
        print("Available models for your key:", available)
        for p in preferred:
            if p in available:
                return p
        # اختيار أول موديل فلاش متاح في حسابك تلقائياً
        for m in available:
            if "flash" in m and "vision" not in m:
                return m
        if available:
            return available[0]
    except Exception as e:
        print("Model list notice:", e)
    return "gemini-2.0-flash"

def update_encyclopedia():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)
    model_name = get_working_model(client)
    print(f"Using auto-selected model: {model_name}")

    latest_news = fetch_latest_news()

    db_file = "updates.json"
    if os.path.exists(db_file):
        with open(db_file, "r", encoding="utf-8") as f:
            current_data = json.load(f)
    else:
        current_data = {"last_updated": "", "live_briefings": []}

    prompt = f"""
    أنت كبير المحللين العسكريين والاستراتيجيين في منصة WARFLIX.
    هذه أحدث الأخبار المسحوبة اليوم من الوكالات العالمية:
    {latest_news}

    المطلوب منك:
    1. فلترة الأخبار واختيار أهم 3 تطورات عسكرية أو جيوسياسية تخص الصراعات والحروب الحالية فقط.
    2. صياغة كل تطور في شكل "فصل تحليلي استراتيجي معمق" باللغة العربية الفصحى المبسطة (يشرح: الحدث، التكتيك العسكري، والأثر الجيوسياسي).
    3. أخرج النتيجة بصيغة JSON فقط تحتوي على قائمة اسمها new_chapters، كل عنصر فيها يحتوي على:
       - conflict_name (اسم الحرب أو الإقليم)
       - chapter_title (عنوان الفصل الاستراتيجي)
       - reading_time (وقت القراءة المقدر)
       - summary (ملخص في سطرين)
       - full_html_analysis (التحليل المفصل مقسماً بعناوين <h4> وفقرات <p> ونقاط <ul>)
    """

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3
        )
    )

    result = json.loads(response.text)
    today_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    for ch in result.get("new_chapters", []):
        ch["date"] = today_str
        current_data["live_briefings"].insert(0, ch)

    current_data["live_briefings"] = current_data["live_briefings"][:30]
    current_data["last_updated"] = today_str

    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update_encyclopedia()
