from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, ImageMessage,
                            TextSendMessage, ImageSendMessage)
import os
import Image

from src.chatgpt import ChatGPT, DALLE
from src.models import OpenAIModel
from src.memory import Memory
from src.logger import logger

load_dotenv('.env')

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

models = OpenAIModel(api_key=os.getenv('OPENAI_API'),
                     model_engine=os.getenv('OPENAI_MODEL_ENGINE'))

image_models = OpenAIModel(api_key=os.getenv('OPENAI_AP_1'),
                           model_engine=os.getenv('OPENAI_MODEL_ENGINE'))

memory = Memory(system_message=os.getenv('SYSTEM_MESSAGE'))
#print(os.getenv('SYSTEM_MESSAGE'))
chatgpt = ChatGPT(models, memory)

#Use chatgpt to genrate a detailed prompt for dalle first.
image_memory = Memory(system_message=os.getenv('SYSTEM_MESSAGE_1'))
image_chatgpt = ChatGPT(image_models, image_memory)
dalle = DALLE(image_models)

start_key_word = os.getenv('START_KEY_WORD')
start_key_word_1 = os.getenv('START_KEY_WORD_1')


@app.route("/callback", methods=['POST'])
def callback():
  signature = request.headers['X-Line-Signature']
  body = request.get_data(as_text=True)
  app.logger.info("Request body: " + body)
  try:
    handler.handle(body, signature)
  except InvalidSignatureError:
    print(
      "Invalid signature. Please check your channel access token/channel secret."
    )
    abort(400)
  return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
  user_id = event.source.user_id
  push_id = user_id
  group_mode = False
  if hasattr(event.source, 'group_id'):
    group_id = event.source.group_id
    push_id = group_id
    group_mode = True

  text = event.message.text
  #logger.info(f'{user_id}: {text}')
  if text.startswith(start_key_word):
    print(user_id, text)
    if text[2:].startswith(start_key_word_1):
      line_bot_api.push_message(push_id, TextSendMessage(text="我負責! 請稍等..."))
      if text[4:].startswith("debug"):
        response = image_chatgpt.get_response(user_id, text[9:].strip())
        line_bot_api.push_message(push_id, TextSendMessage(text=response))
      else:
        response = image_chatgpt.get_response(user_id, text[4:].strip())
      print(response)
      try:
        response = dalle.generate(response)
      except image_models.error.InvalidRequestError:
        msg = TextSendMessage(text="粗暴言論大可不必，我無法為你產生這種圖，你的心態很不健康!")
      else:
        msg = ImageSendMessage(original_content_url=response,
                               preview_image_url=response)
    else:
      #logger.info(f'{user_id}: {text}')
      response = chatgpt.get_response(user_id, text)
      msg = TextSendMessage(text=response)
  else:
    if group_mode == False:
      print("Test")
    return
  line_bot_api.reply_message(event.reply_token, msg)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
  user_id = event.source.user_id
  group_mode = False
  if hasattr(event.source, 'group_id'):
    group_mode = True
  if group_mode == True:
    return
  print(event.message.id)
  SendImage = line_bot_api.get_message_content(event.message.id)
  path = './img/' + event.message.id + '.png'
  with open(path, 'wb') as fd:
    for chunk in SendImage.iter_content():
      fd.write(chunk)
  image_0 = Image.open(path)
  min_side = image_0.width
  if min_side > image_0.height:
    min_side = image_0.height
  image_0 = image_0.crop((0, 0, min_side, min_side))
  image_0.thumbnail((256, 256))
  image_0.save(fp=path)
  line_bot_api.push_message(user_id, TextSendMessage(text="我來救! 請稍等..."))
  response = dalle.variation(path)
  msg = ImageSendMessage(original_content_url=response,
                         preview_image_url=response)
  line_bot_api.reply_message(event.reply_token, msg)
  os.remove(path)


@app.route("/", methods=['GET'])
def home():
  return 'Hello World'


if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)
