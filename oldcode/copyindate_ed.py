#!/usr/bin/env python
# coding: utf-8

# # Design

# Rename existing files in target
# 
# Save renamed files to archive subdirectory
# 
# Find common files, and unique files (copy the latter simply)
# 
# For each pair of common files:
# 1. Make dictionaries of two files
# 1. Find common keys and unique keys
# 1. Update with unique keys
# 1. For common keys, 
#     1. 
# 

# # Intro - Imports

# In[8]:
gdrive = r'G:\My Drive'


import os,sys,re,shutil


sys.path.append(os.path.join(gdrive,'PyLibNLG'))
import similarity as sim
import proc_docs as proc, nlgutls as ngutls
datetime,reduce,reload = [getattr(ngutls,k) for k in 'datetime,reduce,reload'.split(',')]


# In[14]:


from odf.opendocument import OpenDocumentText

from odf.style import (Style, TextProperties, ParagraphProperties, ListLevelProperties, TabStop, TabStops)

from odf.text import (H, P, List, ListItem, ListStyle, ListLevelStyleNumber, ListLevelStyleBullet)

from odf import teletype

reload(proc)

reload(sim)


def compare_ds(olddict,badkeys,newdict):
    for k in badkeys:
        print(k,d[k],newdict[k])

def hindex(s):
    m = proc.hashlib.sha256()
    m.update(s.encode())
    return m.hexdigest()

convert_tkn = lambda text: re.sub('\s+',' ',re.sub('^\s*<.{1,20}>|[^\w ]',' ',str(text).strip().lower())).strip()

convert = lambda text: re.sub('\W','',str(text).strip()).lower()

convert_tkn = lambda text: re.sub('\s+',' ',re.sub('^\s*<.{1,20}>|[^\w ]',' ',str(text).strip().lower())).strip()

fsim = lambda row: sim.similarity(*row) # given a list of two lists of tokens, separate the lists and apply sim
fsim_list = lambda row: fsim(lm(lambda s: s.split(),row)) # given a list of stories, split each and apply fsim

get_commonkeys = lambda srcdict,tgtdict: list(set(srcdict.keys()) & set(tgtdict.keys()))

def combine_files_(fn,paths):
    return combine_file_dicts(*[proc.get_dict_from_file(os.path.join(path,fn)) for path in paths])
def order_stories(d):
    return [(k,d[k]) for k in sorted(list(d.keys()),reverse=True)]

############# TESTING ##############

def compare(k,*ds): # test a key
    ar = []
    wordgroups = [set(combine_list([convert(proc.re.split('\W',story)) for story in d[k]])) for d in ds]
    basewords = wordgroups[0]
    for i,words in enumerate(wordgroups[1:]):
        if words - basewords: ar.append((k,i,words - basewords))
    return ar # list of dictionary indices in ds[1:]

today = proc.datetime.datetime.today().date()
# compar = [compare(k,srcdict,tgtdict) for k in commonkeys] # test all keys
# [e for e in compar if e]


# ## Get paths to two directories and find common file names

# ## Test

# In[31]:


massfiles = r'NLGFiles\NLGMassFiles'
paths_ = [[r'D:/']*3,
         [r'C:/Users/nlgun/Documents'] + [r'C:/Users/nlgun']*2]
drs_ = 'PortFiles Downloads .ipynb_checkpoints'.split()
drss = [[os.path.join(path,dr) for path,dr in zip(paths,drs_)] for paths in paths_]
for drs in drss:
    drs.insert(0,os.path.join(drs[0],massfiles))
drss = [[os.path.normpath(path) for path in drs] for drs in drss]
drss


# In[ ]:


path = r'D:/PortFiles/NLGFiles/NLGMassFiles'
path = r'C:/Users/nlgun/Documents'
filepath = os.path.join(path,'PortFiles/NLGFiles/NLGMassFiles','fileLog.odt')
print(filepath)
os.path.isfile(r'C:/Users/nlgun/Documents/PortFiles/NLGFiles/NLGMassFiles\fileLog.odt')
otherpath = r'C:\Users\nlgun\Documents\PortFiles\NLGFiles\NLGMassFiles\fileLog.odt'
os.path.isfile(otherpath)

