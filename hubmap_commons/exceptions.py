
class HTTPException(Exception):
    
    def __init__(self, description, status_code):
        Exception.__init__(self, description)
        self.status_code = status_code
        self.description = description
        
    def get_status_code(self):
        return self.status_code
    
    def get_description(self):
        return self.description
    
    
class ErrorMessage(Exception):
    
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message
        
    def get_message(self):
        return self.message