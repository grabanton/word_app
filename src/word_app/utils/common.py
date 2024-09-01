import re

class Utils:
    @staticmethod    
    def count_words(text):
        return len( re.findall( r"[0-9a-zA-Z']+", text ) )