from abc import ABC
from abc import abstractmethod


class BaseAdapter(ABC):

    @abstractmethod
    def compile(self):
        pass

    @abstractmethod
    def optimize(self, payload: dict):
        pass