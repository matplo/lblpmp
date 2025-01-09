#!/bin/bash

function thisdir()
{
	SOURCE="${BASH_SOURCE[0]}"
	while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
		DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
		SOURCE="$(readlink "$SOURCE")"
		[[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
	done
	DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
	echo ${DIR}
}
THISD=$(thisdir)

savedir=$(pwd)

source ${THISD}/bash_util.sh
cd ${THISD}

input_file=$1
if [ -z ${input_file} ]; then
	echo_error "Usage: $0 <input_file>"
	exit 1
fi

separator_plain "Publications bibtex->pdf->text"
echo_info "Input file: ${input_file}"
echo_info "This will print things to your terminal..."
today=$(date '+%Y-%m-%d')
echo_info "Today is ${today}"
# foutput=pmp_bib_pubs_${today}
foutput=$(mktemp /tmp/pmp_bib_pubs_${today}_XXXXXX)
tex_file=${foutput}.tex
bib_file=${foutput}.bib
echo_info "bib file: ${bib_file}"

echo_info "Querying INSPIRE (or local cache) for publication information..."
echo_info "To force the query to INSPIRE, use the --download"
is_download_flag_set=$(get_opt "download" $@)
download_flag=""
if [ "x${is_download_flag_set}" == "xyes" ]; then
	echo_info "Forcing download of INSPIRE information..."
	download_flag="--download"
fi

./execvenv.sh python ./inspireq.py -f ${input_file} --format "{.bibtex}" --output ${bib_file} ${download_flag}
if [ $? -ne 0 ]; then
	echo_error "Error querying INSPIRE"
	exit 1
fi

foutputBase=$(basename ${foutput})
cd $(dirname ${foutput})
cp -v ${THISD}/bibliography.tex ${tex_file}
sed -i "s|BIBFILE|${foutputBase}|g" ${tex_file}
pdflatex ${tex_file}
biber ${foutput}
pdflatex ${tex_file}
pdflatex ${tex_file}
pdf2ps ${foutput}.pdf 

echo ""
separator_plain "PMP LISTING BEGIN"
echo ""
# ps2ascii ${foutput}.ps | sed 's/     //g'
ps2ascii ${foutput}.ps | ${THISD}/reformat_text.py
# pstotext ${foutput}.ps
echo ""
separator_plain "PMP LISTING END"
echo ""

files="${foutput}.aux ${foutput}.bbl ${foutput}.bcf ${foutput}.blg ${foutput}.log ${foutput}.out ${foutput}.pdf ${foutput}.ps ${foutput}.run.xml ${foutput}Notes.bib ${foutput}.tex ${foutput}.bib"

for file in $files; do
		if [ -f $file ]; then
				# rm $file
				echo "rm $file"
		fi
done
cd -

cd ${savedir}

