files="bibliography.aux bibliography.bbl bibliography.bcf bibliography.blg bibliography.log bibliography.out bibliography.pdf bibliography.ps bibliography.run.xml bibliographyNotes.bib"

for file in $files; do
		if [ -f $file ]; then
				rm $file
		fi
done

