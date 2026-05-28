import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import anthropic

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
claude = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

# Хранение истории разговоров (в памяти, для MVP)
conversations = {}

SYSTEM_PROMPT = """คุณคือผู้จัดการฝ่ายขายของ NotiMate — ระบบ AI ที่ช่วยติดตามแชทธุรกิจ LINE 24/7

เป้าหมายของคุณ: เก็บข้อมูลจากลูกค้าที่สนใจ และอธิบายประโยชน์ของ NotiMate

ข้อมูลที่ต้องเก็บ (ทีละข้อ ไม่ถามพร้อมกันทั้งหมด):
1. ประเภทธุรกิจ (ร้านกาแฟ / ร้านอาหาร / ร้านค้า / อื่นๆ)
2. จำนวน LINE กรุ๊ปที่ใช้งาน
3. LINE User ID ของเจ้าของ (สำหรับรับการแจ้งเตือน)
4. ข้อความแบบไหนที่ถือว่า "สำคัญ" (เช่น คำสั่งซื้อ, ยอดเงิน, ปัญหาเร่งด่วน)

กฎ:
- ตอบเป็นภาษาไทยเท่านั้น
- สุภาพ กระชับ เป็นกันเอง
- ถามทีละคำถาม ไม่ถามรวม
- ถ้าลูกค้าถามเรื่องอื่นที่ไม่เกี่ยวกับ NotiMate — ตอบสั้นๆ แล้วนำกลับมาที่หัวข้อ
- เมื่อได้ข้อมูลครบแล้ว — สรุปและบอกว่าทีมจะติดต่อกลับภายใน 24 ชั่วโมง

NotiMate คืออะไร:
- AI บอทที่คอยมอนิเตอร์ LINE กรุ๊ปแทนเจ้าของธุรกิจ
- แจ้งเตือนเฉพาะข้อความสำคัญ ไม่ต้องอ่านทุกข้อความ
- เหมาะสำหรับธุรกิจขนาดเล็กที่มีหลายกรุ๊ป
- ราคาเริ่มต้น: ติดต่อสอบถาม (ยังไม่ระบุราคา)"""

def get_claude_response(user_id: str, user_message: str) -> str:
    """Получаем ответ от Claude с историей разговора"""
    
    if user_id not in conversations:
        conversations[user_id] = []
    
    conversations[user_id].append({
        "role": "user",
        "content": user_message
    })
    
    # Ограничиваем историю — последние 20 сообщений
    history = conversations[user_id][-20:]
    
    response = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=history
    )
    
    reply = response.content[0].text
    
    conversations[user_id].append({
        "role": "assistant",
        "content": reply
    })
    
    return reply

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
    # Пропускаем сообщения из групп — бот только для личных чатов
    if event.source.type != 'user':
        return
    
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    
    try:
        reply = get_claude_response(user_id, user_message)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
    except Exception as e:
        print(f"Error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ขออภัยครับ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง")
        )

@app.route("/health", methods=['GET'])
def health():
    return {"status": "ok", "bot": "NotiMate Sales Bot"}, 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
