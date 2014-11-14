#!/usr/bin/env python
# 2014-11-14: original at ~/github/tombaker/shawkle/shuffle.py

from __future__ import division
import os, re, shutil, string, sys, datetime, optparse

def getoptions():
    p = optparse.OptionParser(description="Shawkle - Rule-driven maintenance of plain-text lists",
        prog="shawkle.py", version="0.5", usage="%prog")
    p.add_option("--cloud", action="store", type="string", dest="cloud", default="cloud",
        help="file, contents of which to be prefixed to each urlified HTML file; default 'cloud'")
    p.add_option("--files2dirs", action="store", type="string", dest="files2dirs", default='.files2dirs',
        help="files with corresponding target directories; default '.files2dirs'")
    p.add_option("--globalrules", action="store", type="string", dest="globalrules", default='.globalrules',
        help="rules used globally (typically an absolute pathname), processed first; default '.globalrules'")
    p.add_option("--localrules", action="store", type="string", dest="localrules", default=".rules",
        help="rules used locally (typically a relative pathname), processed second; default '.rules'")
    p.add_option("--sedtxt", action="store", type="string", dest="sedtxt", default=".sedtxt",
        help="stream edits for plain text, eg, expanding drive letters to URIs; default '.sedtxt'")
    p.add_option("--sedhtml", action="store", type="string", dest="sedhtml", default=".sedhtml",
        help="stream edits for urlified HTML, eg, shortening visible pathnames; default '.sedhtml'")
    p.add_option("--htmldir", action="store", type="string", dest="htmldir", default=".html",
        help="name of directory for urlified HTML files; default '.html'")
    ( options, arguments ) = p.parse_args()
    return options

def absfilename(filename):
    filenameexpanded = os.path.abspath(os.path.expanduser(filename))
    if os.path.isfile(filenameexpanded):
        filename = filenameexpanded 
    return filename

def absdirname(dirname):
    dirnameexpanded = os.path.abspath(os.path.expanduser(dirname))
    if os.path.isdir(dirnameexpanded):
        dirname = dirnameexpanded 
    return dirname

def datals():
    """Returns list of files in current directory, excluding dot files and subdirectories.
        If swap files, backup files, or non-text files are encountered, exits with error message."""
    filelist = []
    pathnamelist = os.listdir(os.getcwd())
    for pathname in pathnamelist:
        if os.path.isfile(pathname):
            if pathname[-3:] == "swp":
                print 'Detected swap file', repr(pathname), '- close editor and re-run - exiting...'
                print '======================================================================'
                sys.exit()
            if pathname[-1] == "~":
                print 'Detected temporary file', repr(pathname), '- delete and re-run - exiting...'
                print '======================================================================'
                sys.exit()
            if pathname[0] != ".":
                filelist.append(absfilename(pathname))
    return filelist

def removefiles(targetdirectory):
    pwd = os.getcwd()
    abstargetdir = absdirname(targetdirectory)
    if os.path.isdir(abstargetdir):
        os.chdir(abstargetdir)
        files = datals()
        if files:
            # 2012-11-05: Want to reduce amount of information displayed for now...
            # print 'Clearing out directory', repr(abstargetdir)
            for file in files:
                os.remove(file)
        os.chdir(pwd)
    else:
        print 'Directory', repr(abstargetdir), 'does not exist - exiting...'
        print '======================================================================'
        sys.exit()

def movefiles(sourcedirectory, targetdirectory):
    pwd = os.getcwd()
    abssourcedir = absdirname(sourcedirectory)
    abstargetdir = absdirname(targetdirectory)
    if os.path.isdir(abssourcedir):
        if os.path.isdir(abstargetdir):
            os.chdir(abssourcedir)
            files = datals()
            if files:
                # 2012-11-05: Want to reduce amount of information displayed for now...
                # print 'Moving files from directory', repr(sourcedirectory), "to directory", repr(targetdirectory)
                for file in files:
                    shutil.copy2(file, abstargetdir)
                    os.remove(file)
            os.chdir(pwd)
        else:
            print 'Directory', repr(abstargetdir), 'does not exist - exiting...'
            print '======================================================================'
            sys.exit()
    else:
        print 'Directory', repr(abssourcedir), 'does not exist - exiting...'
        print '======================================================================'
        sys.exit()

