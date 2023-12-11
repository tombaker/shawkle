#!/usr/bin/env python3

from pathlib import Path
import datetime
import optparse
import os
import re
import shutil
import string
import sys
from pathlib import Path
import ruamel.yaml as yaml

class ShawkleError(SystemExit):
    """Exceptions related to this program generally."""

class RuleError(ShawkleError):
    """Exceptions related to a single rule."""

class RulesError(ShawkleError):
    """Exceptions related to sets of rules."""

class DataError(ShawkleError):
    """Exceptions related to data."""

class FilesystemError(ShawkleError):
    """Exceptions related to file system."""

class BadFilenameError(ShawkleError):
    """Exceptions related to filenames."""

def getoptions():
    p = optparse.OptionParser(
        description="Shawkle - Rule-driven maintenance of plain-text lists",
        prog="shawkle.py",
        version="0.5",
        usage="%prog",
    )
    p.add_option(
        "--globalrules",
        action="store",
        type="string",
        dest="globalrules",
        default=".globalrules",
        help="rules used globally (typically an absolute pathname), processed first; default '.globalrules'",
    )
    p.add_option(
        "--localrules",
        action="store",
        type="string",
        dest="localrules",
        default=".rules",
        help="rules used locally (typically a relative pathname), processed second; default '.rules'",
    )
    p.add_option(
        "--htmldir",
        action="store",
        type="string",
        dest="htmldir",
        default=".html",
        help="name of directory for urlified HTML files; default '.html'",
    )
    (options, arguments) = p.parse_args()
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
    """List visible files in cwd. Exit if swap, backup, non-text files found."""
    filelist = []
    pnamelist = os.listdir(os.getcwd())
    here = os.getcwd()
    for pname in pnamelist:
        if os.path.isfile(pname):
            if pname[-3:] == "swp":
                raise DataError(f"Detect swap file {repr(pname)} - skipping {here}.")
            if pname[-1] == "~":
                raise DataError(f"Detect temp file {repr(pname)} - skipping {here}.")
            if pname[0] != ".":
                filelist.append(absfilename(pname))
    return filelist


def removefiles(targetdirectory):
    pwd = os.getcwd()
    abstargetdir = absdirname(targetdirectory)
    if os.path.isdir(abstargetdir):
        os.chdir(abstargetdir)
        files = datals()
        if files:
            for file in files:
                os.remove(file)
        os.chdir(pwd)
    else:
        raise FilesystemError(f"Directory {repr(abstargetdir)} does not exist.")


def movefiles(sourcedirectory, targetdirectory):
    pwd = os.getcwd()
    abssourcedir = absdirname(sourcedirectory)
    abstargetdir = absdirname(targetdirectory)
    if os.path.isdir(abssourcedir):
        if os.path.isdir(abstargetdir):
            os.chdir(abssourcedir)
            files = datals()
            if files:
                for file in files:
                    shutil.copy2(file, abstargetdir)
                    os.remove(file)
            os.chdir(pwd)
        else:
            raise FilesystemError(f"Directory {repr(abstargetdir)} does not exist.")
    else:
        raise FilesystemError(f"Directory {repr(abstargetdir)} does not exist.")


def movetobackups(filelist):
    """Moves given list of files to directory "$PWD/.backup", 
    bumping previous backups to ".backupi", ".backupii", and ".backupiii".
    2011-04-16: Does not test for an unsuccessful attempt to create a directory
    e.g., because of missing permissions."""
    if not filelist:
        raise DataError("No data here to back up or process.")
    backup_directories = [".backup", ".backupi", ".backupii", ".backupiii"]
    for directory in backup_directories:
        if not os.path.isdir(directory):
            os.mkdir(directory)
    removefiles(backup_directories[3])
    movefiles(backup_directories[2], backup_directories[3])
    movefiles(backup_directories[1], backup_directories[2])
    movefiles(backup_directories[0], backup_directories[1])
    for file in filelist:
        shutil.move(file, backup_directories[0])


