from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError, LineBotApiError)
from linebot.models import (MessageEvent, TextMessage, ImageMessage,
                            TextSendMessage, ImageSendMessage)
import os
import Image
import math

from src.chatgpt import ChatGPT, DALLE
from src.models import OpenAIModel
from src.memory import Memory, User_State, memory_user_state
from src.logger import logger

load_dotenv('.env')

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

user_state = dict()

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
image_create_key_word = os.getenv('IMAGE_CREATE_KEY_WORD')
image_variate_key_word = os.getenv('IMAGE_VARIATE_KEY_WORD')



def img_resize(image: Image, size: int) -> Image:
  max_side = image.height
  if image.width > image.height:
    max_side = image.width
  ratio = float(size / max_side)
  #print(max_side, ratio)
  image = image.resize(
    (math.floor(image.width * ratio), math.floor(image.height * ratio)))
  return image


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

  print(push_id not in user_state)
  if push_id not in user_state :
    user_state[push_id] = User_State()
  print(user_state[push_id].user_exist(user_id))
  if user_state[push_id].user_exist(user_id) == False:
    user_state[push_id].initialize(user_id)

  if user_state[push_id].get_data(user_id, 0, 'state') != memory_user_state.NORMAL:
    try:
      line_bot_api.push_message(push_id, TextSendMessage(text="改圖中斷"))
    except LineBotApiError as e:
      print(e)
    user_state[push_id].update(user_id, 0, 'state', memory_user_state.NORMAL)
  text = event.message.text
  #logger.info(f'{user_id}: {text}')
  if text.startswith(start_key_word):
    print(user_id, text)
    if text[2:].startswith(image_create_key_word):
      try:
        line_bot_api.push_message(push_id, TextSendMessage(text="我負責! 請稍等..."))
      except LineBotApiError as e:
        print(e)
      if text[4:].startswith("debug"):
        response = image_chatgpt.get_response(user_id, text[9:].strip())
        try:
          line_bot_api.push_message(push_id, TextSendMessage(text=response))
        except LineBotApiError as e:
          print(e)
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
    elif text[2:].startswith(image_variate_key_word):
      user_state[push_id].update(user_id, 0, 'state', memory_user_state.VARIATION)
      msg = TextSendMessage(text="責任來我就扛，請傳圖片!")
      print(push_id, user_id, user_state[push_id].get_data(user_id, 0, 'state'))
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
  push_id = user_id
  group_mode = False

  if hasattr(event.source, 'group_id'):
    group_id = event.source.group_id
    push_id = group_id
    group_mode = True

  print(push_id not in user_state)
  if push_id not in user_state :
    user_state[push_id] = User_State()
  
  print(user_state[push_id].user_exist(user_id))
  if user_state[push_id].user_exist(user_id) == False:
    user_state[push_id].initialize(user_id)

  print(push_id, user_id, user_state[push_id].get_data(user_id, 0, 'state'))
  if user_state[push_id].get_data(user_id, 0, 'state') == memory_user_state.NORMAL:
    return

  print(event.message.id)
  SendImage = line_bot_api.get_message_content(event.message.id)
  path = './img/' + event.message.id + '.png'
  with open(path, 'wb') as fd:
    for chunk in SendImage.iter_content():
      fd.write(chunk)
  image_base = Image.new("RGBA", (256, 256))
  image_base.save(fp="./img/mask.png")
  image_0 = Image.open(path)
  image_0 = img_resize(image_0, 256)
  start_x = 0
  start_y = 0
  if image_0.width > image_0.height:
    start_y = math.floor((256 - image_0.height) / 2)
  elif image_0.width < image_0.height:
    start_x = math.floor((256 - image_0.width) / 2)
  image_base.paste(image_0, (start_x, start_y))
  image_base.save(fp=path)
  try:
    line_bot_api.push_message(push_id, TextSendMessage(text="我來救! 請稍等..."))
  except LineBotApiError as e:
    print(e)
  response = dalle.variation(path)
  msg = ImageSendMessage(original_content_url=response,
                         preview_image_url=response)
  line_bot_api.reply_message(event.reply_token, msg)
  os.remove(path)
  user_state[push_id].update(user_id, 0, 'state', memory_user_state.NORMAL)

@app.route("/", methods=['GET'])
def home():
  return 'Hello World'


if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)