def movetobackups(filelist):
    """Moves given list of files to directory "$PWD/.backup", 
    bumping previous backups to ".backupi", ".backupii", and ".backupiii".
    2011-04-16: Does not test for an unsuccessful attempt to create a directory
    e.g., because of missing permissions."""
    if not filelist:
        print 'No data here to back up or process - exiting...'
        print '======================================================================'
        sys.exit()
    backupdirs = ['.backup', '.backupi', '.backupii', '.backupiii']
    for dir in backupdirs:
        if not os.path.isdir(dir):
            os.mkdir(dir)
    removefiles(backupdirs[3])
    movefiles(backupdirs[2], backupdirs[3])
    movefiles(backupdirs[1], backupdirs[2])
    movefiles(backupdirs[0], backupdirs[1])
    for file in filelist:
        shutil.move(file, backupdirs[0])

def totalsize():
    """Returns total size in bytes of files in current directory,
    silently removing files of length zero."""
    totalsize = 0
    # 2012-11-05: Want to make the display shorter for now...
    #print 'Removing zero-length files'
    for file in os.listdir(os.getcwd()):
        if os.path.isfile(file):  # ignore directories, especially hidden ("dot") directories
            filesize = os.path.getsize(file)
            if filesize == 0:
                os.remove(file)
            else:
                if file[0] != ".":
                    totalsize = totalsize + filesize
    return totalsize

def slurpdata(datafileslisted):
    """Calls mustbetext() to confirm that all listed files consist of plain text with no blank lines.
    Returns a consolidated, sorted list of lines from all files."""
    mustbetext(datafileslisted)
    alldatalines = []
    for file in datafileslisted:
        filelines = list(open(file))
        alldatalines = alldatalines + filelines
    alldatalines.sort()
    return alldatalines

def getrules(globalrulefile, localrulefile):
    """Consolidates the lines of (optional) global and (mandatory) local rule files into one list.
    Deletes comments and blank lines.  Performs sanity checks to ensure well-formedness of rules.
    Returns a consolidated list of rules, each item itself a list of rule components.
    @@TODO
    -- Test with illegal filenames.  
    -- Maybe also test for dot files.  When used as source or target files,
       dot files would throw off the size test in comparesize()."""
    globalrulelines = []
    globalrulefile = absfilename(globalrulefile)
    localrulefile = absfilename(localrulefile)
    if globalrulefile:
        try:
            globalrulelines = list(open(globalrulefile))
            # print "Using config file:", repr(globalrulefile), "- global rule file"
        except:
            pass
    try:
        localrulelines = list(open(localrulefile))
        # print "Using config file:", repr(localrulefile), "- local rule file"
    except:
        print 'Rule file', repr(localrulefile), 'does not exist (or is unusable) - exiting...'
        print '======================================================================'
        sys.exit()
    listofrulesraw = globalrulelines + localrulelines
    listofrulesparsed = []
    for line in listofrulesraw:
        linesplitonorbar = line.partition('#')[0].strip().split('|')
        if len(linesplitonorbar) == 5:
            try:
                linesplitonorbar[0] = int(linesplitonorbar[0])
            except:
                print repr(linesplitonorbar)
                print 'First field must be an integer - exiting...'
                print '======================================================================'
            if linesplitonorbar[0] < 0:
                print repr(linesplitonorbar)
                print 'First field must be a positive integer - exiting...'
                print '======================================================================'
                sys.exit()
            try:
                re.compile(linesplitonorbar[1])
            except:
                # If string 'linesplitonorbar[1]' is not valid regular expression (eg, contains unmatched parentheses)
                # or some other error occurs during compilation.
                print 'In rule:', repr(linesplitonorbar)
                print '...in order to match the regex string:', repr(linesplitonorbar[1])
                catstring = "...the rule component must be escaped as follows: '" + re.escape(linesplitonorbar[1]) + "'"
                print catstring
                sys.exit()
            if len(linesplitonorbar[4]) > 0:
                if not linesplitonorbar[4].isdigit():
                    print repr(linesplitonorbar)
                    print 'Fifth field must be an integer or zero-length string - exiting...'
                    print '======================================================================'
                    sys.exit()
            if linesplitonorbar[4] < 1:
                print repr(linesplitonorbar)
                print 'Fifth field integer must be greater than zero - exiting...'
                print '======================================================================'
                sys.exit()
            if len(linesplitonorbar[1]) > 0:
                if len(linesplitonorbar[2]) > 0:
                    if len(linesplitonorbar[3]) > 0:
                        listofrulesparsed.append(linesplitonorbar)
            else:
                print repr(linesplitonorbar)
                print 'Fields 2, 3, and 4 must be non-empty - exiting...'
                print '======================================================================'
                sys.exit()
        elif len(linesplitonorbar) > 1:
            print linesplitonorbar
            print 'Edit to five fields, simply comment out, or escape any orbars in regex string - exiting...'
            print '======================================================================'
            sys.exit()
    createdfiles = []
    count = 0
    for rule in listofrulesparsed:
        sourcefilename = rule[2]
        targetfilename = rule[3]
        valid_chars = "-_=.%s%s" % (string.ascii_letters, string.digits)
        filenames = [ sourcefilename, targetfilename ]
        for filename in filenames:
            if filename[0] == ".":
                print 'Filename', repr(filename), 'should not start with a dot...'
                sys.exit()
            for c in filename:
                if c not in valid_chars:
                    if ' ' in filename:
                        print repr(rule)
                        print 'Filename', repr(filename), 'should have no spaces'
                        sys.exit()
                    else:
                        print repr(rule)
                        print 'Filename', repr(filename), 'has one or more characters other than:', repr(valid_chars)
                        sys.exit()
            try:
                open(filename, 'a+').close()  # like "touch" ensures that filename is writable
            except:
                print 'Cannot open', repr(filename), 'as a file for appending - exiting...'
                print '======================================================================'
                sys.exit()
        createdfiles.append(targetfilename)
        if count == 0:
            createdfiles.append(sourcefilename)
        if sourcefilename == targetfilename:
            print 'In rules:', repr(rule)
            print 'Source file:', repr(sourcefilename), 'is same as target file:', repr(targetfilename), '- exiting...'
            print '======================================================================'
            sys.exit()
        if not sourcefilename in createdfiles:
            print repr(rule)
            print 'Source file', repr(sourcefilename), 'has no precedent target file.  Exiting...'
            print '======================================================================'
            sys.exit()
        count = count + 1
    return listofrulesparsed

