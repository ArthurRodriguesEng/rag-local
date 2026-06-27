def executar(func, *args, **kwargs):
    print("Antes")

    func()

    print("Depois")


@executar
def ola():
    print("Olá")


@executar
def teste():
    print("Teste")
