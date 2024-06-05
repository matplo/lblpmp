#!/usr/bin/env python3

import os
import argparse
import sys
import csv
from datetime import datetime

import re
# as per recommendation from @freylis, compile once only
CLEANR = re.compile('<.*?>') 
CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')

def cleanhtml(raw_html):
	cleantext = re.sub(CLEANR, '', raw_html)
	return cleantext

print_once_error_list = []
def print_once_error(something):
    if something not in print_once_error_list:
	    print_once_error_list.append(something)
    
def print_once_errors():
    for s in print_once_error_list:
        print(s, file=sys.stderr)

def date_ok(sdate, args, row):
	cutoffdate_min = None
	cutoffdate_max = None
	if args.calendar_year:
		cutoffdate_min = datetime.strptime('{}-01-01'.format(args.calendar_year), '%Y-%m-%d').date()
		cutoffdate_max = datetime.strptime('{}-01-01'.format(args.calendar_year+1), '%Y-%m-%d').date()
	if args.fiscal_year:
		cutoffdate_min = datetime.strptime('{}-10-01'.format(args.fiscal_year-1), '%Y-%m-%d').date()
		cutoffdate_max = datetime.strptime('{}-10-01'.format(args.fiscal_year-0), '%Y-%m-%d').date()
	if args.pmp_year:
		cutoffdate_min = datetime.strptime('{}-07-01'.format(args.pmp_year-1), '%Y-%m-%d').date()
		cutoffdate_max = datetime.strptime('{}-07-01'.format(args.pmp_year-0), '%Y-%m-%d').date()
	if args.after_date:
		try:
			cutoffdate_min = datetime.strptime('{}'.format(args.after_date), '%Y-%m-%d').date()     
		except:
			print_once_error('[e] bad after date specified {} - format should be %Y-%m-%d'.format(args.after_date))
	if args.before_date:
		try:
			cutoffdate_max = datetime.strptime('{}'.format(args.before_date), '%Y-%m-%d').date()     
		except:
			print_once_error('[e] bad before date specified {} - format should be %Y-%m-%d'.format(args.before_date))
	if 'None' in sdate:
		# print_once_error('[e] no date for entry: {}'.format(str(row)))
		return False
	if len(sdate) < len('YYYY-MM-DD'):
		sdate = sdate + '-01'
	if len(sdate) < len('YYYY-MM-DD'):
		sdate = sdate + '-01'
	odate = datetime.strptime(sdate, '%Y-%m-%d').date()
	if cutoffdate_max is None and cutoffdate_min is None:
		return True
	if cutoffdate_max is None and cutoffdate_min:
		return (odate >= cutoffdate_min)
	if cutoffdate_max and cutoffdate_min is None:
		return (odate < cutoffdate_max)
	return (odate >= cutoffdate_min and odate < cutoffdate_max)

def do_process_file(args):
	fname = args.input
	if args.debug:
		print('[i] using', fname)
	number = 1
	debug_info = []
	with open(fname, newline='') as csvfile:
		reader = csv.DictReader(csvfile)
		if args.debug:
			for row in reader:
				print(row.keys())
				break
		for row in reader:
			sdate = row['pub_date']
			if date_ok(sdate, args, row) is False:
				if args.preprints or args.preprints_only:
					sdate = row['preprint_date']
					if date_ok(sdate, args, row) is False:
						debug_info.append(['wrong prepring date', sdate, row])
						continue
				else:
					debug_info.append(['wrong pub date', sdate, row])
					continue
			jinfo = row['journal_info']
			if not args.preprints and not args.preprints_only:
				if 'n/a' in jinfo:
					debug_info.append(['no journal info', jinfo, row])
					continue
			if args.preprints_only:
				if 'n/a' in jinfo:
					pass
				else:
					continue
			title = row['title']
			title = cleanhtml(title)
			# print(f'{odate} "{title}", {jinfo},', 'https://doi.org/{}'.format(row['doi']))
			surl = 'https://doi.org/{}'.format(row['doi'])
			if 'None' in surl and (args.preprints or args.preprints_only):
				surl = row['url_record']
			if args.show_date:
				if 'n/a' not in jinfo:
					print(f'{number}) {args.prepend} "{title}", {jinfo}, {surl}, {sdate}')
				else:
					print(f'{number}) {args.prepend} "{title}", {surl}, {sdate}')
			else:
				if 'n/a' not in jinfo:
					print(f'{number}) {args.prepend} "{title}", {jinfo}, {surl}')
				else:
					print(f'{number}) {args.prepend} "{title}", {surl}')
			number = number + 1

	if args.debug:
		print('[i] debug ingfo:')
		for s in debug_info:
			ds = ' | '.join([str(xs) for xs in s])
			print(' - ', ds)


def main():
	parser = argparse.ArgumentParser(description='process csv and extract prog report', prog=os.path.basename(__file__))
	parser.add_argument('--input', help="csv file", type=str, default='prog_report_alice_pubs_2023-07-28.csv')
	year = parser.add_mutually_exclusive_group(required=False)
	year.add_argument('--pmp-year', help="current year - will take July-previous to July-current", type=int, default=None)
	year.add_argument('--fiscal-year', '--FY', help="current fiscal year - will take Oct-previous to Sept-current", type=int, default=None)
	year.add_argument('--calendar-year', help="current year - will take Dec-previous to Dec-current", type=int, default=None)
	parser.add_argument('--after-date', help='date from which to start - listing Y-m-d', type=str, default='')
	parser.add_argument('--before-date', help='date until which to list - Y-m-d', type=str, default='')
	parser.add_argument('--prepend', help='prepend text for each publication - for example "ALICE Collaboration,"', type=str, default='')
	parser.add_argument('--preprints', help='accept preprints - use the date of the preprint', action='store_true', default=False)
	parser.add_argument('--preprints-only', help='take preprints only - use the date of the preprint', action='store_true', default=False)
	parser.add_argument('--show-date', help='show date of the publication', action='store_true', default=False)
	parser.add_argument('--debug', help='show debug information', action='store_true', default=False)
	args = parser.parse_args()

	if args.after_date:
		try:
			cutoffdate_min = datetime.strptime('{}'.format(args.after_date), '%Y-%m-%d').date()     
		except:
			print_once_error('[e] bad after date specified {} - format should be %Y-%m-%d'.format(args.after_date))
			print_once_errors()
			return

	if args.before_date:
		try:
			cutoffdate_max = datetime.strptime('{}'.format(args.before_date), '%Y-%m-%d').date()     
		except:
			print_once_error('[e] bad before date specified {} - format should be %Y-%m-%d'.format(args.before_date))
			print_once_errors()
			return

	do_process_file(args)
	print_once_errors()
     
if __name__=="__main__":
	main()
