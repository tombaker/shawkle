#!/usr/bin/env python3
# 2014-11-14: original at ~/github/tombaker/shawkle/shuffle.py

import os, re, shutil, string, sys, datetime, optparse, yaml

def getoptions():
    p = optparse.OptionParser(description="Shawkle - Rule-driven maintenance of plain-text lists",
        prog="shawkle.py", version="0.5", usage="%prog")
    p.add_option("--globalrules", action="store", type="string", dest="globalrules", default='.globalrules',
        help="rules used globally (typically an absolute pathname), processed first; default '.globalrules'")
    p.add_option("--localrules", action="store", type="string", dest="localrules", default=".rules",
        help="rules used locally (typically a relative pathname), processed second; default '.rules'")
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
                print('Detected swap file', repr(pathname), '- close editor and re-run - exiting...')
                print('======================================================================')
                sys.exit()
            if pathname[-1] == "~":
                print('Detected temporary file', repr(pathname), '- delete and re-run - exiting...')
                print('======================================================================')
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
        print('Directory', repr(abstargetdir), 'does not exist - exiting...')
        print('======================================================================')
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
            print('Directory', repr(abstargetdir), 'does not exist - exiting...')
            print('======================================================================')
            sys.exit()
    else:
        print('Directory', repr(abssourcedir), 'does not exist - exiting...')
        print('======================================================================')
        sys.exit()

def movetobackups(filelist):
    """Moves given list of files to directory "$PWD/.backup", 
    bumping previous backups to ".backupi", ".backupii", and ".backupiii".
    2011-04-16: Does not test for an unsuccessful attempt to create a directory
    e.g., because of missing permissions."""
    if not filelist:
        print('No data here to back up or process - exiting...')
        print('======================================================================')
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
        print('Rule file', repr(localrulefile), 'does not exist (or is unusable) - exiting...')
        print('======================================================================')
        sys.exit()
    listofrulesraw = globalrulelines + localrulelines
    listofrulesparsed = []
    for line in listofrulesraw:
        linesplitonorbar = line.partition('#')[0].strip().split('|')
        if len(linesplitonorbar) == 5:
            try:
                linesplitonorbar[0] = int(linesplitonorbar[0])
            except:
                print(repr(linesplitonorbar))
                print('First field must be an integer - exiting...')
                print('======================================================================')
            if linesplitonorbar[0] < 0:
                print(repr(linesplitonorbar))
                print('First field must be a positive integer - exiting...')
                print('======================================================================')
                sys.exit()
            try:
                re.compile(linesplitonorbar[1])
            except:
                # If string 'linesplitonorbar[1]' is not valid regular expression (eg, contains unmatched parentheses)
                # or some other error occurs during compilation.
                print('In rule:', repr(linesplitonorbar))
                print('...in order to match the regex string:', repr(linesplitonorbar[1]))
                catstring = "...the rule component must be escaped as follows: '" + re.escape(linesplitonorbar[1]) + "'"
                print(catstring)
                sys.exit()
#            if len(linesplitonorbar[4]) > 0:
#                if not linesplitonorbar[4].isdigit():
#                    print(repr(linesplitonorbar))
#                    print('Fifth field must be an integer or zero-length string - exiting...')
#                    print('======================================================================')
#                    sys.exit()
#            if linesplitonorbar[4] < 1:
#                print(repr(linesplitonorbar))
#                print('Fifth field integer must be greater than zero - exiting...')
#                print('======================================================================')
#                sys.exit()
            if len(linesplitonorbar[1]) > 0:
                if len(linesplitonorbar[2]) > 0:
                    if len(linesplitonorbar[3]) > 0:
                        listofrulesparsed.append(linesplitonorbar)
            else:
                print(repr(linesplitonorbar))
                print('Fields 2, 3, and 4 must be non-empty - exiting...')
                print('======================================================================')
                sys.exit()
        elif len(linesplitonorbar) > 1:
            print(linesplitonorbar)
            print('Edit to five fields, simply comment out, or escape any orbars in regex string - exiting...')
            print('======================================================================')
            sys.exit()
    createdfiles = []
    count = 0
    for rule in listofrulesparsed:
        sourcefilename = rule[2]
        targetfilename = rule[3]
        # 2015-06-05: adding colon to list of permissible characters in filenames - would not work for Windows...
        valid_chars = "@:-_=.%s%s" % (string.ascii_letters, string.digits)
        filenames = [ sourcefilename, targetfilename ]
        for filename in filenames:
            if filename[0] == ".":
                print('Filename', repr(filename), 'should not start with a dot...')
                sys.exit()
            for c in filename:
                if c not in valid_chars:
                    if ' ' in filename:
                        print(repr(rule))
                        print('Filename', repr(filename), 'should have no spaces')
                        sys.exit()
                    else:
                        print(repr(rule))
                        print('Filename', repr(filename), 'has one or more characters other than:', repr(valid_chars))
                        sys.exit()
            try:
                open(filename, 'a+').close()  # like "touch" ensures that filename is writable
            except:
                print('Cannot open', repr(filename), 'as a file for appending - exiting...')
                print('======================================================================')
                sys.exit()
        createdfiles.append(targetfilename)
        if count == 0:
            createdfiles.append(sourcefilename)
        if sourcefilename == targetfilename:
            print('In rules:', repr(rule))
            print('Source file:', repr(sourcefilename), 'is same as target file:', repr(targetfilename), '- exiting...')
            print('======================================================================')
            sys.exit()
        if not sourcefilename in createdfiles:
            print(repr(rule))
            print('Source file', repr(sourcefilename), 'has no precedent target file.  Exiting...')
            print('======================================================================')
            sys.exit()
        count = count + 1
    return listofrulesparsed

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
        print('Warning: data may have been lost - revert to backup!')
        print('======================================================================')

