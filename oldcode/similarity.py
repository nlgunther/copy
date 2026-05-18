import math
# Computes the length of a real vector
def norm(v):return math.sqrt(sum([x**2 for x in v]) )

# @param [Array] firstlist a list of comparable objects
# @param [Array] secondlist a list of comparable objects
# @return [Float]  the cosine of the angle between firstlist and secondlist viewed as vectors as explained above
# Computes the cosine between two arrays of comparable objects  The arrays are
#   viewed as vectors in R^{|Union of two arrays|} with a
#   1 or 0 in each coordinate depending on whether the object does or doesn't occurs
#   in that array.  The dot product is just the length of their intersection.
def similarity(firstlist,secondlist):
    firstset,secondset = set(map(str.lower,firstlist)),set(map(str.lower,secondlist))
    intersection = firstset & secondset
    #print('intersection' ,intersection)
    s1size,s2size,intersectionsize = map(len,(firstset,secondset,intersection))
    # return(s1size,s2size,intersectionsize)
    return 0 if 0 in (s1size,s2size,intersectionsize) else intersectionsize/(norm([1]*s1size)*norm([1]*s2size))

sim  = similarity # similarity

def bestmatch(phrase,phraselist,returniter = False):
    ranks = map(lambda phrase1:sim(phrase,phrase1),phraselist)
    pairs = list(zip(list(ranks),phraselist))
    pairs.sort(reverse = True)
    return iter(pairs) if returniter else next(iter(pairs))
    
def listmatch(phraselist1,phraselist2):
    return [(phrase,bestmatch(phrase,phraselist2)[1]) for phrase in phraselist1]

def test():
    # print(sim((hi ho).split(' '), (hi ho).split(' ')))
    print(sim('hi'.split(' '), 'hi ho'.split(' ')) == 1 /math.sqrt(2))
    print(sim(''.split(' '), 'hi ho'.split(' ')) == 0)
    s = 'government security treasury constant maturity nominal'.split(' ')
    t = 'treasury bill secondary market'.split(' ')
    t1 = 'constant maturity treasury rate'.split( ' ')
    print(similarity(t,t1))
    print(math.acos(sim(s,t))*2/math.pi) # fraction of pi/2 so 1 = pi/2
    print(math.acos(sim(s,t1))*2/math.pi)# fraction of pi/2 so 1 = pi/2


