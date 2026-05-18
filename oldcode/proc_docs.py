import os,re,time,hashlib,copy
from collections import defaultdict
from functools import reduce
from importlib import reload
import datetime
from dateutil.parser import parse
from odf import text, teletype
from odf.opendocument import load

# get_date = lambda y,m,d: datetime.datetime(y,m,d).date()

def get_paras(path):
    try: 
        textdoc = load(path)
        allparas = textdoc.getElementsByType(text.P)
        return('\n'.join([teletype.extractText(para) for para in allparas]))
    except  (RuntimeError, TypeError, NameError, Exception,TypeError) as e:
        print('Problems with filename %s, %s' % (path,e))

def get_dir_paras(path = "notes.odt"): return get_paras(path)


proc2date = lambda s,modstring = lambda s: s.strip()[1:-1]: parse(modstring(s)).date()
 
# def proc2dates(*ss,modstring = lambda s: s.strip()[1:-1]): return [proc2date(s) for s in ss]

def to_dict(txt,drex = '<\d+\W\d+\W\d+>'):
    ld = defaultdict(list)
    for k,v in zip(re.findall(drex,txt),re.split(drex,txt)[1:]): ld[proc2date(k)].append(v)
    return ld
    
# doc2dict = lambda pth,drex = '<\d+\W\d+\W\d+>': to_dict(get_dir_paras(pth),drex)
 
# def to_date_dict(txt,drex = '<\d+\W\d+\W\d+>'): 
    # dd = to_dict(txt,drex)
    # return dict(zip(proc2dates(*dd.keys()),dd.values()))
    
def get_dict_from_file(path):    
    # return to_date_dict(get_dir_paras(path))
    return to_dict(get_dir_paras(path))
    
