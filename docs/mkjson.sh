#!/bin/bash
#
# Make JSON from local CSV
#
# @@TODO make part of dexy config
#

which lpod-show.py >/dev/null
if [[ "$?" != "0" ]]; then
    echo "$0: This script needs lpod installed - see http://lpod-project.org/"
    echo "    lpod can be installed using apt-get on on Ubuntu Linux as lpod-python"
    exit 0
fi

for f in UserRequirements-astro UserRequirements-bio UserRequirements-gen TechRequirements-all TechnicalFacets; do
    lpod-show.py ../data/$f.ods >$f.csv 
    echo "python ../python/ReadCSV.py $f"
    python ../python/ReadCSV.py $f
done

#lpod-show.py ../data/UserRequirements-astro.ods >UserRequirements-astro.csv
#python ../python/ReadCSV.py UserRequirements-astro
#python ../python/ReadCSV.py UserRequirements-bio
#python ../python/ReadCSV.py UserRequirements-gen
#python ../python/ReadCSV.py TechRequirements-all
#python ../python/ReadCSV.py TechnicalFacets

# End.
