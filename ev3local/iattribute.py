class AttributeIteratorMixin(object):
    """Adds a method to a class that creates an iterator
    over the values of an attribute
    """

    def iattribute(self, name):
        """
        Args:
            name (str): Name of an attribute
        Yields:
            any: Value of the attribute `name` of `self`
        """
        while True:
            yield getattr(self, name)

    def sattribute(self, iter, name):
        for value in iter:
            setattr(self, name, str(int(value)))
            yield value