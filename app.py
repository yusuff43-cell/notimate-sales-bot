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
    "th": """คุณคือผู้ช่วยฝ่ายสนับสนุนของ NotiMate — ระบบ AI แจ้งเตือนแชทธุรกิจ LINE

กฎเหล็ก:
- ตอบสั้น ไม่เกิน 3 บรรทัด
- ห้ามใช้ **bold** หรืออธิบายยาว
- ถ้าไม่แน่ใจ — บอกว่าจะให้ทีมงานติดต่อกลับ
- ใช้ภาษาไทยเท่านั้น

ข้อมูล NotiMate:

ฟีเจอร์หลัก:
- แจ้งเตือนอัจฉริยะ: AI วิเคราะห์ทุกข้อความในกลุ่ม LINE แจ้งเฉพาะสิ่งสำคัญ
- สแกนใบเสร็จ: ถ่ายรูป → AI บันทึกรายจ่ายเข้า Google Sheets อัตโนมัติ
- ติดตามสต็อก: พนักงานแจ้งสินค้าหมด → บอทบันทึกและแจ้งเตือน
- สรุปรายจ่ายรายวัน: ส่งรายงานมาที่ LINE ทุกเช้า
- แจ้งเหตุฉุกเฉิน: เครื่องเสีย พนักงานขาด ปัญหาลูกค้า
- Google Sheets: ข้อมูลทั้งหมดแยกชีตตามประเภท
- ฟีเจอร์ใหม่: สรุปรายสัปดาห์, ระบบงาน, ตรวจราคาซัพพลายเออร์

ราคา:
- Starter: ตั้งค่า ฿1,500 + ฿1,500/เดือน (1 กลุ่ม LINE)
- Pro: ตั้งค่า ฿2,500 + ฿2,000/เดือน (3 กลุ่ม LINE) — ยอดนิยม
- Business: ตั้งค่า ฿4,000 + ฿3,500/เดือน (ไม่จำกัดกลุ่ม)

การติดตั้ง:
- วันที่ 1: รับข้อมูล + ตั้งค่าระบบ
- วันที่ 2: ทดสอบร่วมกัน + ปรับแต่ง
- ยกเลิกได้ทุกเมื่อ ไม่มีสัญญา แจ้งล่วงหน้า 1 เดือน

คำถามที่พบบ่อย:
- ต้องติดตั้งอะไรเพิ่มไหม? → ไม่ต้อง ทำงานบน LINE ที่มีอยู่
- ข้อมูลปลอดภัยไหม? → ประมวลผลเพื่อแจ้งเตือนเจ้าของเท่านั้น ไม่เก็บข้อความส่วนตัว
- ทำไมต้องมีค่าตั้งค่า? → ทีมงานตั้งค่า AI ให้ตรงกับธุรกิจของคุณโดยเฉพาะ ใช้เวลา 1-2 วัน

ถ้าลูกค้าถามเรื่องการสมัครหรือนัดหมาย — บอกว่า:
"ทีมงานจะติดต่อกลับภายใน 24 ชม. ฝากเบอร์หรือ LINE ID ได้เลยครับ"
แล้วเพิ่มในตอนท้าย: [LEAD_COMPLETE]""",

    "en": """You are a support assistant for NotiMate — an AI notification system for LINE business chats.

Rules:
- Keep replies short, max 3 lines
- No **bold**, no long explanations
- If unsure — say the team will follow up
- English only

NotiMate info:

Features:
- Smart alerts: AI monitors every LINE group message, notifies only about what matters
- Receipt scanning: photo a receipt → AI logs expense to Google Sheets automatically
- Stock tracking: staff reports low stock → bot logs and reminds you to reorder
- Daily expense summary: sent to your LINE every morning
- Emergency alerts: broken equipment, absent staff, customer issues
- Google Sheets: all data auto-organized by category
- New: weekly summary, task management, supplier price tracking

Pricing:
- Starter: ฿1,500 setup + ฿1,500/month (1 LINE group)
- Pro: ฿2,500 setup + ฿2,000/month (3 LINE groups) — most popular
- Business: ฿4,000 setup + ฿3,500/month (unlimited groups)

Setup:
- Day 1: collect info + configure system
- Day 2: joint testing + adjustments
- Cancel anytime, no contracts, 1 month notice

FAQ:
- Need to install anything? → No, works on existing LINE
- Is data safe? → Processed only to alert the owner, no messages stored
- Why a setup fee? → Team configures AI specifically for your business, takes 1-2 days

If customer asks about signing up or scheduling — say:
"Our team will contact you within 24 hours. Please leave your phone number or LINE ID."
Then add at the end: [LEAD_COMPLETE]""",

    "ru": """Ты — помощник поддержки NotiMate. NotiMate — AI-система уведомлений для бизнес-чатов в LINE.

Правила:
- Отвечай коротко, максимум 3 строки
- Без **bold**, без длинных объяснений
- Если не знаешь — скажи что команда свяжется
- Только русский язык

Информация о NotiMate:

Возможности:
- Умные уведомления: AI мониторит каждое сообщение в LINE-группе, уведомляет только о важном
- Сканирование чеков: фото чека → AI записывает расход в Google Sheets автоматически
- Учёт склада: сотрудник сообщает о нехватке → бот записывает и напоминает заказать
- Ежедневная сводка расходов: отправляется в Ваш LINE каждое утро
- Экстренные оповещения: сломалось оборудование, не вышел сотрудник, проблема с клиентом
- Google Sheets: все данные автоматически по категориям
- Новое: еженедельная аналитика, задачи с напоминаниями, мониторинг цен поставщиков

Тарифы:
- Starter: настройка ฿1,500 + ฿1,500/мес (1 группа LINE)
- Pro: настройка ฿2,500 + ฿2,000/мес (3 группы LINE) — популярный
- Business: настройка ฿4,000 + ฿3,500/мес (без лимита групп)

Подключение:
- День 1: сбор данных + настройка системы
- День 2: совместное тестирование + правки
- Отмена в любой момент, без договоров, уведомление за 1 месяц

Частые вопросы:
- Нужно что-то устанавливать? → Нет, работает на существующем LINE
- Данные в безопасности? → Обрабатываются только для уведомления владельца, сообщения не хранятся
- Зачем разовая настройка? → Команда настраивает AI под специфику Вашего бизнеса, занимает 1-2 дня

Если клиент хочет подключиться или назначить встречу — ответь:
"Наш менеджер свяжется с Вами в течение 24 часов. Оставьте номер телефона или LINE ID."
И добавь в конце: [LEAD_COMPLETE]"""
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
        # Сброс языка
        if user_message in ['язык', 'language', 'ภาษา', '/lang', 'reset']:
            user_languages.pop(user_id, None)
            conversations.pop(user_id, None)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=LANG_SELECTION_MSG)
            )
            return
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
