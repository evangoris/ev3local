class AttributeIteratorMixin(object):
    """Adds a method to a class that creates an iterator
    over the values of an attribute
    """

    def iattribute(self, name):
        """Stream the values of an attribute

        Args:
            name (str): Name of an attribute
        Yields:
            any: Value of the attribute `name` of `self`
        """
        while True:
            yield getattr(self, name)

    def sattribute(self, iter, name):
        """Stream an iterator into an attribute

        Args:
            iter (iterable of TYPE): Iterable that will provide values that are set
            name (str): Name of attribute to set with the values from `iter`

        Yields:
            iterable of TYPE: Iterable with same values as `iter`
        """
        for value in iter:
            setattr(self, name, value)
            yield value