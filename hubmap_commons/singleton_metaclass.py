# This component comes from the PSC Public Health Applications Common
# Software Libraries (PHACSL) project, https://github.com/PSC-PublicHealth/phacsl
# That version was in turn based on some StackOverflow examples.  It 
# provides a metaclass that can be used to produce singleton class instances.

from collections import defaultdict
class ClassIsInstanceMeta(type):
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, '_setofclasses'):
            cls._setofclasses = defaultdict(set)
        cls._setofclasses[cls.__name__].add(cls.__name__)
        def recurse_class_hierarchy(cls):
            class_list = [cls.__name__]
            for base_ in cls.__bases__:
                class_list.extend(recurse_class_hierarchy(base_))
            return class_list
        for c in recurse_class_hierarchy(cls):
            cls._setofclasses[cls.__name__].add(c)
        def isinstance(self, cls_):
            cls_str = cls_.__name__
            if cls_str in self.__class__._setofclasses[self.__class__.__name__]:
                return True
            else:
                return False
        cls.isinstance = isinstance
        super(ClassIsInstanceMeta, cls).__init__(name, bases, dct)

