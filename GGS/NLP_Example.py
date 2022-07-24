from ggs import *
import numpy as np
import matplotlib.pyplot as plt
import gensim


#FILL IN HERE WITH THE WORD EMBEDDING VECTOR THAT YOU WANT TO USE
#Google News embedding available for download at https://code.google.com/archive/p/word2vec/
model = gensim.models.KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True)

#Preprocessing of Wikipedia data

numThresh = 5 #If word re-occurs more than numThresh times and in multiple articles, then remove it
repeats = dict()
section = 0
with open('Data/WikipediaText.txt','r') as f:
    for line in f:
        for raw in line.split():
            word = filter(str.isalpha, raw).lower()
            if (word == 'breakpointsection'): #Pre-defined "code word" to indicate a new article!
                section = section + 1
            if word in repeats:
                if (section != repeats[word][1]):
                    repeats[word] = [repeats[word][0]+1, -1]
                else:
                    repeats[word] = [repeats[word][0]+1, section]
            else:
                repeats[word] = [1,section]

with open('ProcessedText.txt', 'w') as fileName:
    with open('Data/WikipediaText.txt','r') as f:
        for line in f:
            for raw in line.split():
                word = filter(str.isalpha, raw)

                if(word == 'BREAKPOINTSECTION'):
                    fileName.write(word+' ')
                elif (repeats[word.lower()][0] <= numThresh):
                    fileName.write(word+' ')
                elif (repeats[word.lower()][1] != -1):
                    fileName.write(word+' ')
                # else:
                #     print "Skipping", word
                
#Get Word2Vec Embedding
numWords = 1282
data = np.zeros((numWords,300))
counter = 0
with open('ProcessedText.txt','r') as f:
    for line in f:
        for raw in line.split():
            word = filter(str.isalpha, raw)
            if (word == 'BREAKPOINTSECTION'):
                print "Breakpoint at", counter
                continue
            try:
                val = model.word_vec(word)
                data[counter,:] = val
                counter = counter + 1
            except KeyError:
                continue

#Run GGS
print "Running GGS"
a = GGS(data.T, 7, 0.0001)
print a
