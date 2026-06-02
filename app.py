import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import anthropic

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
claude = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
OWNER_ID = os.environ['MY_LINE_USER_ID']

conversations = {}
user_languages = {}

LANG_SELECTION_MSG = """สวัสดีครับ! / Hello! / Привет!

เลือกภาษา / Choose language / Выберите язык:
1. 🇹🇭 ภาษาไทย
2. 🇬🇧 English
3. 🇷🇺 Русский"""

SYSTEM_PROMPTS = {
    "th": """คุณคือผู้ช่วยขายของ NotiMate ระบบ AI แจ้งเตือนแชทธุรกิจ LINE

กฎเหล็ก:
- ตอบสั้น กระชับ ไม่เกิน 3 บรรทัด
- ถามทีละคำถามเดียว พร้อมตัวเลือก
- ห้ามอธิบายยาว ห้ามใช้ **bold**
- ใช้ภาษาไทยเท่านั้น

ขั้นตอนการสนทนา (เรียงตามลำดับ):

ขั้น 1 — ถามประเภทธุรกิจ:
"ธุรกิจของคุณคือ?
1. ร้านกาแฟ/เบเกอรี่
2. ร้านอาหาร
3. ร้านค้า/บริการ
4. อื่นๆ"

ขั้น 2 — ถามจำนวน LINE กรุ๊ป:
"มี LINE กรุ๊ปพนักงานกี่กรุ๊ป?
1. 1 กรุ๊ป
2. 2-3 กรุ๊ป
3. มากกว่า 3 กรุ๊ป"

ขั้น 3 — ปิดการขาย:
"ขอบคุณครับ! ทีมงานจะติดต่อกลับภายใน 24 ชม.
กรุณาฝากเบอร์โทรหรือ LINE ID ไว้ได้เลยครับ"

เมื่อได้รับเบอร์หรือ LINE ID — ตอบว่า:
"ได้รับข้อมูลแล้วครับ ขอบคุณ! ทีมงานจะติดต่อเร็วๆ นี้ครับ 🙏"
แล้วเพิ่มข้อความพิเศษในตอนท้ายว่า: [LEAD_COMPLETE]

ถ้าถามนอกเรื่อง — ตอบสั้นๆ แล้วกลับมาที่คำถามปัจจุบัน""",

    "en": """You are a sales assistant for NotiMate — an AI notification system for LINE business chats.

Rules:
- Keep replies short, max 3 lines
- Ask one question at a time with numbered options
- No long explanations, no **bold**
- Use English only

Conversation flow (in order):

Step 1 — Ask business type:
"What type of business do you have?
1. Café / Bakery
2. Restaurant
3. Shop / Services
4. Other"

Step 2 — Ask number of LINE groups:
"How many employee LINE groups do you have?
1. 1 group
2. 2-3 groups
3. More than 3"

Step 3 — Close the sale:
"Thank you! Our team will contact you within 24 hours.
Please leave your phone number or LINE ID."

When contact info is received — reply:
"Got it, thank you! We'll be in touch soon 🙏"
Then add at the end: [LEAD_COMPLETE]

If asked off-topic — answer briefly and return to the current question.""",

    "ru": """Ты — менеджер по продажам NotiMate. NotiMate — AI-система уведомлений для бизнес-чатов в LINE.

Правила:
- Отвечай коротко, максимум 3 строки
- Задавай один вопрос за раз с вариантами ответа
- Без длинных объяснений, без **bold**
- Только русский язык

Этапы диалога (строго по порядку):

Этап 1 — Спроси тип бизнеса:
"Какой у вас бизнес?
1. Кофейня / Пекарня
2. Ресторан / Кафе
3. Магазин / Услуги
4. Другое"

Этап 2 — Спроси количество LINE-групп:
"Сколько рабочих LINE-групп у вас есть?
1. 1 группа
2. 2-3 группы
3. Больше 3"

Этап 3 — Закрывай сделку:
"Отлично! Наш менеджер свяжется с вами в течение 24 часов.
Оставьте номер телефона или LINE ID."

Когда получил контакт — ответь:
"Данные получены, спасибо! Скоро свяжемся 🙏"
И добавь в конце: [LEAD_COMPLETE]

Если вопрос не по теме — ответь коротко и вернись к текущему шагу."""
}

