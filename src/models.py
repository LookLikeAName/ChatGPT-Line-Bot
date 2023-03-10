from typing import List, Dict
import openai


class ModelInterface:

  def chat_completion(self, messages: List[Dict]) -> str:
    pass

  def image_generation(self, prompt: str) -> str:
    pass


class OpenAIModel(ModelInterface):

  def __init__(self,
               api_key: str,
               model_engine: str,
               image_size: str = '256x256'):
    openai.api_key = api_key
    self.model_engine = model_engine
    self.image_size = image_size
    self.error = openai.error

  def chat_completion(self, messages) -> str:
    #print(messages)
    response = openai.ChatCompletion.create(model=self.model_engine,
                                            messages=messages)
    #print(response)
    return response

  def image_generation(self, prompt: str) -> str:
    response = openai.Image.create(prompt=prompt, n=1, size=self.image_size)
    image_url = response.data[0].url
    return image_url
  
  def image_variation(self, path: str) -> str:
    response = openai.Image.create_variation(image=open(path, "rb"), n=1, size=self.image_size)
    image_url = response.data[0].url
    return image_url