# paths_ = '/run/media/nlgunther/PortFiles;/home/nlgunther/Documents'.split(';')
paths_ =lm(lambda s: s.strip(),  r'C:/Users/nlgun/Documents;D:/'.split(';'))
# paths_ =lm(lambda s: s.strip(),  r'C:/Users/nlgun/Documents;K:/'.split(';'))
paths = [os.path.join(path,r'PortFiles/NLGFiles/NLGMassFiles') for path in paths_]
paths.reverse() # OPTIONAL!!

print('Copying %s to %s' % tuple(paths))
filenames = [lf(lambda p: os.path.splitext(p)[-1]=='.odt'
                and not re.search('(?i)\d+|copy',p),os.listdir(path))
             for path in paths]
sourceset,targetset = lm(set,filenames) 
commonfilenames = list(sourceset & targetset)
uniquesourcefiles = list(sourceset - targetset)
uniquesourcefiles[:5]
# (', '.join(commonfilenames),uniquesourcefiles)


# ## Copy Unique SourceFiles

# In[ ]:


print(paths)


def testpath(path, test= lambda path: os.path.isdir(path)):
    assert test(path), 'Path %s is not valid' % path
    
# testpaths = lambda paths, test= lambda path: os.path.isdir(path): all([test(path) for path in paths])
testpaths = lambda paths, test= lambda path: os.path.isdir(path): [testpath(path,test) for path in paths]

testpaths(paths)#all ([os.path.isdir(path) for path in paths])


# In[ ]:


# paths = list(reversed(paths))
uniquepathpairs_ = [[os.path.join(path,fn) for fn in uniquesourcefiles] for path in paths] # first path, then files
uniquepathpairs = list(zip(*uniquepathpairs_)) # zip source file (exists), target file (doesn't exist)
print(uniquepathpairs[:5],len(uniquepathpairs))
allpathpairs = uniquepathpairs[0] + uniquepathpairs[1]
assert testpaths(uniquepathpairs_[0], lambda x: os.path.isfile(x))
for sourcepath,targetpath in uniquepathpairs:
    shutil.copy2(sourcepath,targetpath)


# ## Move to First Working Path

# In[ ]:


workingpath = paths[0]
get_ipython().run_line_magic('cd', '$workingpath')

get_ipython().run_line_magic('pwd', '')


# ## Testing on info.odt

# In[ ]:


# A Test
fn = 'info.odt'
srcdict,tgtdict = [proc.get_dict_from_file(os.path.join(path,fn)) for path in paths]
set(srcdict.keys()) > set(tgtdict.keys())


# # Function

# ## Get common keys

# In[ ]:


get_commonkeys = lambda srcdict,tgtdict: list(set(srcdict.keys()) & set(tgtdict.keys()))


# ## Combine file dictionaries

# In[ ]:


testsim= lambda row: sim.similarity(*lm(lambda s: s.split(),row))

