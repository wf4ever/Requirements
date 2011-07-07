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
    refrexp = re.compile(r"^\s*(\w+)\s*(\[(\w+)\])?\s*$")
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
    return

def addRowData(rowdata, resultdata):
    if rowdata[0] != "":
        resultdata.append( (rowdata[0],
                { 'id':      rowid
                , 'role':    rowdata[1]
                , 'req':     rowdata[2]
                , 'reason':  [rowdata[3]]
                , 'benefit': rowdata[4]
                , 'impact':  rowdata[5]
                , 'source':  decodeSourceReferences(rowdata[6])
                , 'comment': rowdata[7]
                }
            ))
    else:
        resultdata.append(resultdata[-1]['reason'].append(rowdata[3])
    return resultdata

def testAddRowData():
    r1 = addRowData("R1",
        ["R1", "As", "I want", "So that", "3", "4", "ABC [1]", "Comment"],
        {})
    assert r1[0][0] == "R1"
    assert r1[0][1]["id"] == "R1"
    assert r1[0][1]["role"] == "As"
    assert r1[0][1]["req"]  == "I want"
    assert r1[0][1]["reason"][0] == "So that"
    assert r1[0][1]["benefit"] == "3"
    assert r1[0][1]["impact"] == "4"
    assert r1[0][1]["source"]["ABC"] == "1"
    assert r1[0][1]["comment"] == "Comment"
    r2 = addRowData(
        ["", "", "", "Another reason", "", "", "", ""],
        r1)
    assert r2[0][0] == "R1"
    assert r2[0][1]["id"] == "R1"
    assert r2[0][1]["role"] == "As"
    assert r2[0][1]["req"]  == "I want"
    assert r2[0][1]["reason"][0] == "So that"
    assert r2[0][1]["reason"][1] == "Another reason"
    assert r2[0][1]["benefit"] == "3"
    assert r2[0][1]["impact"] == "4"
    assert r2[0][1]["source"]["ABC"] == "1"
    assert r2[0][1]["comment"] == "Comment"
    return

def First(seq):
    return seq[0]

def IdCmp(key1, key2):
    key1 = req1[0]
    key2 = req2[0]
    

def readCSV(csvfilename, jsonfilename):
    # Read CSV data into internal data structure
    data  = { 'refs': {}, 'reqs': [] }
    rowid = None
    copydata = False
    csvfilestream = open(csvfilename, "r")
    for row in csv.reader(csvfilestream, dialect="excel"):
        if row[0] == ".refs":
            refs[row[1]] = row[2]
        elif row[0] == ".start":
            copydata = True
        elif row[0] == ".end":
            copydata = False
        elif copydata:
            addRowData(row, data['reqs'])
    csvfilestream.close()
    # Sort requirements by Id, assuming form ABCnnn
    data.reqs = sorted(row.reqs(IdCmp))
    # Now write resulting data
    jsonfilestream = open(jsonfilename, "w")
    json.dump(data, jsonfilestream, indent=4)
    jsonfilestream.close()
    return

if __name__ == "__main__":
    if len(sys.argv) <= 1 or sys.argv[1] == "test":
        print "ReadCSV: Testing..."
        testDecodeSourceReferences()
        testAddRowData()
        print "ReadCSV: Testing done."
    elif sys.argv[1] != "" and os.path.isfile(sys.argv[1]+".csv"):
        readCSV(sys.argv[1]+".csv", sys.argv[1]+".json")
    else:
        print "usage: python ReadCSV.py <filename>"
        print ""
        print "Reads <filename>.py, writes <filename.json>"
        print ""

# End.
