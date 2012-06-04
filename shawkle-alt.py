     1  def shuffle2(rules, datalines):
     2      """An alternative way to code shuffle().  
     3      Instead of writing files at every step of the way, collects lines in a dictionary structure.
     4      Initial tests on 2011-03-30 suggest that this might actually be _slower_.
     5      Takes as arguments a list of rules and a list of data lines as a starting point.
     6      For the first rule only: 
     7          writes data lines matching a regular expression to the target file,
     8          writes data lines not matching the regular expression to the source file.
     9      For each subsequent rule: 
    10          reads data lines from source file, 
    11          writes lines matching a regular expression to the target file, 
    12          writes lines not matching a regular expression to the source file, overwriting the source file."""
    13      rulenumber = 0
    14      all = {}
    15      for rule in rules:
    16          rulenumber += 1
    17          field = rule[0]
    18          searchkey = rule[1]
    19          source = rule[2]
    20          target = rule[3]
    21          sortorder = rule[4]
    22          sourcelines = []
    23          targetlines = []
    24          if sortorder:
    25              print '%s [%s] "%s" to "%s", sorted by field %s' % (field, searchkey, source, target, sortorder)
    26          else:
    27              print '%s [%s] "%s" to "%s"' % (field, searchkey, source, target)
    28          if rulenumber > 1:
    29              #datalines = list(open(source))
    30              datalines = list(all[source])
    31          if field == 0:
    32              if searchkey == ".":
    33                  sourcelines = []
    34                  targetlines = [ line for line in datalines ]
    35              else:
    36                  sourcelines = [ line for line in datalines if not re.search(searchkey, line) ]
    37                  targetlines = [ line for line in datalines if re.search(searchkey, line) ]
    38          else:
    39              ethfield = field - 1
    40              for line in datalines:
    41                  if field > len(line.split()):
    42                      sourcelines.append(line)
    43                  else:
    44                      if re.search(searchkey, line.split()[ethfield]):
    45                          targetlines.append(line)
    46                      else:
    47                          sourcelines.append(line)
    48                  if sortorder:
    49                      targetlines = dsusort(targetlines, sortorder)
    50          if sourcelines:
    51              all[source] = sourcelines
    52          else:
    53              all[source] = []
    54          if not all.has_key(target):
    55              all[target] = []
    56          if all[target]:
    57              all[target] = all[target] + targetlines
    58          else:
    59              all[target] = targetlines
    60          for key in all:
    61              newfile = open(key, 'w')
    62              newfile.writelines(all[key])
    63              newfile.close()
       
