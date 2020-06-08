
class HTTPException(Exception):
    
    def __init__(self, description, status_code):
        Exception.__init__(self, description)
        self.status_code = status_code
        self.description = description
        
    def get_status_code(self):
        return self.status_code
    
    def get_description(self):
        return self.description