def combine_file_dicts(srcdict,tgtdict):
    commonkeys = get_commonkeys(srcdict,tgtdict)
    re = proc.re
    hashlib = proc.hashlib
    import numpy as np
    import itertools as itls
    sim_thresh = 0.95
    i,changedks = 0,[]
    for k in commonkeys:
        # get the story lists for key (date) k
        srcstories,tgtstories = [d[k] for d in (srcdict,tgtdict)]
        # convert the stories for each list to eliminate uniformative characters 
        # and make a list of hash indices for source and target lists
        srchash,tgthash = [lm(lambda s: hindex(convert(s)),stories) for stories in (srcstories,tgtstories)]
        # make a dictionary mapping the target hashes to the stories
        tgthashdict = dict(zip(tgthash,tgtstories))
        # find the new hashes and the the associated new stories
        newstoriesset = set(tgthash) - set(srchash)
        newstories = [tgthashdict[h] for h in list(newstoriesset)]
        if newstories:print(k,newstories) # DEBUG
        # because different hashes may result from minor changes, perform a cosine similarity analysis
        if newstories:
            # tokenize each story in source and target story lists, leaving the white space in place
            # but converting long white space to a single space
            rows,cols = [np.array(lm(convert_tkn,strs)) for strs in (srcstories,newstories)]
            # create a #|source stories| by #|target stories| 2D array for testing all pairs' similarity
            m, n = [len(x) for x in (rows,cols)]
            testar = np.array(list(itls.product(rows,cols))).reshape(m,n,2)
            simar = np.apply_along_axis(fsim_list,-1,testar) # fsim_list splits on white space and tests pairs
            newar = np.apply_along_axis(all,0,(simar<sim_thresh))
            print('newar',newar)
            if newar.any():
                tested_newstories = np.array(newstories)[newar].tolist()
                print('adding',tested_newstories)
                srcstories.extend(tested_newstories)
                srcdict[k]=srcstories
                changedks.append(k)
    for k in tgtdict.keys(): # add the tgtdict k,v pairs where k is new to srcdict
        if k not in commonkeys: srcdict[k] = tgtdict[k]
    return srcdict


# In[ ]:


# A Test
d = combine_file_dicts(*[proc.get_dict_from_file(os.path.join(path,'info.odt')) for path in paths])


# In[ ]:


paths
len(d)


# In[ ]:


set(d.keys())>set(tgtdict.keys())


# # Apply to all common files

# ##  Loop through commonfilenames

# In[ ]:


# paths.reverse()
def combine_files_(fn,paths = paths):
    return combine_file_dicts(*[proc.get_dict_from_file(os.path.join(path,fn)) for path in paths])

combined_files,problems = [],[]
for fn in commonfilenames:
    try: combined_files.append((fn,combine_files_(fn)))
        
    except:
        problems.append(fn)
#         continue


# In[ ]:


problems


# In[ ]:


combdict = dict(combined_files)
k = sorted(combdict.keys())[0]
# k,combdict[k]


# # Convert Existing Common Files in Target

# In[ ]:


today,paths[1]


# In[ ]:


legacyfilename = 'legacy'
legacypath = os.path.join(paths[1],legacyfilename)
print(legacypath)
if not os.path.isdir(legacypath):
    print('made %s directory at %s' % (legacyfilename,legacypath))
    os.mkdir(legacypath)


# In[ ]:


commonfilenames[:10]


# ## Save Legacy Files, Creating Legacy Subdirectory if Needed

# In[ ]:


ar=[]
print(paths)


# In[ ]:


targetpath = paths[1]
print('The target path for new legacy files is %s' % legacypath)
assert os.path.split(legacypath)[0] == targetpath
for fn in commonfilenames:
    newfn = '%s_%s%s' % (os.path.splitext(fn)[0],str(today).replace('-','_'),os.path.splitext(fn)[-1])
#     newfn = '%s%s' % (os.path.splitext(fn)[0],'.txt')
    try:os.rename(os.path.join(targetpath,fn),os.path.join(legacypath,newfn) )
    except (FileExistsError,FileNotFoundError) as e:
        tpl = (fn,newfn,e)
        print(*tpl)
        ar.append((tpl))
        continue
#     break


# In[ ]:


ar


# In[ ]:


paths[0]


# ### Correct Mistakes if Needed

# In[ ]:


targetpath = paths[1]


# In[ ]:


get_ipython().run_line_magic('cd', '$targetpath')
get_ipython().run_line_magic('cd', 'legacy')
get_ipython().run_line_magic('pwd', '')


# In[ ]:


# ONE-OFF ERROR CORRECTION - FILES MOVED TO LEGACY BEFORE COMBINED FILES CREATED
legacypath = '.'
CORRECT = True#False
if CORRECT:
    print(legacypath)
    rex = '_2021_10_\d+'
    sourcetargetpaths = [(os.path.join(legacypath,fn), os.path.join(paths[1],re.sub(rex,'',fn)))
                   for fn in os.listdir(legacypath) if os.path.isfile(os.path.join(legacypath,fn))
                   and not os.path.isfile(os.path.join(paths[1],re.sub(rex,'',fn)))]
    print(sourcetargetpaths[:3])
