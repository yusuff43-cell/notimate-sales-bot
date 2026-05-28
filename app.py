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

SYSTEM_PROMPT = """คุณคือผู้ช่วยขายของ NotiMate ระบบ AI แจ้งเตือนแชทธุรกิจ LINE

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

ถ้าถามนอกเรื่อง — ตอบสั้นๆ แล้วกลับมาที่คำถามปัจจุบัน"""

def get_claude_response(user_id: str, user_message: str) -> str:
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
        system=SYSTEM_PROMPT,
        messages=history
    )

    reply = response.content[0].text

    conversations[user_id].append({
        "role": "assistant",
        "content": reply
    })

    return reply

def send_lead_notification(user_id: str):
    """Push уведомление владельцу когда лид готов"""
    history = conversations.get(user_id, [])
    
    # Собираем данные из диалога
    summary = "\n".join([
        f"{'Клиент' if m['role'] == 'user' else 'Бот'}: {m['content']}"
        for m in history[-8:]
    ])
    
    message = f"🔔 Новый лид NotiMate!\n\nДиалог:\n{summary}"
    
    try:
        line_bot_api.push_message(
            OWNER_ID,
            TextSendMessage(text=message)
        )
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
    user_message = event.message.text.strip()

    try:
        reply = get_claude_response(user_id, user_message)
        
        # Проверяем завершён ли лид
        if '[LEAD_COMPLETE]' in reply:
            clean_reply = reply.replace('[LEAD_COMPLETE]', '').strip()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=clean_reply)
            )
            send_lead_notification(user_id)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )
    except Exception as e:
        print(f"Error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ขออภัยครับ กรุณาลองใหม่")
        )

@app.route("/health", methods=['GET'])
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
