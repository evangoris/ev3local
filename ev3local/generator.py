# TODO: Write unit tests for generator combinators with regard to
# TODO: exceptions
#

def coroutine(f):
    def g(self):
        i = f(self)
        i.next()
        return i
    return g

class filegenerator(object):

    def __init__(self, filepath):
        self._filepath = filepath

    def __iter__(self):
        with open(self._filepath) as f:
            while True:
                yield f.read()

    @coroutine
    def __generator__(self):
        with open(self._filepath, 'w') as f:
            while True:
                value = yield
                f.write(str(value))
                f.flush()

def generator(obj):
    return obj.__generator__()

def driver(iterator, generator, delay):
    import time
    def loop():
        for x in iterator:
            generator.send(x)
            time.sleep(delay)
    return loop


@coroutine
def filter(f, generator):
    while True:
        value = yield
        generator.send(value)


@coroutine
def map(f, generator):
    while True:
        value = yield
        generator.send(f(value))


@coroutine
def branch(g1, g2):
    while True:
        v1, v2 = yield
        g1.send(v1)
        g2.send(v2)