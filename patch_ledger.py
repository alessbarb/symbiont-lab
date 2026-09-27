import os
import re

content = open('src/symbiont/core/social/ledger.py').read()
content = content.replace('''
    def open_questions(self) -> list[SocialQuestion]:''', '''
class _Temp:
    def open_questions(self) -> list[SocialQuestion]:''')

# Wait, let's just write a proper python script to fix it
