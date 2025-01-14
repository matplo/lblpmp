#!/bin/bash

pdflatex bibliography.tex
biber bibliography
pdflatex bibliography.tex
pdflatex bibliography.tex
pdf2ps bibliography.pdf 
ps2ascii bibliography.ps
./clean_bibliography.sh
