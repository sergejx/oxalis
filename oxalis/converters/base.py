# Oxalis -- A website building tool for Gnome
# Copyright (C) 2014 Sergej Chodarev
from abc import ABCMeta, abstractmethod
from collections import namedtuple


class Converter(metaclass=ABCMeta):
    """Protocol that must be implemented by all converter classes."""
    @abstractmethod
    def __init__(self, site_path, file_path):
        pass

    @staticmethod
    @abstractmethod
    def matches(path):
        """
        Tests if the converter can be applied to the file on specified path.
        """
        pass

    @abstractmethod
    def target(self):
        """
        Get a name of generated file.
        """
        pass

    @abstractmethod
    def dependencies(self):
        """
        A list of paths to file dependencies (change of dependency would
        trigger conversion).
        """
        pass

    @abstractmethod
    def convert(self):
        """
        Do the conversion.
        Returns an ErrorMessage if some error occurred, or None otherwise.
        """
        pass


ErrorMessage = namedtuple('ErrorMessage', ['file', 'message'])