#                   and re.search(rex,fn)]
#     for sourcepath,targetpath in sourcetargetpaths:
#         shutil.copy2(sourcepath,targetpath)
    #     break


# In[ ]:





# In[ ]:


# ONE-OFF ERROR CORRECTION
CORRECT = False
if CORRECT:
    print(legacypath)
    rex = '_2021_10_\d+'
    targetpaths = [os.path.join(paths[0],fn) 
                   for fn in os.listdir(paths[0]) if os.path.isfile(os.path.join(paths[0],fn))
                  and re.search(rex,fn)]
    for path in targetpaths:
        shutil.move(path,os.path.join(legacypath,os.path.basename(path)))
    #     break


# # Write Combined Files

# ## Imports

# In[ ]:


from odf.opendocument import OpenDocumentText

from odf.style import (Style, TextProperties, ParagraphProperties, ListLevelProperties, TabStop, TabStops)

from odf.text import (H, P, List, ListItem, ListStyle, ListLevelStyleNumber, ListLevelStyleBullet)

from odf import teletype


# ## Process all Common Files 

# In[ ]:


# make sure you define combdict first!
def save_odf(fn):
    d = combdict[fn]
    ar=[]
    for k,v in sorted(d.items(),reverse=True):
        lines = [proc.re.sub('\n+','\n',l.encode().decode().strip()) for l in v if l.strip()]
        # changed to have separate paragraphs for each line, so can re-parse next time 
        ar.extend(['<%i/%i/%i>' % (k.month,k.day,k.year) + l for l in lines])#''.join(lines))
    testdoc = OpenDocumentText()
    for e in ar:
        p = P()
        teletype.addTextToElement(p,e)
        testdoc.text.addElement(p)
    testdoc.save(os.path.join(paths[1],fn))

for fn in combdict.keys(): save_odf(fn)
    


# In[ ]:


def order_stories(d):
    return [(k,d[k]) for k in sorted(list(d.keys()),reverse=True)]

combdict = dict(combined_files)

for fn,d in combdict.items():#zip(commonfilenames,combined_files):
    fn = os.path.splitext(fn)[0]
#     newpath = os.path.join(paths[0],'%s_combined_%s.odt' % (fn,today))
    newpath = os.path.join(paths[1],'%s.odt' % fn)

# Simple Copying

# # Imports

# In[ ]:


import os, sys, shutil,datetime,re
now = datetime.datetime.now()
today = datetime.datetime.today().date()
todaystr = str(today).replace('-','_')


# # Set up Source and Target Directories to Copy

# In[ ]:


# srctgt = '/run/media/ngunther/PortFiles;/home/ngunther/Documents/NicholasGunther'.split(';')
srctgt = r'C:\Users\nlgun\Documents;K:/'.split(';')
srctgt = r'C:\Users\nlgun;D:/'.split(';')
# srctgt = r'C:\Users\nlgun;K:/'.split(';')
srctgt


# In[ ]:


[os.path.join(x,y) for x,y in zip('a b'.split(),'c d'.split())]


# In[ ]:


srcdr,tgtdr = [os.path.join(dr,stub,'PortFiles') for dr,stub in zip(srctgt,('Documents',''))]
# print(srctgt,srcdr,tgtdr,list(zip(('Documents',''),srctgt)))

# srcdr,tgtdr = [os.path.join(dr,'PortFiles') for dr in srctgt]
# srcdr,tgtdr = tgtdr,srcdr  # to reverse
for dr in (srcdr,tgtdr):
    assert os.path.isdir(dr), "% s isn't a directory" % dr
print('The source directory is %s and the target directory is %s' % (srcdr,tgtdr))


# In[ ]:


exotic = 0

