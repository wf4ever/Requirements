#!/bin/python
#
#--------1---------2---------3---------4---------5---------6---------7---------8
#
# Read CSV file from stdin, or named on command line, and generate JSON output
# that can be manipulated using Dexy. The CSV format read is the default output
# generated when saving an OpenOffcie Calc spreadsheet as CSV.
#
# The CSV input file is decorated with directives in column one key rows:
#
# .ref <tag> <description>
#       provides a reference to an external source of information linked or
#       referenced by the input file.
#
# .start
# (rows of data)
# .end
#       these delimit rows of tabular data that is emitted as JSON, and may 
#       occur multiple times.
#
# Between .start and .end tags, rows are assumed to have the following columns:
#   id      identifies a requirement
#   role    role of user to whom a requirement relates
#   req     statement of requirement
#   reason  reason for or benefit of requirement.  May be repeated.
#   benefit benefit to user score (1-5)
#   impact  impact for community score (1-5)
#   source  source of requirement (may contain reference tag in square brackets)
#   comment other comment about the requirement.
#
# Other content in the input file is ignored.
#
# The JSON output is formatted thus:
#
#   { refs: { <tag>: <description>, ... }
#   , reqs:
#     { <id>:
#       { role:     "<role>"
#       , req:      "<requirement>"
#       , reason:   "<reason>"
#       , benefit:  ["<benefit score>", ...]
#       , impact:   "<impact score>"
#       , source:   {"<source>": "<source reference tag>", ...}
#       , comment:  "<comment>"
#       }
#     , ...  
#     } 
#   }

import sys
import os
import csv
import json
import re
from operator import itemgetter, attrgetter

def decodeSourceReferences(rowdata):
    #print "rowdata: "+rowdata
    refresult = {}
    refdata = rowdata.split(",")
    #print "refdata: "+repr(refdata)
    refrexp = re.compile(r"^\s*([A-Za-z0-9_.]+)\s*(\[(\w+)\])?\s*$")
    #refrexp = re.compile(r"(^(\w+)$)")
    for r in refdata:
        #print "r: "+r
        refmatch = refrexp.match(r)
        if refmatch:
            #print "g0: "+repr(refmatch.group(0))
            #print "g1: "+repr(refmatch.group(1))
            #print "g2: "+repr(refmatch.group(2))
            #print "g3: "+repr(refmatch.group(3))
            refresult[refmatch.group(1)] = refmatch.group(3)
    return refresult

def testDecodeSourceReferences():
    r0 = decodeSourceReferences("ABC")
    assert r0["ABC"] == None
    r1 = decodeSourceReferences("ABC [1]")
    assert r1["ABC"] == "1"
    r2 = decodeSourceReferences("  ABC [1] ,  DEF[2] ")
    assert r2["ABC"] == "1"
    assert r2["DEF"] == "2"
    r3 = decodeSourceReferences("ABC[1],DEF")
    assert r3["ABC"] == "1"
    assert r3["DEF"] == None
    r4 = decodeSourceReferences("Dx.y[1]")
    assert r4["Dx.y"] == "1"
    return

def addRowDataOrig(rowdata, resultdata):
    if rowdata[0] != "":
        resultdata.append( (rowdata[0],
                { 'id':      rowdata[0]
                , 'role':    rowdata[1]
                , 'require': rowdata[2]
                , 'reason':  [rowdata[3]]
                , 'benefit': rowdata[4]
                , 'impact':  rowdata[5]
                , 'source':  decodeSourceReferences(rowdata[6])
                , 'comment': rowdata[7]
                }
            ))
    else:
        resultdata[-1][1]['reason'].append(rowdata[3])
    return resultdata

def testAddRowDataOrig():
    r1 = addRowData(
        ["R1", "As", "I want", "So that", "3", "4", "Dx.y [1]", "Comment"],
        [])
    assert r1[0][0] == "R1"
    assert r1[0][1]["id"] == "R1"
    assert r1[0][1]["role"] == "As"
    assert r1[0][1]["require"]  == "I want"
    assert r1[0][1]["reason"][0] == "So that"
    assert r1[0][1]["benefit"] == "3"
    assert r1[0][1]["impact"] == "4"
    assert r1[0][1]["source"]["Dx.y"] == "1"
    assert r1[0][1]["comment"] == "Comment"
    r2 = addRowData(
        ["", "", "", "Another reason", "", "", "", ""],
        r1)
    assert r2[0][0] == "R1"
    assert r2[0][1]["id"] == "R1"
    assert r2[0][1]["role"] == "As"
    assert r2[0][1]["require"]  == "I want"
    assert r2[0][1]["reason"][0] == "So that"
    assert r2[0][1]["reason"][1] == "Another reason"
    assert r2[0][1]["benefit"] == "3"
    assert r2[0][1]["impact"] == "4"
    assert r2[0][1]["source"]["Dx.y"] == "1"
    assert r2[0][1]["comment"] == "Comment"
    return

