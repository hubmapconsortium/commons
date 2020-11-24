# This component comes from the PSC Public Health Applications Common
# Software Libraries (PHACSL) project,
# https://github.com/PSC-PublicHealth/phacsl
# That version was in turn based on some StackOverflow examples.  It
# provides a metaclass that can be used to produce singleton class instances.

from typing import Dict


class SingletonMetaClass(type):
    """
    Thanks again to stackoverflow, this is a Singleton metaclass for Python.

    http://stackoverflow.com/questions/6760685/creating-a-singleton-in-python

    Note that 'self' in this case should properly be 'cls' since it is a class,
    but the syntax checker doesn't like that.
    """
    _instances: Dict[type, type] = {}

    # syntax checker cannot handle metaclasses, so 'self' rather than 'cls'
    def __call__(self, *args, **kwargs) -> type:
        if self not in self._instances:
            self._instances[self] = (super(SingletonMetaClass, self)
                                     .__call__(*args, **kwargs))
        return self._instances[self]