# srctgt = '/run/media/ngunther/PortFiles;/home/ngunther'.split(';')
# srctgt = r'C:\Users\nlgun;D:/'.split(';')
#srcdr,tgtdr = [os.path.join(dr,'PortFiles/NLGFiles/NLGMassFiles') for dr in srctgt]
samedrs = 'Downloads;.ipynb_checkpoints'.split(';')
srcdrs,tgtdrs = [[os.path.join(dr,enddr) for enddr in samedrs] for dr in srctgt]
for a,b in zip((srcdrs,tgtdrs),(srcdr,tgtdr)): a.append(b)
print(srcdrs,tgtdrs)

if exotic:
    diffdrs = '.ipynb_checkpoints;Documents/.ipynb_checkpoints'.split(';')
    adddrs = [os.path.join(dr,enddr) for enddr,dr in zip(diffdrs,srctgt)]
    # if none
    adddrs = []
    print(adddrs)


# In[ ]:


# [old.append(new) for old,new in zip((srcdrs,tgtdrs),adddrs)]
# [old.append(new) for old,new in zip((srcdrs,tgtdrs),(srcdr,tgtdr))]

# srcdrs,tgtdrs = tgtdrs,srcdrs
print(srcdrs,tgtdrs)


# In[ ]:


# srcdr,tgtdr = [os.path.join(dr,'PortFiles') for dr in srctgt]
# srcdr,tgtdr = tgtdr,srcdr  # to reverse
assert all([os.path.isdir(dr) for dr in (srcdr,tgtdr)])
print('The source directory is %s and the target directory is %s' % (srcdr,tgtdr))


# srctgt = '/run/media/ngunther/PortFiles;/home/ngunther/Documents/NicholasGunther'.split(';')
# srcdr,tgtdr = [os.path.join(dr,'PortFiles') for dr in srctgt]
# assert all([os.path.isdir(dr) for dr in (srcdr,tgtdr)])

# srcpath,tgtpath = '/home/ngunther/Documents/NicholasGunther/PortFiles/output_compare.txt;/run/media/ngunther/PortFiles/PortFiles/output_compare.txt'.split(';')
# testfilepairs(srcpath,tgtpath,datetime.datetime(2021,1,1))
# mtime_(srcpath),mtime_(tgtpath),testfilepairs(srcpath,tgtpath,datetime.datetime(2021,7,25))

# srcpath,tgtpath = '/run/media/ngunther/PortFiles/PortFiles/addressBook.ods;/home/ngunther/Documents/NicholasGunther/PortFiles/addressBook.ods'.split(';')
# testfilepairs(srcpath,tgtpath,datetime.datetime(2021,1,1))

# In[ ]:


srcdrs[0].split(os.sep)[-1]


# # Set up Source and Target Directories

# In[ ]:


srctgtdrs = [srcdrs,tgtdrs]

srctgtdrs.reverse()
srctgtdrs


# # Set Up Tests for When to Copy a File Pair 

# In[ ]:





# In[ ]:


mtime_ = lambda path: datetime.datetime.fromtimestamp(os.path.getmtime(path))
def testfilepairs(srcpath,tgtpath,cutoff = None,future = now): # returns True = copy, False = don't copy
    if not os.path.isfile(srcpath): print('This path does not exist %s' % srcpath)
    else:
        srcmtime = mtime_(srcpath)
        if re.search('\.eml$|venv',os.path.splitext(srcpath)[-1]): return False # omit certain files
        if srcmtime > future: return False
        if cutoff and cutoff > srcmtime: return False # if srcpath file is too early, ignore it - don't copy
        elif not os.path.isfile(tgtpath): return True # if tgtpath doesn't exist, copy
        else: return mtime_(tgtpath) < srcmtime # only copy if srcpath is modified after tgtpath


# # Copy 

# In[ ]:


for i,srctgtdr in enumerate(zip(*srctgtdrs)): print(i,'Will copy from %s to %s' % tuple(srctgtdr))


# In[ ]:


os.path.basename(tgtdr),tgtdr


# In[ ]:


# srctgtdrs.reverse()
exclude = 'System Volume Information,RECYCLE.BIN,Recycled,Thumbs.db'.split(',')
shallow_list =  'Downloads .ipynb_checkpoints NLGMassFiles'.split()
keep_list = 'Kindle'.split()
directories2exclude = 'legacy'.split()