def getmappings(mappings, helpmessage):
    """Parses the given file, the lines are supposed to consist of two fields separated by a vertical bar.
    Strips comments, commented lines, and blank lines.
    Ignores lines with more than two vertical-bar-delimited fields.
    Returns list, each item of which is a list of two items ."""
    helpmessage = str(helpmessage)
    mappings = os.path.expanduser(mappings)
    # print "Using config file:", repr(mappings), helpmessage
    mappingsraw = []
    mappingsparsed = []
    try:
        mappingsraw = list(open(mappings))
    except:
        # print 'Config file', repr(mappings), 'does not exist - skipping...'
        return mappingsparsed
    for line in mappingsraw:
        linesplitonorbar = line.partition('#')[0].strip().split('|')
        if len(linesplitonorbar) == 2:
            # 2014-01-18: strip whitespace - BEGIN
            linesplitonorbar[0] = linesplitonorbar[0].strip()
            linesplitonorbar[1] = linesplitonorbar[1].strip()
            # 2014-01-18: strip whitespace - END
            mappingsparsed.append(linesplitonorbar)
    return mappingsparsed

def relocatefiles(files2dirs):
    """Given the list of mappings of filenames to target directories:
        if file and directory both exist, moves file to directory,
        if file exists but not the target directory, reports that the file is staying put."""
    timestamp = datetime.datetime.now()
    prefix = timestamp.isoformat('.')
    for line in files2dirs:
        filename = line[0]
        dirpath = os.path.expanduser(line[1])
        timestampedpathname = dirpath + '/' + prefix[0:13] + prefix[14:16] + prefix[17:25] + '.' + filename
        try:
            shutil.move(filename, timestampedpathname)
            print 'Moving', repr(filename), 'to', repr(timestampedpathname)
        except:
            if os.path.exists(filename):
                print 'Keeping file', repr(filename), 'where it is - directory', dirpath, 'does not exist...'