def total_size() -> int:
    """Compute total size of files in cwd, silently removing files of length zero.

    Returns:
        int: Total size of files in cwd.
    """
    cwd = Path.cwd()
    files = [entry for entry in Path.cwd().iterdir() if entry.is_file()]
    total_size = 0
    for file in files:
        if file.stat().st_size == 0:
            file.unlink()
        else:
            total_size += file.stat().st_size
    return total_size


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
        except:
            pass
    try:
        localrulelines = list(open(localrulefile))
    except:
        raise RulesError(f"Rule file {repr(localrulefile)} not found or unusable.")
    listofrulesraw = globalrulelines + localrulelines
    listofrulesparsed = []
    for line in listofrulesraw:
        linesplitonorbar = line.partition("#")[0].strip().split("|")
        if len(linesplitonorbar) == 5:
            try:
                linesplitonorbar[0] = int(linesplitonorbar[0])
            except:
                raise RuleError(f"Field 1 in {repr(linesplitonorbar)} not integer.")
            if linesplitonorbar[0] < 0:
                raise RuleError(f"Field 1 in {repr(linesplitonorbar)} not positive.")
            try:
                re.compile(linesplitonorbar[1])
            except error:
                raise RuleError(f"Escape regex: {re.escape(linesplitonorbar[1])}.")
            if linesplitonorbar[4]:
                if not linesplitonorbar[4].isdigit():
                    raise RuleError(f"Field 5, if present, must be digit.")
            if len(linesplitonorbar[1]) > 0:
                if len(linesplitonorbar[2]) > 0:
                    if len(linesplitonorbar[3]) > 0:
                        listofrulesparsed.append(linesplitonorbar)
            else:
                raise RuleError(f"Fields 2, 3, and 4 must be non-empty.")
        elif len(linesplitonorbar) > 1:
            raise RuleError(f"Cut to 5 fields, comment out, or escape pipes in regex.")
    createdfiles = []
    count = 0
    for rule in listofrulesparsed:
        sourcefilename = rule[2]
        targetfilename = rule[3]
        valid_chars = "@:-_=.%s%s" % (string.ascii_letters, string.digits)
        filenames = [sourcefilename, targetfilename]
        for filename in filenames:
            if filename[0] == ".":
                raise FilenameError(f"{repr(filename)} must not start with dot.")
                sys.exit()
            for c in filename:
                if c not in valid_chars:
                    if " " in filename:
                        raise FilenameError("{repr(filename)} must have no spaces.")
                    else:
                        raise FilenameError(f"Filenames use only {repr(valid_chars)}.")
            try:
                open(filename, "a+").close()
            except IsADirectoryError:
                raise FilesystemError(f"Cannot open {repr(filename)} as file.")
        createdfiles.append(targetfilename)
        if count == 0:
            createdfiles.append(sourcefilename)
        if sourcefilename == targetfilename:
            raise RuleError(f"{repr(sourcefilename)} is both source and target.")
        if not sourcefilename in createdfiles:
            raise RuleError(f"{repr(sourcefilename)} not initialized as source.")
        count = count + 1
    return listofrulesparsed


def shuffle(rule_list, dataline_list):
    """Takes as arguments a list of rules and a list of data lines as a starting point.
    For the first rule only: 
        writes data lines matching a regular expression to the target file,
        writes data lines not matching the regular expression to the source file.
    For each subsequent rule: 
        reads data lines from source file, 
        writes lines matching a regular expression to the target file, 
        writes lines not matching a regular expression to the source file, overwriting the source file."""
    rulenumber = 0
    for rule in rule_list:
        rulenumber += 1
        field = rule[0]
        searchkey = rule[1]
        source = rule[2]
        target = rule[3]
        sortorder = rule[4]
        sourcelines = []
        targetlines = []
        if rulenumber > 1:
            dataline_list = list(open(source))
        if field == 0:
            if searchkey == ".":
                targetlines = [line for line in dataline_list]
            else:
                sourcelines = [
                    line for line in dataline_list if not re.search(searchkey, line)
                ]
                targetlines = [
                    line for line in dataline_list if re.search(searchkey, line)
                ]
        else:
            ethfield = field - 1
            for line in dataline_list:
                if field > len(line.split()):
                    sourcelines.append(line)
                else:
                    if re.search(searchkey, line.split()[ethfield]):
                        targetlines.append(line)
                    else:
                        sourcelines.append(line)
        sourcefile = open(source, "w")
        sourcefile.writelines(sourcelines)
        sourcefile.close()
        targetfile = open(target, "a")
        targetfile.writelines(targetlines)
        targetfile.close()
        if sortorder:
            targetlines = list(open(target))
            targetlines = dsusort(targetlines, int(sortorder))
            targetfile = open(target, "w")
            targetfile.writelines(targetlines)
            targetfile.close()


