#!/bin/bash

# Compilation script for the emergent deception paper
# Run this script in the same directory as the .tex and .bib files

echo "Compiling Emergent Deception in Multi-Agent Systems paper..."

# First compilation to create aux files
pdflatex emergent_deception_multiagent_systems_2025.tex

# Run BibTeX to process references
bibtex emergent_deception_multiagent_systems_2025

# Second compilation to include references
pdflatex emergent_deception_multiagent_systems_2025.tex

# Third compilation to resolve all cross-references
pdflatex emergent_deception_multiagent_systems_2025.tex

echo "Compilation complete! Check emergent_deception_multiagent_systems_2025.pdf"

# Clean up auxiliary files (optional)
# Uncomment the following lines if you want to remove auxiliary files
# rm -f *.aux *.log *.bbl *.blg *.out