def shuffle(rules, datalines):
    """Takes as arguments a list of rules and a list of data lines as a starting point.
    For the first rule only: 
        writes data lines matching a regular expression to the target file,
        writes data lines not matching the regular expression to the source file.
    For each subsequent rule: 
        reads data lines from source file, 
        writes lines matching a regular expression to the target file, 
        writes lines not matching a regular expression to the source file, overwriting the source file."""
    rulenumber = 0
    for rule in rules:
        rulenumber += 1
        field = rule[0]
        searchkey = rule[1]
        source = rule[2]
        target = rule[3]
        sortorder = rule[4]
        sourcelines = []
        targetlines = []
        # 2012-11-05: Want to shorten display for now, so commenting out...
        #if sortorder:
        #    print '%s [%s] "%s" to "%s", sorted by field %s' % (field, searchkey, source, target, sortorder)
        #else:
        #    print '%s [%s] "%s" to "%s"' % (field, searchkey, source, target)
        if rulenumber > 1:
            datalines = list(open(source))
        if field == 0:
            if searchkey == ".":
                targetlines = [ line for line in datalines ]
            else:
                sourcelines = [ line for line in datalines if not re.search(searchkey, line) ]
                targetlines = [ line for line in datalines if re.search(searchkey, line) ]
        else:
            ethfield = field - 1
            for line in datalines:
                if field > len(line.split()):
                    sourcelines.append(line)
                else:
                    if re.search(searchkey, line.split()[ethfield]):
                        targetlines.append(line)
                    else:
                        sourcelines.append(line)
        sourcefile = open(source, 'w'); sourcefile.writelines(sourcelines); sourcefile.close()
        targetfile = open(target, 'a'); targetfile.writelines(targetlines); targetfile.close()
        if sortorder:
            targetlines = list(open(target))
            targetlines = dsusort(targetlines, sortorder)
            targetfile = open(target, 'w'); targetfile.writelines(targetlines); targetfile.close()

def comparesize(sizebefore, sizeafter):
    """Given the aggregate size in bytes of files "before" and "after":
        reports if sizes are the same, or
        warns if sizes are different."""
    #print 'Size pre was', sizebefore
    #print 'Size post is', sizeafter, '- includes files, if any, moved to other directories'
    if sizebefore == sizeafter:
        #print 'Done: data shawkled and intact!'
        #print 'DONE'
        pass
    else:
        print 'Warning: data may have been lost - revert to backup!'
        print '======================================================================'

def urlify(listofdatafiles, sedtxt, sedhtml, htmldir, cloud):
    """For each file in list of files (listofdatafiles): 
        create a urlified (HTML) file in the specified directory (htmldir), 
        prepending the contents of an optional cloud file (cloud) to each urlified file,
        optionally stream-editing the plain text using before-and-after transforms (sedtxt), and
        optionally stream-editing the urlified text using before-and-after transforms (sedhtml).
        Note: Need to replace fourth argument of urlify with something like str(arguments.htmldir) - test...
        urlify(datafilesaftermove, sedtxtmappings, sedhtmlmappings, '.imac', optionalcloudfile)"""
    cloud = absfilename(cloud)
    cloudlines = []
    if os.path.isfile(cloud):
        #print "Prepending file", repr(cloud), "to each urlified file"
        cloudlines = list(open(cloud))
    htmldir = absdirname(htmldir)
    if not os.path.isdir(htmldir):
        print 'Creating directory', repr(htmldir)
        os.mkdir(htmldir)
    else:
        removefiles(htmldir)
    #print repr(htmldir)
    for file in listofdatafiles:
        try:
            openfilelines = list(open(file))
            openfilelines = cloudlines + openfilelines
        except:
            print 'Cannot open', file, '- exiting...'
            print '======================================================================'
            sys.exit()
        urlifiedlines = []
        for line in openfilelines:
            for sedmap in sedtxt:
                try:
                    old = sedmap[0]
                    new = sedmap[1]
                    oldcompiled = re.compile(old)
                    line = re.sub(oldcompiled, new, line)
                except:
                    pass
            line = urlify_string(line)
            for visualimprovement in sedhtml:
                try:
                    ugly = visualimprovement[0]
                    pretty = visualimprovement[1]
                    line = line.replace(ugly, pretty)
                except:
                    pass
            urlifiedlines.append(line)
        filehtml = htmldir + '/' + os.path.basename(file) + '.html'
        try:
            openfilehtml = open(filehtml, 'w')
        except:
            print 'Cannot open', repr(filehtml), 'for writing - exiting...'
            print '======================================================================'
            sys.exit()
        openfilehtml.write('<PRE>\n')
        linenumber = 1
        field1before = ''
        for urlifiedline in urlifiedlines:
            # 2014-01-14 For now, disabling the addition of a blank line between blocks starting with different prefixes
            # field1 = urlifiedline.split()[0]
            # if linenumber > 1:
            #     if field1before != field1:
            #         openfilehtml.write('\n')
            # field1before = field1
            # linenumber += 1
            openfilehtml.write(urlifiedline)
        openfilehtml.close()

