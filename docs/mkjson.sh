#!/bin/bash
#
# Make JSON from local CSV
#
# @@TODO make part of dexy config
#
python ../python/ReadCSV.py UserRequirements-astro
python ../python/ReadCSV.py UserRequirements-bio
python ../python/ReadCSV.py UserRequirements-gen
python ../python/ReadCSV.py TechRequirements-all
python ../python/ReadCSV.py TechnicalFacets

# End.