def addRowData(colfns, rowdata, resultdata):
    """
    Extract data from a row and add it to the rowdata structure.
    
    colfns      is a list of classes with methods for setting or adding 
                values from the corresponding columns, except the first column
                is always an identifier.
    rowdata     is a list of values from a row of the input CSV file
    resultdata  is a result data structure containing a list of
                (id,value_dictionary,maxlistlen) triples, whcih is updated to 
                reflect the supplied CSV data
    """
    if rowdata[0] != "":
        # Create new result entry from row
        itemdata = { 'id': rowdata[0], 'len': 1 }
        for i in range(1, len(colfns)):
            colfns[i].set(itemdata, rowdata[i])
        resultdata.append([rowdata[0],itemdata])
    else:
        # Add non-blank values to existing entry
        itemdata = resultdata[-1][1]
        moredata = 0
        for i in range(1, len(colfns)):
            if rowdata[i] != "":
                colfns[i].add(itemdata, rowdata[i])
                moredata = 1
        itemdata['len'] += moredata
    return resultdata

class col_single:
    """
    Column functions for singleton item values
    """
    def __init__(self, key):
        self._key = key
        return
    def set(self, itemdata, val):
        itemdata[self._key] = val
        return
    def add(self, itemdata, val):
        assert val == "", (
            "id %s, column %s: cannot add value to singleton value"%
            (itemdata['id'], self._key)
            )

class col_multiple:
    """
    Column functions for multiple item values appearing over multiple rows
    New "col_multiple" value entries are aligned across columns.
    """
    def __init__(self, key):
        self._key = key
        return
    def set(self, itemdata, val):
        itemdata[self._key] = [val]
        return
    def add(self, itemdata, val):
        if val != "":
            # Pad value list to current sub-row count
            while len(itemdata[self._key]) < itemdata['len']:
                itemdata[self._key].append("")
            # Append to value list
            itemdata[self._key].append(val)
        return

class col_commalist:
    """
    Column functions for multiple item values appearing as a comma-separated
    list
    """
    def __init__(self, key):
        self._key = key
        return
    def set(self, itemdata, val):
        itemdata[self._key] = [ v.strip() for v in val.split(",") ]
        return
    def add(self, itemdata, val):
        if val != "":
            itemdata[self._key] += [ v.strip() for v in val.split(",") ]
        return

class col_sources:
    """
    Column functions for multiple source values appearing as a comma-separated
    list
    """
    def __init__(self, key):
        self._key = key
        return
    def set(self, itemdata, val):
        itemdata[self._key] = decodeSourceReferences(val)
        return
    def add(self, itemdata, val):
        if val != "":
            itemdata[self._key].update(decodeSourceReferences(val))
        return

column_function_map = {
    'single':       col_single,
    'multiple':     col_multiple,
    'commalist':    col_commalist,
    'source':       col_sources
    }

default_column_keys = (
    'id',
    "role",
    "require",
    "reason",
    "benefit",
    "impact",
    "source",
    "comment"
    )

default_column_functions = (None,
    col_multiple("role"),
    col_single("require"),
    col_multiple("reason"),
    col_multiple("benefit"),
    col_multiple("impact"),
    col_sources("source"),
    col_multiple("comment")
    )

