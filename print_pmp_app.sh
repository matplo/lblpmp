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

source ${THISD}/bash_util.sh
cd ${THISD}

input_file=$1
if [ -z ${input_file} ]; then
	echo_error "Usage: $0 <input_file>"
	exit 1
fi

separator_plain "PMP Publications"
echo_info "Input file: ${input_file}"
echo_info "This will print things to your terminal..."
today=$(date '+%Y-%m-%d')
echo_info "Today is ${today}"
foutput=pmp_pubs_${today}.csv
echo_info "CSV file: ${foutput}"

echo_info "Querying INSPIRE (or local cache) for publication information..."
echo_info "To force the query to INSPIRE, use the --download"
is_download_flag_set=$(get_opt "download" $@)
download_flag=""
if [ "x${is_download_flag_set}" == "xyes" ]; then
	echo_info "Forcing download of INSPIRE information..."
	download_flag="--download"
fi

./execvenv.sh ./inspireq.py -f ${input_file} --format "{.arxiv_id},{.inspire_id},{.preprint_date},{.pub_date},\"{.title}\",\"{.journal_info}\",{.url_record},{.doi}" --output ${foutput} ${download_flag}
if [ $? -ne 0 ]; then
	echo_error "Error querying INSPIRE"
	exit 1
fi

this_year=$(date '+%Y')

echo_info "This will print the PMP text for the year ${this_year} - will take July-previous to July-current..."
separator_plain "PMP LISTING"

echo ""
separator_plain "List of papers published in journals"
echo ""
./execvenv.sh ./process_csv.py --input ${foutput} --pmp-year ${this_year}

echo ""
separator_plain "List of pre-prints (submitted; other reports)"
echo ""
./execvenv.sh ./process_csv.py --input ${foutput} --pmp-year ${this_year} --preprints-only

echo ""
separator_plain "done."
cd -