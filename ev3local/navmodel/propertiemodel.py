"""A property model serves a collection of objects and their properties

The current value of several properties across several objects can be
queried with one call.

The right queries are contained in the responses of other queries so
little has to be assumed.

Evan Goris, 2015
"""

class PModel(object):
    """
    """
    def __init__(self):

        self._properties = {}
            # Mapping of device id to property mapping
            #

    def addobject(self, object, name, propertynames):
        """Add an object to this PModel

        Args:
            object (object): An object
            name (str): Unique name for this object
            propertynames (list of str): List of property names to serve

        Raises:
            RuntimeError: When a name in `propertynames` is not actually a
                property of `object`
        """
        oprops = {}
        for propertyname in propertynames:
            if propertyname not in dir(object):
                raise RuntimeError
            oprops[propertyname] = (lambda x: lambda: object.__getattribute__(x))(propertyname)
        self._properties[name] = oprops
        return name

    def properties(self, oname):
        """Get the property names of an object
        """
        return [ pname for pname in self._properties[oname] ]

    def propertyvalues(self, properties):
        """Augment a list of (objectname, propertyname) with
        the corresponding values

        Args:
            properties (list of tpl): List of tuples (objectname, propertyname)

        Returns:
            list of tpl: List of tuples (objectname, propertyname, propertyvalue)

        Raises:
            Runtimewarning: When unkown devices and/or properties are requested
        """
        values = []
        try:
            for deviceid, propertyid in properties:
                try:
                    device = self._properties[deviceid]
                except:
                    raise
                    raise RuntimeWarning("Unknow device %(name)s"%{'name': deviceid})
                try:
                    value  = device[propertyid]()
                except:
                    raise RuntimeWarning("Unknow property %(pname)s for device %(dname)s"%{'pname': propertyid, 'dname': deviceid})
                values.append((deviceid, propertyid, value))
            return values
        except ValueError:
            raise RuntimeWarning("Invalid list of properties: '" + str(properties) + "'")

    def objects(self):
        """Get a list of all objects

        Returns:
            list of dict: For each object a dict
                    {
                      'name': Name of object
                      'properties': List with a dict for each property
                    }
                Each dict for a property has the form
                    {
                      'name': Name of property
                      'value': Current value of property
                      'query': Tuple that can be passed to propertyvalues()
                    }
        """
        result = []
        for objectname, objectproperties in self._properties.iteritems():
            dev = {}
            dev['name'] = objectname

            properties = []
            for propertyname, propertyvalue in objectproperties.iteritems():
                properties.append({
                    'name':  propertyname,
                    'value': propertyvalue(),
                    'query': [objectname, propertyname]})

            dev['properties'] = properties

            result.append(dev)

        return result