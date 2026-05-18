import os,re
from importlib import reload
from functools import reduce
from collections import defaultdict

from datetime import datetime

l_ = lambda f: lambda *args,**kwargs: list(f(*args,**kwargs))
lm = l_(map)
lf = l_(filter)
combine_list = lambda l: proc.reduce(lambda cum,e: cum + e, l[1:], l[0])

DEBUG,MAX_DEPTH = False,3
def find_filefolder(fspec):
    fspec_ = (fspec+'$').split()
    l = fspec_.copy()
    l.reverse()
    dirlist = []
    for root,drs, files in os.walk('.',topdown=True):
        if l: # if l, look for l[-1] at the start
            wkndrs = [dr for dr in drs if re.search('^%s' % l[-1],dr)]
            if wkndrs: # if you found it, pop the list and restrict the found directories
                l.pop()
                drs[:] = wkndrs
#         print(drs)
        if not l or not wkndrs: # if list is empty or no directories based on the list restrict to those starting with letters
            drs[:] = [dr for dr in drs if re.search(r'^\w',dr)]
            if not drs: continue # if no directories, keep looping
        specdirs = [drx for drx in [os.path.join(root,dr) for dr in drs] if os.path.isdir(drx) and re.search('.*'.join(fspec_),drx)]
        if specdirs:
            infimatop = os.path.join(root,specdirs[0])
            if DEBUG: print(infimatop)
#             assert os.path.isdir(infimatop)
            dirlist.extend(specdirs)
#             break
        if len(root.split(os.path.sep))>MAX_DEPTH:
#             if DEBUG: print('Someting went wrong; too deep: %s' % root)
            continue
    return dirlist

def find_local_folders():    
    return [find_filefolder(s) for s in  'One Market code;One Product Projects'.split(';')]