def comparesize(sizebefore, sizeafter):
    """Compares aggregate size before/after and warns if different."""
    if not sizebefore == sizeafter:
        raise ShawkleError("Warning: data may have been lost - revert to backup!")


def urlify(listofdatafiles, htmldir):
    """For each file in list of files (listofdatafiles): 
        create a urlified (HTML) file in the specified directory (htmldir), 
        Note: Need to replace fourth argument of urlify with something like str(arguments.htmldir) - test...
        urlify(datafilesaftermove, '.imac')"""
    htmldir = absdirname(htmldir)
    if not os.path.isdir(htmldir):
        print("Creating directory", repr(htmldir))
        os.mkdir(htmldir)
    else:
        removefiles(htmldir)
    for file in listofdatafiles:
        try:
            openfilelines = list(open(file))
        except:
            print("Cannot open", file, "- exiting...")
            print(
                "======================================================================"
            )
            sys.exit()
        urlifiedlines = []
        for line in openfilelines:
            line = urlify_string(line)
            urlifiedlines.append(line)
        filehtml = htmldir + "/" + os.path.basename(file) + ".html"
        try:
            openfilehtml = open(filehtml, "w")
        except:
            print("Cannot open", repr(filehtml), "for writing - exiting...")
            print(
                "======================================================================"
            )
            sys.exit()
        openfilehtml.write("<PRE>\n")
        linenumber = 1
        field1before = ""
        for urlifiedline in urlifiedlines:
            openfilehtml.write(urlifiedline)
        openfilehtml.close()


def mustbetext(datafiles):
    """Confirms that listed files consist of plain text, with no blank lines, 
    else exits with helpful error message.
    Draws on p.25 recipe from O'Reilly Python Cookbook."""
    pass


def relocatefiles(files2dirs):
    """
    Given a dictionary mapping filenames to target directories:
    * if file and directory both exist, moves file to target directory
    * if file exists but target directory does not exist, reports that file is staying put
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    for filename, destination_dir in files2dirs["files2dirs"].items():
        destination_file = destination_dir + "/" + timestamp + "." + filename
        try:
            shutil.move(filename, destination_file)
            print("Moving", repr(filename), "to", repr(destination_file))
        except:
            if os.path.exists(filename):
                print(
                    "Keeping file",
                    repr(filename),
                    "where it is - directory",
                    destination_dir,
                    "does not exist...",
                )


def getfiles2dirs(files2dirs):
    """Returns dictionary (mapping files to destination directories) from YAML file."""
    with open(files2dirs) as yamlfile:
        config = yaml.safe_load(yamlfile)
    return config


def dsusort(lines: list, fn: int):
    """Return list of strings ("lines") sorted by given field."""
    return [t[1] for t in sorted([(item.split()[fn-1:fn], item) for item in lines])]


def urlify_string(s):
    """Returns given string with HTML links around any URLs found."""
    URL_REGEX = re.compile(
        r"""((?:mailto:|git://|http://|https://|file:///|chrome://)[^ <>'"{},|\\^`[\]]*)"""
    )
    if "<a href=" in s:
        return s
    return URL_REGEX.sub(r'<a href="\1">\1</a>', s)


if __name__ == "__main__":
    args = getoptions()
    rules = getrules(args.globalrules, args.localrules)
    size_before = total_size()
    datafilesbefore = datals()
    datalines = slurpdata(datafilesbefore)
    movetobackups(datafilesbefore)
    shuffle(rules, datalines)
    size_after = total_size()
    filesanddestinations = getfiles2dirs("/Users/tbaker/Dropbox/uu/mklists.yml")
    relocatefiles(filesanddestinations)
    datafilesaftermove = datals()
    htmldirectory = os.path.abspath(os.path.expanduser(args.htmldir))
    urlify(datafilesaftermove, htmldirectory)
    comparesize(size_before, size_after)
