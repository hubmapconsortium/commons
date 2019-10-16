import traceback
import logging


class HubmapError(Exception):
    def __init__(self, message, errors):

        # Call the base class constructor with the parameters it needs
        super().__init__(message)

        self.errors = errors
        
    def getJson(self):
        return {'displayMessage' : self.message, 'internalMessage' : self.errors}