def urlify(listofdatafiles, htmldir):
    """For each file in list of files (listofdatafiles): 
        create a urlified (HTML) file in the specified directory (htmldir), 
        Note: Need to replace fourth argument of urlify with something like str(arguments.htmldir) - test...
        urlify(datafilesaftermove, '.imac')"""
    htmldir = absdirname(htmldir)
    if not os.path.isdir(htmldir):
        print('Creating directory', repr(htmldir))
        os.mkdir(htmldir)
    else:
        removefiles(htmldir)
    for file in listofdatafiles:
        try:
            openfilelines = list(open(file))
        except:
            print('Cannot open', file, '- exiting...')
            print('======================================================================')
            sys.exit()
        urlifiedlines = []
        for line in openfilelines:
            line = urlify_string(line)
            urlifiedlines.append(line)
        filehtml = htmldir + '/' + os.path.basename(file) + '.html'
        try:
            openfilehtml = open(filehtml, 'w')
        except:
            print('Cannot open', repr(filehtml), 'for writing - exiting...')
            print('======================================================================')
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

def mustbetext(datafiles):
    """Confirms that listed files consist of plain text, with no blank lines, 
    else exits with helpful error message.
    Draws on p.25 recipe from O'Reilly Python Cookbook."""
    pass
#    for file in datafiles:
#        givenstring = open(file).read(512)
#        text_characters = "".join(map(chr, list(range(32, 127)))) + "\n\r\t\b"
#        _null_trans = string.maketrans("", "")
#        if "\0" in givenstring:     # if givenstring contains any null, it's not text
#            print('Data file:', repr(file), 'contains a null, ergo is not a text file - exiting...')
#            print('======================================================================')
#            sys.exit()
#        if not givenstring:         # an "empty" string is "text" (arbitrary but reasonable choice)
#            return True
#        substringwithnontextcharacters = givenstring.translate(_null_trans, text_characters)
#        lengthsubstringwithnontextcharacters = len(substringwithnontextcharacters)
#        lengthgivenstring = len(givenstring)
#        proportion = lengthsubstringwithnontextcharacters / lengthgivenstring
#        if proportion >= 0.30: # s is 'text' if less than 30% of its characters are non-text ones
#            print('Data file', repr(file), 'has more than 30% non-text, ergo is not a text file - exiting...')
#            print('======================================================================')
#            sys.exit()
#        filelines = list(open(file))
#        for line in filelines:
#            linestripped = line.strip()
#            if len(linestripped) == 0:
#                print('File', repr(file), 'has blank lines - exiting...')
#                print('======================================================================')
#                sys.exit()

###############################################################################################

def relocatefiles(files2dirs):
    """
    Given a dictionary mapping filenames to target directories:
    * if file and directory both exist, moves file to target directory
    * if file exists but target directory does not exist, reports that file is staying put
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    for filename, destination_dir in files2dirs['files2dirs'].items():
        destination_file = destination_dir + '/' + timestamp + '.' + filename
        try:
            shutil.move(filename, destination_file)
            print('Moving', repr(filename), 'to', repr(destination_file))
        except:
            if os.path.exists(filename):
                print('Keeping file', repr(filename), 'where it is - directory', dirpath, 'does not exist...')

def getfiles2dirs(files2dirs):
    """
    Reads yaml dictionary mapping filenames to destination directories.
    """
    with open(files2dirs) as yamlfile:
        config = yaml.load(yamlfile)
    return config

def dsusort(data_lines, sort_field_number):
    """
    Given: 
    * 'data_lines': a list of data lines
    * 'sort_field_number': number of field by which 'data_lines' is to be sorted

    Returns: 
    * 'data_lines' sorted by 'sort_field_number'
    """
    data_lines_decorated = []
    for line in data_lines:
        if int(sort_field_number) <= len(line.split()):
            sort_field_contents = line.split()[int(sort_field_number) - 1]
        else:
            sort_field_contents = ''
        data_lines_decorated.append((sort_field_contents, line))
    data_lines_decorated.sort()
    return [ t[1] for t in data_lines_decorated ]


def urlify_string(s):
    """
    2017-07-18 Puts HTML links around URLs found in a string.
    """
    URL_REGEX = re.compile(r"""((?:mailto:|git://|http://|https://)[^ <>'"{},|\\^`[\]]*)""")
    if '<a href=' in s:
        return s
    return URL_REGEX.sub(r'<a href="\1">\1</a>', s)

if __name__ == "__main__":
    arguments              = getoptions()
    rules                  = getrules(arguments.globalrules, arguments.localrules)
    sizebefore             = totalsize()
    datafilesbefore        = datals()
    datalines              = slurpdata(datafilesbefore)
    movetobackups(datafilesbefore)
    shuffle(rules, datalines)
    sizeafter              = totalsize()
    filesanddestinations   = getfiles2dirs('/Users/tbaker/Dropbox/uu/agenda/.files2dirs.yaml')
    relocatefiles(filesanddestinations)
    datafilesaftermove     = datals()
    htmldirectory          = os.path.abspath(os.path.expanduser(arguments.htmldir))
    urlify(datafilesaftermove, htmldirectory)
    comparesize(sizebefore, sizeafter)

