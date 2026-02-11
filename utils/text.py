import difflib
from functools import reduce
from utils.wer import getCER, getWER
def overlap(s1, s2):
    # https://stackoverflow.com/a/14128905/4001592
    if s2.strip() == '':
        return s1
    if s1.strip() == '':
        return s2
    s = difflib.SequenceMatcher(None, s1, s2)
    pos_a, pos_b, size = s.find_longest_match(0, len(s1), 0, len(s2))
    result = s1[:pos_a] + s2[pos_b:]
    #print("RESULT: ", result,)
    #print(s1[:pos_a], s2[pos_b:])
    #print("S1:", s1)
    #print("S2:", s2)
    
    werR = getCER(s1, result)
    werL = getCER(s2, result)
    werRL = getCER(s1,s2)
    werLR = getCER(s2,s1)
    #print("werR:",werR)
    #print("werL:",werL)
    #print("werRL:", werRL)
    #print("werLR:", werLR)
    #print("werrrr", getCER(result,s1))
    #print("woorrr", getCER(result,s2))
    wer = werR + werL + werRL + werLR

    if len(s1)  > len(result) and wer >= 3.5:
      return s1
    else:
      return result
