#This is an ordinary token parser where words are read from the file and 
#are separated. Any punctuation or single letters are removed.

 #nltk.download('punkt_tab') uncomment if not yet downloaded
from nltk.tokenize import word_tokenize

import string

fileName = input()

with open(fileName, "r") as file:
    tokens = word_tokenize(file.read())

punctuations = set(string.punctuation)
tokens = [token for token in tokens 
          if not all(char in punctuations for char in token)
          and len(token) > 1]
print("Tokens")
print(tokens)

# Tokens are further parsed for their syllables
#The tglSyllabification.py is lifted from itudidyay and is used like a library
import tglSyllabification

syllables = []
for token in tokens:
    syllables.append(tglSyllabification.syllabify(token))
    
print("\nSyllables")
print(syllables)