cutoff = datetime.datetime(2020,1,1)

print('Excluding %s' % exclude, 'Shallow copy only %s' % ', '.join(shallow_list))

for srcdr,tgtdr in zip(*srctgtdrs):
    copied,problems = [],[]
    print('Copying from %s to %s' % (srcdr,tgtdr))
    problemfiles = []
    srclen,tgtlen = [len(dr.split(os.sep)) for dr in (srcdr,tgtdr)]
    i = 0
    for root, dirs, files in os.walk(srcdr):
#         [dirs.remove(d) for d in list(dirs) if d in exclude]
#         directory = srcdr.split(os.sep)[-1]
#         print(directory)
        curdir = os.path.basename(root)
        tentative_exclude = any([re.search('(?i)'+dr,curdir) for dr in shallow_list])
        keep = any([re.search('(?i)'+dr,root) for dr in keep_list]) # allow full tree for certain directories
        if tentative_exclude and not keep:
            print('Only copy top of %s from %s in %s' % (curdir,root,srcdr))
            dirs[:]=[]
        srcrelpath = os.sep.join(root.split(os.sep)[srclen:])
        tgtrelpath = os.path.join(tgtdr,srcrelpath)
        #print(os.path.join(tgtdr,tgtrelpath))
        srcpaths, tgtpaths = [[os.path.join(relpath,file) for file in files] for relpath in (root,tgtrelpath)]
        for srcpath in srcpaths:
            if not os.path.isfile(srcpath): print("%s is not a file" % srcpath)
        for srcpath,tgtpath in zip(srcpaths,tgtpaths):
            #print(srcpath,'\n',tgtpath)
            #print(testfilepairs(srcpath,tgtpath,datetime.datetime(2021,1,1)),'\n'*2)
            if testfilepairs(srcpath,tgtpath,cutoff):
                try:
                    tgtdirname = os.path.dirname(tgtpath)
                    if not os.path.isdir(tgtdirname): os.mkdir(tgtdirname)
                    shutil.copy2(srcpath,tgtpath)
                    copied.append('source: %s; target: %s' % (srcpath,tgtpath))
                except: problemfiles.append('source: %s; target: %s' % (srcpath,tgtpath))
#         break
    for ar,fn in zip((copied,problemfiles),'copied problems'.split()):
        if ar:
            with open(os.path.join(tgtdr,'%s_%s.txt' % (fn,todaystr)),'w') as f: f.write('\n'.join(ar))


# In[ ]:


srctgtdrs = (srcdrs,tgtdrs)
print(srctgtdrs)


# In[ ]:


from datetime import datetime
import os, sys, shutil,re
now = datetime.now()
today = datetime.today().date()
todaystr = str(today).replace('-','_')

mtime_ = lambda path: datetime.fromtimestamp(os.path.getmtime(path))
def testfilepairs(srcpath,tgtpath,cutoff = None,future = now): # returns True = copy, False = don't copy
    if not os.path.isfile(srcpath): print('This path does not exist %s' % srcpath)
    else:
        srcmtime = mtime_(srcpath)
        if re.search('\.eml$|venv',os.path.splitext(srcpath)[-1]): return False # omit certain files
        if srcmtime > future: return False
        if cutoff and cutoff > srcmtime: return False # if srcpath file is too early, ignore it - don't copy
        elif not os.path.isfile(tgtpath): return True # if tgtpath doesn't exist, copy
        else: return mtime_(tgtpath) < srcmtime # only copy if srcpath is modified after tgtpath

# srcdr,tgtdr = r'D:\PortFiles;C:\\Users\\nlgun\\Documents\\PortFiles'.split(';')
# srcdr,tgtdr = r'D:\Downloads;C:\\Users\\nlgun\\Downloads'.split(';')
# srcdr,tgtdr = r'D:\.ipynb_checkpoints;C:\Users\\nlgun\.ipynb_checkpoints'.split(';')
srcdrs,tgtdrs = [[dr] for dr in (srcdr,tgtdr)]
srctgtdrs = [srcdrs,tgtdrs]

