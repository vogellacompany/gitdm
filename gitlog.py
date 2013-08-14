#
# Stuff for dealing with the git log output.
#
# Someday this will be the only version of grabpatch, honest.
#
from patterns import patterns
import re


#
# Input file handling.  Someday it would be good to make this smarter
# so that it handles running git with the right options and such.
#
# Someday.
#
InputFile = None

def SetInput(input):
    global InputFile
    InputFile = input

SavedLine = ''

def getline(input):
    global SavedLine
    if SavedLine:
        ret = SavedLine
        SavedLine = ''
        return ret
    l = input.readline()
    if l:
        return l.rstrip()
    return None

def SaveLine(line):
    global SavedLine
    SavedLine = line

#
# A simple state machine based on where we are in the patch.  The
# first stuff we get is the header.
#
S_HEADER = 0
#
# Then comes the single-line description.
#
S_DESC = 1
#
# ...the full changelog...
#
S_CHANGELOG = 2
#
# ...and the tag section.
#
S_TAGS = 3
S_DONE = 4

#
# The functions to handle each of these states.
#
def get_header(patch, line, input):
    if line == '':
        return S_DESC
    m = patterns['author'].match(line)
    if m:
        patch.author = m.group(1)
    return S_HEADER

def get_desc(patch, line, input):
    if not line:
        print 'Missing desc in', patch.commit
        return S_CHANGELOG
    patch.desc = line
    #print 'desc', patch.desc
    line = getline(input)
    if line:
        print 'Weird post-desc line in', patch.commit
    return S_CHANGELOG

tagline = re.compile(r'^\s+(([-a-z]+-by)|cc):.*@.*$', re.I)
def get_changelog(patch, line, input):
    #print 'cl', line
    if not line:
        if patch.templog:
            patch.changelog += patch.templog
            patch.templog = ''
    if patterns['commit'].match(line):
        # No changelog at all - usually a Linus tag
        SaveLine(line)
        return S_DONE
    elif tagline.match(line):
        if patch.templog:
            patch.changelog += patch.templog
        return get_tag(patch, line, input)
    else:
        patch.templog += line + '\n'
    return S_CHANGELOG

def get_tag(patch, line, input):
    #
    # Some people put blank lines in the middle of tags.
    #
    #print 'tag', line
    if not line:
        return S_TAGS
    #
    # A new commit line says we've gone too far.
    #
    if patterns['commit'].match(line):
        SaveLine(line)
        return S_DONE
    m = patterns['signed-off-by'].match(line)
    if m:
        patch.signoffs.append(m.group(2))
    else:
        #
        # Look for other tags indicating that somebody at least
        # looked at the patch.
        #
        for tag in ('acked-by', 'reviewed-by', 'tested-by'):
            if patterns[tag].match(line):
                patch.othertags += 1
                break
    return S_TAGS

grabbers = [ get_header, get_desc, get_changelog, get_tag ]


#
# A variant on the gitdm patch class.
#
class patch:
    def __init__(self, commit):
        self.commit = commit
        self.desc = ''
        self.changelog = ''
        self.templog = ''
        self.author = ''
        self.signoffs = [ ]
        self.othertags = 0

def grabpatch(input):
    #
    # If it's not a patch something is screwy.
    #
    line = getline(input)
    if line is None:
        return None
    m = patterns['commit'].match(line)
    if not m:
        print 'noncommit', line
        return None
    p = patch(m.group(1))
    state = S_HEADER
    #
    # Crank through the patch.
    #
    while state != S_DONE:
        line = getline(input)
        if line is None:
            if state != S_TAGS:
                print 'Ran out of patch'
            return p
        state = grabbers[state](p, line, input)
    return p