def dsusort(dlines, field):
    """Given a list of datalines (list "dlines"):
        returns list sorted by given field (greater-than-zero integer "field")."""
    intfield = int(field)
    ethfield = intfield - 1
    dlinesdecorated = []
    for line in dlines:
        linelength = len(line.split())
        if intfield > linelength:
            fieldsought = ''
        else:
            fieldsought = line.split()[ethfield]
        decoratedline = (fieldsought, line)
        dlinesdecorated.append(decoratedline)
    dlinesdecorated.sort()
    dlinessorted = []   # 2011-03-14: Is this line necessary?
    dlinessorted = [ t[1] for t in dlinesdecorated ]
    return dlinessorted

def mustbetext(datafiles):
    """Confirms that listed files consist of plain text, with no blank lines, 
    else exits with helpful error message.
    Draws on p.25 recipe from O'Reilly Python Cookbook."""
    for file in datafiles:
        givenstring = open(file).read(512)
        text_characters = "".join(map(chr, range(32, 127))) + "\n\r\t\b"
        _null_trans = string.maketrans("", "")
        if "\0" in givenstring:     # if givenstring contains any null, it's not text
            print 'Data file:', repr(file), 'contains a null, ergo is not a text file - exiting...'
            print '======================================================================'
            sys.exit()
        if not givenstring:         # an "empty" string is "text" (arbitrary but reasonable choice)
            return True
        substringwithnontextcharacters = givenstring.translate(_null_trans, text_characters)
        lengthsubstringwithnontextcharacters = len(substringwithnontextcharacters)
        lengthgivenstring = len(givenstring)
        proportion = lengthsubstringwithnontextcharacters / lengthgivenstring
        if proportion >= 0.30: # s is 'text' if less than 30% of its characters are non-text ones
            print 'Data file', repr(file), 'has more than 30% non-text, ergo is not a text file - exiting...'
            print '======================================================================'
            sys.exit()
        filelines = list(open(file))
        for line in filelines:
            linestripped = line.strip()
            if len(linestripped) == 0:
                print 'File', repr(file), 'has blank lines - exiting...'
                print '======================================================================'
                sys.exit()

def urlify_string(s):
    """Puts HTML links around a URL, i.e., a string ("s") starting
    with "http", "file", or "irc", etc.
    This code, found on Web, appears to be based on Perl Cookbook, section 6.21 ("urlify")."""
    urls = r'(http|https|telnet|gopher|file|wais|ftp|irc)'
    ltrs = r'\w';
    gunk = r'/#~:.?+=&%@!\-'
    punc = r'.:?\-'
    any  = ltrs + gunk + punc 
    pat = re.compile(r"""
      \b                    # start at word boundary
      (                     # begin \1  {
       %(urls)s  :          # need resource and a colon
       [%(any)s] +?         # followed by one or more
                            #  of any valid character, but
                            #  be conservative and take only
                            #  what you need to....
      )                     # end   \1  }
      (?=                   # look-ahead non-consumptive assertion
       [%(punc)s]*          # either 0 or more punctuation
       [^%(any)s]           #   followed by a non-url char
       |                    # or else
       $                    #   then end of the string
      )
    """%locals(), re.VERBOSE | re.IGNORECASE)
    return re.sub(pat, r"<A HREF=\1>\1</A>", s)

if __name__ == "__main__":
    #home = os.environ.get("HOME")            # uncomment to use test data
    #testdata = home + '/shawkle/testdata/a'  # uncomment to use test data
    #os.chdir(testdata)                       # uncomment to use test data
    arguments              = getoptions()
    rules                  = getrules(arguments.globalrules, arguments.localrules)
    sizebefore             = totalsize()
    # 2012-11-05: Want to reduce amount of information displayed for now...
    # print 'Size of files is', sizebefore
    datafilesbefore        = datals()
    datalines              = slurpdata(datafilesbefore)
    movetobackups(datafilesbefore)
    shuffle(rules, datalines)
    sizeafter              = totalsize()
    filesanddestinations   = getmappings(arguments.files2dirs, '- specifies names of files and destination directories')
    relocatefiles(filesanddestinations)
    datafilesaftermove     = datals()
    sedtxtmappings         = getmappings(arguments.sedtxt, '- specifies stream edits before urlification')
    sedhtmlmappings        = getmappings(arguments.sedhtml, '- specifies stream edits after urlification')
    optionalcloudfile      = arguments.cloud
    htmldirectory          = os.path.abspath(os.path.expanduser(arguments.htmldir))
    urlify(datafilesaftermove, sedtxtmappings, sedhtmlmappings, htmldirectory, optionalcloudfile)
    comparesize(sizebefore, sizeafter)