def testAddRowData():
    r1 = addRowData(default_column_functions,
        ["R1", "As", "I want", "So that", "3", "4", "Dx.y [1]", "Comment"],
        [])
    assert r1[0][0] == "R1"
    assert r1[0][1]["id"] == "R1"
    assert r1[0][1]["role"][0] == "As"
    assert r1[0][1]["require"]  == "I want"
    assert r1[0][1]["reason"][0] == "So that"
    assert r1[0][1]["benefit"][0] == "3"
    assert r1[0][1]["impact"][0] == "4"
    assert r1[0][1]["source"]["Dx.y"] == "1"
    assert r1[0][1]["comment"][0] == "Comment"
    r2 = addRowData(default_column_functions,
        ["", "", "", "Another reason", "", "", "", ""],
        r1)
    assert r2[0][0] == "R1"
    assert r2[0][1]["id"] == "R1"
    assert r2[0][1]["role"][0] == "As"
    assert r2[0][1]["require"]  == "I want"
    assert r2[0][1]["reason"][0] == "So that"
    assert r2[0][1]["reason"][1] == "Another reason"
    assert r2[0][1]["benefit"][0] == "3"
    assert r2[0][1]["impact"][0] == "4"
    assert r2[0][1]["source"]["Dx.y"] == "1"
    assert r2[0][1]["comment"][0] == "Comment"
    r3 = addRowData(default_column_functions,
        ["", "Role2", "", "Reason2", "3.2", "4.2", "", "Comment2"],
        r2)
    assert r3[0][0] == "R1"
    assert r3[0][1]["id"] == "R1"
    assert r3[0][1]["role"][0] == "As"
    assert r3[0][1]["role"][1] == ""
    assert r3[0][1]["role"][2] == "Role2"
    assert r3[0][1]["require"]  == "I want"
    assert r3[0][1]["reason"][0] == "So that"
    assert r3[0][1]["reason"][1] == "Another reason"
    assert r3[0][1]["reason"][2] == "Reason2"
    assert r3[0][1]["benefit"][0] == "3"
    assert r3[0][1]["benefit"][1] == ""
    assert r3[0][1]["benefit"][2] == "3.2"
    assert r3[0][1]["impact"][0] == "4"
    assert r3[0][1]["impact"][1] == ""
    assert r3[0][1]["impact"][2] == "4.2"
    assert r3[0][1]["source"]["Dx.y"] == "1"
    assert r3[0][1]["comment"][0] == "Comment"
    assert r3[0][1]["comment"][1] == ""
    assert r3[0][1]["comment"][2] == "Comment2"
    return

def intOrNone(s):
    return (s or None) and int(s)

def cmpId(key1, key2):
    keyre = re.compile(r"([A-Za-z_]+)(\d+)?")
    match1 = keyre.match(key1)
    match2 = keyre.match(key2)
    res = cmp(match1.group(1), match2.group(1))
    if res == 0:
        # Note cmp treats None < any number
        res = cmp(intOrNone(match1.group(2)), intOrNone(match2.group(2)))
    return res

def testCmpId():
    assert intOrNone(None)  == None
    assert intOrNone("")    == None
    assert intOrNone("123") == 123
    assert cmpId("A2",  "B1")  == -1
    assert cmpId("B1",  "A2")  ==  1
    assert cmpId("B",   "A")   ==  1
    assert cmpId("A1",  "A1")  ==  0
    assert cmpId("A",   "A")   ==  0
    assert cmpId("A",   "A1")  == -1
    assert cmpId("B",   "A1")  ==  1
    assert cmpId("A1",  "A10") == -1
    assert cmpId("A10", "A1")  ==  1
    assert cmpId("A10", "A2")  ==  1
    return

def readCSV(csvfilename, jsonfilename):
    # Read CSV data into internal data structure
    data  = { 'refs': {}, 'reqs': [] }
    rowid = None
    copydata = False
    colkeys  = default_column_keys
    colfuncs = default_column_functions
    csvfilestream = open(csvfilename, "r")
    for row in csv.reader(csvfilestream, dialect="excel"):
        if len(row) == 0:
            pass    # skip blank row: lpod-show.py adds blank line to CSV export
        elif row[0] == ".refs":
            refs[row[1]] = row[2]
        elif row[0] == ".start":
            copydata = True
        elif row[0] == ".end":
            copydata = False
        elif row[0] == ".keys":
            colkeys = ['id'] + row[1:]
        elif row[0] == ".types":
            colfuncs = [ None ] + [ column_function_map[row[i]](colkeys[i]) for i in range(1,len(row)) ]
        elif copydata:
            addRowData(colfuncs, row, data['reqs'], )
    csvfilestream.close()
    # Sort requirements by Id, assuming form ABCnnn
    #data['reqs'] = [ [r[0],r[1]] for r in sorted(data['reqs'], cmpId, itemgetter(0))]
    data['reqs'] = sorted(data['reqs'], cmpId, itemgetter(0))
    # Now write resulting data
    jsonfilestream = open(jsonfilename, "w")
    json.dump(data, jsonfilestream, indent=4)
    jsonfilestream.close()
    return

if __name__ == "__main__":
    if len(sys.argv) <= 1 or sys.argv[1] == "test":
        print "ReadCSV: Testing..."
        testDecodeSourceReferences()
        testCmpId()
        testAddRowData()
        print "ReadCSV: Testing done."
    elif sys.argv[1] != "" and os.path.isfile(sys.argv[1]+".csv"):
        readCSV(sys.argv[1]+".csv", sys.argv[1]+".json")
    else:
        print "usage: python ReadCSV.py <filename>"
        print ""
        print "Reads <filename>.csv, writes <filename.json>"
        print ""

# End.
