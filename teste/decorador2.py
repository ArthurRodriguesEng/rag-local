from functools import cached_property
from time import sleep
import init


class Calculadora:

    @staticmethod
    def somar(a, b):
        return a + b


print(Calculadora.somar(5, 2))
