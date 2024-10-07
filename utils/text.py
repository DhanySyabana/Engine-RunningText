import difflib
from functools import reduce
def overlap(s1, s2):
    # https://stackoverflow.com/a/14128905/4001592
    s = difflib.SequenceMatcher(None, s1, s2)
    pos_a, pos_b, size = s.find_longest_match(0, len(s1), 0, len(s2))
    result = s1[:pos_a] + s2[pos_b:]
    if len(s1)  > len(result):
      return s1
    else:
      return result
