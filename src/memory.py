from typing import Dict
from collections import defaultdict
from enum import Enum
 
class memory_user_state(Enum):
    NORMAL = 'normal'
    VARIATION = 'variation'
    EDIT = 'edit'
    RESERVED = 'reserved'
    

class MemoryInterface:
    def append(self, user_id: str, data) -> None:
        pass

    def update(self, user_id: str, index: int, key: str, data) -> None:
        pass

    def get_data(self, user_id: str, index: int, key: str):
        return ""
  
    def get_storage(self, user_id: str):
        return ""

    def remove(self, user_id: str) -> None:
        pass

    def user_exist(self, user_id: str) -> bool:
      return False

class Memory(MemoryInterface):
    def __init__(self, system_message):
        self.storage = defaultdict(list)
        self.system_message = system_message

    def initialize(self, user_id: str):
        self.storage[user_id] = [{
            'role': 'system', 'content': self.system_message
        }]

    def append(self, user_id: str, data: Dict) -> None:
        #print(user_id)
        #print(self.storage[user_id])
        if self.storage[user_id] == []:
            self.initialize(user_id)
        self.storage[user_id].append(data)
        if(len(self.storage[user_id])) > 4 :
          del self.storage[user_id][1]

    def get_storage(self, user_id: str) -> str:
      return self.storage[user_id]

    def remove(self, user_id: str) -> None:
      self.storage[user_id] = []
    
    def user_exist(self, user_id: str) -> bool:
      return (self.storage[user_id] != [])

class User_State(MemoryInterface):
  def __init__(self):
    self.storage = defaultdict(list)
    
  def initialize(self, user_id: str):
      self.storage[user_id] = [
        {'state': memory_user_state.NORMAL, 'prompt':''}
      ]

  def update(self, user_id: str, index: int, key: str, data) -> None:
    self.storage[user_id][index][key] = data

  def get_data(self, user_id: str, index: int, key: str):
    return self.storage[user_id][index][key]
  
  def get_storage(self, user_id: str):
    return self.storage[user_id]
  
  def remove(self, user_id: str) -> None:
    self.storage[user_id] = []

  def user_exist(self, user_id: str) -> bool:
    return (self.storage[user_id] != [])