LANG_MAP = {
    "1": "th",
    "2": "en", 
    "3": "ru",
    "thai": "th", "ไทย": "th",
    "english": "en", "eng": "en",
    "русский": "ru", "ru": "ru", "рус": "ru"
}

BUSINESS_MAP = {
    "th": {"1": "ร้านกาแฟ/เบเกอรี่", "2": "ร้านอาหาร", "3": "ร้านค้า/บริการ", "4": "อื่นๆ"},
    "en": {"1": "Café/Bakery", "2": "Restaurant", "3": "Shop/Services", "4": "Other"},
    "ru": {"1": "Кофейня/Пекарня", "2": "Ресторан/Кафе", "3": "Магазин/Услуги", "4": "Другое"}
}

GROUPS_MAP = {
    "th": {"1": "1 กรุ๊ป", "2": "2-3 กรุ๊ป", "3": "3+ กรุ๊ป"},
    "en": {"1": "1 group", "2": "2-3 groups", "3": "3+ groups"},
    "ru": {"1": "1 группа", "2": "2-3 группы", "3": "3+ групп"}
}

def get_claude_response(user_id: str, user_message: str, lang: str) -> str:
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({
        "role": "user",
        "content": user_message
    })

    history = conversations[user_id][-10:]

    response = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system=SYSTEM_PROMPTS[lang],
        messages=history
    )

    reply = response.content[0].text

    conversations[user_id].append({
        "role": "assistant",
        "content": reply
    })

    return reply

def send_lead_notification(user_id: str, lang: str):
    history = conversations.get(user_id, [])
    messages = [m['content'] for m in history if m['role'] == 'user']

    # Первое сообщение — выбор языка, пропускаем
    business_raw = messages[1] if len(messages) > 1 else '—'
    groups_raw = messages[2] if len(messages) > 2 else '—'
    contact = messages[3] if len(messages) > 3 else '—'

    business = BUSINESS_MAP.get(lang, BUSINESS_MAP["th"]).get(business_raw, business_raw)
    groups = GROUPS_MAP.get(lang, GROUPS_MAP["th"]).get(groups_raw, groups_raw)

    lang_label = {"th": "🇹🇭 Thai", "en": "🇬🇧 English", "ru": "🇷🇺 Russian"}.get(lang, lang)

    message = (
        f"🔔 Новый лид NotiMate!\n\n"
        f"🌐 Язык: {lang_label}\n"
        f"🏪 Бизнес: {business}\n"
        f"💬 Групп: {groups}\n"
        f"📞 Контакт: {contact}"
    )

    try:
        line_bot_api.push_message(OWNER_ID, TextSendMessage(text=message))
    except Exception as e:
        print(f"Push error: {e}")

@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.source.type != 'user':
        return

    user_id = event.source.user_id
    user_message = event.message.text.strip().lower()

    try:
        # Шаг 0 — выбор языка
        if user_id not in user_languages:
            lang = LANG_MAP.get(user_message)
            if lang:
                user_languages[user_id] = lang
                # Запускаем первый вопрос через Claude
                reply = get_claude_response(user_id, "start", lang)
            else:
                # Показываем выбор языка
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=LANG_SELECTION_MSG)
                )
                return
        else:
            lang = user_languages[user_id]
            reply = get_claude_response(user_id, user_message, lang)

        # Проверяем завершён ли лид
        if '[LEAD_COMPLETE]' in reply:
            clean_reply = reply.replace('[LEAD_COMPLETE]', '').strip()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=clean_reply)
            )
            send_lead_notification(user_id, lang)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )

    except Exception as e:
        print(f"Error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Sorry / ขออภัย / Ошибка. Please try again.")
        )

@app.route("/health", methods=['GET'])
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
