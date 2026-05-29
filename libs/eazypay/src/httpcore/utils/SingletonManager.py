class SingletonMeta(type):
    """
    This is a metaclass for creating singletons.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the constructor and how to call the constructor
        are described here in this docstring.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(metaclass=SingletonMeta):
    """
    This is the base class for creating singletons.
    """
    pass
