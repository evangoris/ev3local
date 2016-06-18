def ev3model(motors, sensors):

    model = {
        "detail":{
            "name": lambda: "EV3",
            "motors": [],
            "sensors": []
        }
    }

    for motor in motors:
        mmodel = {
            "key": motor.port,
            "summary": {
                "port": motor.port
            },
            "detail": {
                "port": (lambda m : lambda: m.port)(motor),
                "duty_cycle": (lambda m: lambda :m.duty_cycle)(motor)
            }
        }
        model["detail"]["motors"].append(mmodel)

    for sensor in sensors:
        smodel = {
            "key": sensor.port,
            "summary": {
                "port": sensor.port
            },
            "detail": {
                "port": (lambda s: lambda :s.port)(sensor)
            }
        }
        model["detail"]["sensors"].append(smodel)

    return model


def pathtourl(server):
    return lambda path: server + '/' + '/'.join(path)

def navigatetree(tree, createlink=lambda x:x):
    """Construct a function that can be used to navigate through
    a tree.

    The return value of the navigation function contains information
    on how to navigate further into the tree. The purpose of this
    code is to have the code that determines this information and
    the code that uses this information together

    Args:
        tree (dict): Dictionary that represents the root of a tree
        createlink (callable): Callable to construct a 'link' from a path

    Returns:
        callable: Function that can be used to navigate through the tree
    """

    def compressed(dict_, prefix, linkself=False):
        """Return a compressed copy of a dictionary.

        The dictionary as part of a tree is compressed by obtaining
        a copy without all its children. Instead information is provided
        on how to navigate into its children.

        Args:
            dict (dict): Dictionary to compress
            prefix (list of str): Path up to `dict_`
            linkself (bool): If true then a link to self is added

        Returns:
            dict: Compressed copy of `dict`
        """
        newdict = {}
        newdict['links'] = []
        if linkself:
            newdict['links'].append({'type':'self', 'path': createlink(prefix + [dict_['key']])})
            for key, value in dict_["summary"].iteritems():
                newdict[key] = value
        else:
            for key, value in dict_["detail"].iteritems():
                if type(value)==list:
                    newdict['links'].append({'type': key, 'path': createlink(prefix + [key])})
                elif type(value)==dict:
                    newdict['links'].append({'type': key, 'path': createlink(prefix + [key])})
                else:
                    newdict[key] = value()
        try:
            del newdict['key']
        except KeyError:
            pass
        return newdict

    def navigate(path):
        """Use a sequence of path elements to navigate through the tree and
        return the node we end up at. The possible children of this node are not
        returned but insted information is provided on how to navigate further.

        Args:
            path (list of str): Path 'into' the model

        Returns:
            dict or list: A view of the model located at `path`
        """
        lenpath = len(path)
        i = 0
        state = tree
        while i<lenpath:
            if type(state)==dict:
                state = state["detail"][path[i]]
            elif type(state)==list:
                items = (x for x in state if x['key']==path[i])
                state = items.next()
            else:
                raise RuntimeError

            i += 1

        if type(state)==dict:
            return compressed(state, prefix=path)
        elif type(state)==list:
            return [ compressed(x, prefix=path, linkself=True) for x in state ]
        else:
            raise RuntimeError

    return navigate