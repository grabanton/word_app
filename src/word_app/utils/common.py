import re

class Utils:
    @staticmethod    
    def count_words(text):
        return len( re.findall( r"[a-zA-Z']+", text ) )