baselength = len(os.path.normpath(srcdr).split(os.sep))

# srctgtdrs.reverse()
exclude = 'System Volume Information,RECYCLE.BIN,Recycled,Thumbs.db'.split(',')
shallow_list =  'Downloads .ipynb_checkpoints NLGMassFiles'.split()
keep_list = 'Kindle'.split()
directories2exclude = 'legacy'.split()

cutoff = datetime(2020,1,1)

print(*[''.join((text,': ',addition,'\n'))
    for text, addition in zip('Excluding;Shallow copy only;Full copy'.split(';'),
        ([', '.join(l) for l in (exclude, shallow_list, keep_list)]))])

for srcdr,tgtdr in zip(*srctgtdrs):
    copied,problems = [],[]
    print('Copying from %s to %s' % (srcdr,tgtdr))
    problemfiles = []
    srclen,tgtlen = [len(os.path.normpath(dr).split(os.sep)) for dr in (srcdr,tgtdr)]
    i = 0
    for root, dirs, files in os.walk(srcdr):
#         [dirs.remove(d) for d in list(dirs) if d in exclude]
#         directory = os.path.normpath(srcdr).split(os.sep)[-1]
#         print(directory)
        curdir = os.path.basename(root)
        tentative_exclude = any([re.search('(?i)'+dr,curdir) for dr in shallow_list])
        keep = any([re.search('(?i)'+dr,root) for dr in keep_list]) # allow full tree for certain directories
        if tentative_exclude and not keep:
            print('Only copy top of %s from %s in %s' % (curdir,root,srcdr))
            dirs[:]=[]
        srcrelpath = os.sep.join(os.path.normpath(root).split(os.sep)[srclen:])
        tgtrelpath = os.path.join(tgtdr,srcrelpath)
        #print(os.path.join(tgtdr,tgtrelpath))
        srcpaths, tgtpaths = [[os.path.join(relpath,file) for file in files] for relpath in (root,tgtrelpath)]
        for srcpath in srcpaths:
            
            if not os.path.isfile(srcpath):
                print("%s is not a file" % srcpath)
                
        for srcpath,tgtpath in zip(srcpaths,tgtpaths):
            #print(srcpath,'\n',tgtpath)
            #print(testfilepairs(srcpath,tgtpath,datetime(2021,1,1)),'\n'*2)
            if testfilepairs(srcpath,tgtpath,cutoff):
#                 print(mtime_(srcpath),mtime_(tgtpath))
                try:
                    tgtdirname = os.path.dirname(tgtpath)
                    if not os.path.isdir(tgtdirname): os.mkdir(tgtdirname)
                    shutil.copy2(srcpath,tgtpath)
                    copied.append('source: %s; target: %s' % (srcpath,tgtpath))
                except: problemfiles.append('source: %s; target: %s' % (srcpath,tgtpath))
#         break
    for ar,fn in zip((copied,problemfiles),'copied problems'.split()):
        if ar:
            with open(os.path.join(tgtdr,'%s_%s.txt' % (fn,todaystr)),'w') as f: 
                f.write('\n'.join(ar))


# In[ ]:


print(problemfiles)
    #print(root,'\n',paths)
    #i+=1
    #if i > 12: break


# In[ ]:


ar = []
path = os.path.join(paths[1],'..','..')


# In[ ]:


os.path.normpath(paths[1]).split(os.sep)


# In[ ]:


pfiles = os.path.abspath(path)
for root,drs,files in os.walk(pfiles):
    ar.append((root,files))


# In[ ]:


print(1,
     2)
x = 3
k' = {x}'


# In[ ]:


ar[:100]


# In[ ]:


pth = r'D:\PortFiles\NLGFiles\NLGMassFiles\Diary.odt'
pth1 = r'D:\PortFiles\NLGFiles\NLGMassFiles\Diary.odt'
print(mtime_(pth),mtime_(pth1))
# testfilepairs(pth,pth1)


# In[ ]:




