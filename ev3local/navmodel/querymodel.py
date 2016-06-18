"""Model behind the web-service

The objects and their properties are organized in collections and each
collection is further sub-divided into types, sub-types, sub-sub-types, etc.
Moreover each object has an id which is unique within the collection the object
is a member of.

The objects can be queried with urls of the form

    /collection
    /collection/type
    /collection/type/subtype
    ...
    /collection?id=ID

The idea is that the result of each query contains enough information
to construct new more refined queries.

In general the result of a query Q is of the following form

    ([(object,[objectlink, ...]), ... ], [link, ...])

Here [link, ...] is a series of queries that refine Q.
object is an object in the result set and [objectlink, ...] is a series
of queries that give refined info on the object.

In the case of /collection?id=ID the return will always return at most one
object and be further of the form

    ([(object, [objectlink, ...])], [])

"""



class QModel(object):

    def __init__(self):

        self._tables = {}
        devices = []
        self._tables['devices'] = devices

        self.adddevice(None)
        self.adddevice(None)

    def adddevice(self, device):
        dev = {}
        dev['id']     = self._newdeviceid()
        dev['types']  = ['x', 'y']
        dev['device'] = device
        self._tables['devices'].append(dev)

    def _newdeviceid(self):
        ids = sorted([x['id'] for x in self._tables['devices']])
        id  = 1
        for i in ids:
            if id==i:
                id += 1
            else:
                return id
        return id


    def query(self, path, args):

        tablename = path[0]
        types     = path[1:]

        try:
            id = args['id']
        except KeyError:
            id = None

        if id:
            result = [x for x in self._tables[tablename] if types <= x['types'] and x['id']==id]
            return result
        else:
            result = [x for x in self._tables[tablename] if types <= x['types']]

        n     = len(types)
        ids   = [x['id'] for x in result]
        types = set([x['types'][n:][0] for x in result])

        augresults = [ ([tablename], {'id': id}, x) for (id, x) in zip(ids, result) ]
        return (augresults, [(path + [type_], {}) for type_ in types])


