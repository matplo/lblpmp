#!/usr/bin/env python3

import tqdm
import threading
import multiprocessing
import re
import yaml
import os
import json
import sys
import urllib.request, urllib.parse, urllib.error
import http.client
import pickle
import argparse
import tempfile
from pathlib import Path


gDebug    = False

# --- generic_object.py

class GenericObject(object):
    max_chars = 1000

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)
        if self.args:
            self.configure_from_dict(self.args.__dict__)
        if self.init_dict:
            self.configure_from_dict(self.init_dict)
        if self.init_json:
            self.configure_from_json(self.init_json)
        if self.init_yaml:
            self.configure_from_yaml(self.init_yaml)

    def configure_from_args(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def configure_from_dict(self, d, ignore_none=False):
        for k in d:
            if ignore_none and d[k] is None:
                continue
            self.__setattr__(k, d[k])

    def configure_from_json(self, js, ignore_none=False):
        d = json.loads(js)
        for k in d:
            if ignore_none and d[k] is None:
                continue
            self.__setattr__(k, d[k])

    def configure_from_yaml(self, yml, ignore_none=False):
        d = None
        if type(yml) is str:
            yml = yml.encode("utf-8")
            if os.path.exists(yml):
                with open(yml, "r") as _f:
                    yml = _f.read()
        d = yaml.safe_load(yml)
        if not isinstance(d, dict):
            raise ValueError(f"Invalid YAML input {d}")
        for k in d:
            if ignore_none and d[k] is None:
                continue
            self.__setattr__(k, d[k])

    def __getattr__(self, key):
        try:
            return self.__dict__[key]
        except KeyError:
            pass
        self.__setattr__(key, None)
        return self.__getattr__(key)

    def __str__(self) -> str:
        s = []
        s.append(
            "[i] {} ({})".format(
                str(self.__class__).split(".")[1].split("'")[0], id(self)
            )
        )
        for a in self.__dict__:
            if a[0] == "_":
                continue
            sval = str(getattr(self, a))
            if len(sval) > self.max_chars:
                sval = sval[: self.max_chars - 4] + "..."
            s.append("   {} = {}".format(str(a), sval))
        return "\n".join(s)

    def __repr__(self) -> str:
        return self.__str__()

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __iter__(self):
        _props = [a for a in self.__dict__ if a[0] != "_"]
        return iter(_props)

# --- inspire_record.py

class Cache(GenericObject):
    def __init__(self, dir=None, **kwargs):
        super().__init__(**kwargs)
        self.cache_dir = dir
        if self.cache_dir is None:
            self.cache_dir = os.curdir + "/.cache"
        self.cache_file = self.cache_dir + "/cache.db"
        os.makedirs(self.cache_dir, exist_ok=True)
        if self.verbose:
            print("[i] cache using", self.cache_file, file=sys.stderr)
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, "a+") as _f:
                if self.verbose:
                    print("[i] cache file created", self.cache_file)
                pass
        if not os.path.exists(self.cache_file):
            print("[e] cache file does not exist", self.cache_file, file=sys.stderr)
            self.cache_file = None

    def save_query(self, url_inspire, feedr):
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=self.cache_dir, delete=False
        ) as _ffeed:
            with open(self.cache_file, "a+") as _fcache:
                _fcache.writelines(
                    ["[*url]={} [*file]={}\n".format(url_inspire, _ffeed.name)]
                )
            _ffeed.write(feedr)
            _ffeed.close()
            if self.verbose:
                print("[i] written", _ffeed.name, file=sys.stderr)
        self.purge(url_inspire=url_inspire)

    def read_query(self, url_inspire):
        if self.verbose:
            print("[i] checking cache...", file=sys.stderr)
        with open(self.cache_file, "r") as _fcache:
            db = _fcache.readlines()
        file_to_read = None
        for l in db:
            if "[*url]={}".format(url_inspire) in l:
                file_to_read = l.split("[*file]=")[1].strip("\n")
        if file_to_read is None:
            if self.verbose:
                print("[i] no cached result", file=sys.stderr)
            return None
        with open(file_to_read, "rb") as _ffeed:
            feedr = _ffeed.read()
        if self.verbose:
            print(
                "[i] using cached result from {}".format(file_to_read), file=sys.stderr
            )
        return feedr

    def purge(self, url_inspire):
        if self.read_query(url_inspire=url_inspire):
            if self.verbose:
                print("[i] checking cache for duplicates...", file=sys.stderr)
            with open(self.cache_file, "r") as _fcache:
                # db = [l.strip('\n') for l in _fcache.readlines()]
                db = _fcache.readlines()
            entries = []
            for l in db:
                if "[*url]={}".format(url_inspire) in l:
                    entries.append(l)
            if len(entries) < 2:
                return
            if self.verbose:
                print("[i] last entry:", entries[-1].strip("\n"), file=sys.stderr)
                print("    duplicates:", entries[:-1], file=sys.stderr)
            new_db = []
            files_to_delete = []
            for l in db:
                if "[*url]={}".format(url_inspire) in l:
                    if l == entries[-1]:
                        new_db.append(l)
                    else:
                        file_name_from_entry = l.split("[*file]=")[1].strip("\n")
                        files_to_delete.append(file_name_from_entry)
                else:
                    new_db.append(l)
            with open(self.cache_file, "w") as _fcache:
                _fcache.writelines(new_db)
            for _df in files_to_delete:
                if os.path.exists(_df):
                    if self.verbose:
                        print("[w] removing", _df, file=sys.stderr)
                    os.remove(_df)


# return dictionary where a=value can be more words 23
def get_eq_val(s):
    ret_dict = {}
    if s is None:
        return ret_dict
    if len(s) < 1:
        return ret_dict
    regex = r"[\w]+="
    matches = re.findall(regex, s, re.MULTILINE)
    for i, m in enumerate(matches):
        m_start = s.index(m)
        m_end = -1
        if i < len(matches) - 1:
            m_end = s.index(matches[i + 1]) - 1
        else:
            m_end = len(s)
        _sm = s[m_start:m_end]
        eqs = _sm.split("=")
        ret_dict[eqs[0]] = eqs[1].strip()
    return ret_dict


class InspireRecordData(GenericObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.from_string:
            self.arxiv_id = self.from_string.split()[0]
            if len(self.from_string.split()) > 1:
                self.extra_info = " ".join(self.from_string.split()[1:])
        if self.from_record:
            self.record = self.from_record
            if self.record.source is None:
                self.record.source = "unknown"
            if self.record.source.lower().startswith("arxiv"):
                self.arxiv_id = self.record.id
            else:
                self.arxiv_id = None
            if self.record.source.lower().startswith("inspire"):
                self.inspire_id = self.record.id
            else:
                self.inspire_id = None
        _tmpd = get_eq_val(self.extra_info)
        for k in _tmpd:
            self.__setattr__(k, _tmpd[k])


class InspireRecord(GenericObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.from_string:
            self.data = InspireRecordData(from_string=self.from_string, verbose=self.verbose)
        if self.from_record:
            self.data = InspireRecordData(from_record=self.from_record, verbose=self.verbose)
        if self.cache_dir is None:
            _id = None
            if self.data.arxiv_id:
                _id = self.data.arxiv_id
            if self.data.inspire_id:
                _id = self.data.inspire_id
            if _id:
                self.cache_dir = os.path.join("./.cache", _id)
        if self.verbose:
            print("[i] data", self.data)
            print("[i] cache dir", self.cache_dir)
        if self.cache_dir:
            self.cache = Cache(dir=self.cache_dir, verbose=self.verbose)
            self.is_valid = True
            _ = self.retrieve()
        else:
            self.data.inspire_record_json = None
            self.is_valid = False

    def decode_journal_string(self):
        _journal_info = None

        try:
            jname = self.data.inspire_record_json["metadata"]["publication_info"][0]["journal_title"]
            jyear = self.data.inspire_record_json["metadata"]["publication_info"][0]["year"]
            _journal_info = f"{jname} ({jyear})"
        except:
            pass

        try:
            jname = self.data.inspire_record_json["metadata"]["publication_info"][0]["journal_title"]
            jvol = self.data.inspire_record_json["metadata"]["publication_info"][0]["journal_volume"]
            jartid = self.data.inspire_record_json["metadata"]["publication_info"][0]["artid"]
            jyear = self.data.inspire_record_json["metadata"]["publication_info"][0]["year"]
            _journal_info = f"{jname} {jvol} {jartid} ({jyear})"
        except:
            pass

        try:
            jname = self.data.inspire_record_json["metadata"]["publication_info"][0]["journal_title"]
            jvol = self.data.inspire_record_json["metadata"]["publication_info"][0]["journal_volume"]
            _pstart = self.data.inspire_record_json["metadata"]["publication_info"][0]["page_start"]
            _pend = self.data.inspire_record_json["metadata"]["publication_info"][0]["page_end"]
            jartid = "p.{}-{}".format(_pstart, _pend)
            jyear = self.data.inspire_record_json["metadata"]["publication_info"][0]["year"]
            _journal_info = f"{jname} {jvol} {jartid} ({jyear})"
        except:
            pass

        try:
            jname = self.data.inspire_record_json["metadata"]["publication_info"][0]["journal_title"]
            jvol = self.data.inspire_record_json["metadata"]["publication_info"][0]["journal_volume"]
            _pstart = self.data.inspire_record_json["metadata"]["publication_info"][0]["page_start"]
            _jartid = self.data.inspire_record_json["metadata"]["publication_info"][0]["artid"]
            jartid = "{} p.{}".format(_jartid, _pstart)
            if _jartid:
                # ignore the page info (usually page not needed)
                jartid = _jartid
            else:
                jartid = "p.{}".format(_pstart)
            jyear = self.data.inspire_record_json["metadata"]["publication_info"][0]["year"]
            _journal_info = f"{jname} {jvol} {jartid} ({jyear})"
        except:
            pass

        if _journal_info is None:
            try:
                _journal_info = self.data.inspire_record_json["metadata"]["publication_info"][0][
                    "pubinfo_freetext"
                ]
            except:
                pass
        if _journal_info is None:
            _journal_info = "n/a"
        self.data.journal_info = _journal_info

    def get_extra_info(self, what):
        val = None
        try:
            # val = self.data.extra_info.split('{}='.format(what))[1].split(' ')[0]
            for v in self.data.extra_info.split():
                if f"{what}=" == v[: len(what) + 1]:
                    val = v[len(what) + 1 :]
        except:
            pass
        return val

    def inspire_id_from_arxiv(self):
        if self.data.arxiv_id is None:
            print(f'[e] no arxiv id ? {self.data.arxiv_id}')
            return None
        self.data.url_insp_search_abs_id = "https://inspirehep.net/api/literature?sort=mostrecent&size=1&page=1&q=find%20eprint%20{}".format(
            self.data.arxiv_id
        )
        self.data.inspire_record = self.query(self.data.url_insp_search_abs_id)
        self.data.arxiv2inspire_failed = 0
        try:
            self.data.inspire_id = self.data.inspire_record["hits"]["hits"][0]["id"]
            self.data.url_json = self.data.inspire_record["hits"]["hits"][0]["links"]["json"]
        except:
            self.data.arxiv2inspire_failed = 1

        if self.data.arxiv2inspire_failed == 1:
            if self.get_extra_info("inspire_id"):
                self.data.inspire_id = self.get_extra_info("inspire_id")
                self.data.api_url_record = "https://inspirehep.net/api/literature/{}".format(self.data.inspire_id)
                self.data.url_json = self.data.api_url_record + "?format=json"
            else:
                self.data.arxiv2inspire_failed = 2

        if self.data.arxiv2inspire_failed == 2:
            self.data.url_insp_arxiv_api = f'https://inspirehep.net/api/arxiv/{self.data.arxiv_id}'
            self.data.inspire_record = self.query(self.data.url_insp_arxiv_api)
            try:
                self.data.inspire_id = self.data.inspire_record["hits"]["hits"][0]["id"]
                self.data.url_json = self.data.inspire_record["hits"]["hits"][0]["links"]["json"]
            except:
                self.data.arxiv2inspire_failed = 3

        if self.data.arxiv2inspire_failed == 3:
            self.data.inspire_not_found = True
            return None
        return self.data.inspire_id

    def retrieve(self):
        if self.data.inspire_id is None:
            self.data.inspire_id = self.inspire_id_from_arxiv()
            if self.data.inspire_id is None:
                print(f'[e] no inspire id found for [{self.data.arxiv_id}]')
                self.is_valid = False
                return None
        self.data.url_record = "https://inspirehep.net/literature/{}".format(self.data.inspire_id)
        if self.data.url_inspire is None:
            self.data.url_inspire = self.data.url_record
        self.data.api_url_record = "https://inspirehep.net/api/literature/{}".format(self.data.inspire_id)
        self.data.url_json = self.data.api_url_record + "?format=json"
        self.data.inspire_record_json = self.query(self.data.url_json)
        # from here on one can use self.q('something.subsomething)
        self.data.url_latex_us = self.q("links.latex-us")
        self.data.latex_us = self.query(self.data.url_latex_us, parse_json=False)  # .decode("utf-8") # this should be TEXT not json!
        if isinstance(self.data.latex_us, bytes):
            self.data.latex_us = self.data.latex_us.decode('utf-8')        
        self.data.url_bibtex = self.q("links.bibtex")
        self.data.bibtex = self.query(self.data.url_bibtex, parse_json=False)  # .decode("utf-8") # this should be TEXT not json!
        if isinstance(self.data.bibtex, bytes):
            self.data.bibtex = self.data.bibtex.decode('utf-8')        

        # self.data.doi = self.inspire_record_json["metadata"]["dois"][0]["value"]
        self.data.doi = self.q("metadata.dois.0.value")
        if self.data.doi:
            self.data.url_doi = "https://doi.org/{}".format(self.data.doi)
        else:
            self.data.url_doi = (
                self.data.url_record
            )  # this might be unexpected - check doi first
        self.decode_journal_string()
        self.data.arxiv_id_check = self.q("metadata.arxiv_eprints.0.value")
        if self.data_arxiv_id is None:
            self.data.arxiv_id = self.data.arxiv_id_check
        if self.data_arxiv_id != self.data_arxiv_id_check:
            print('[w] arxiv id off?', self.data_arxiv_id, self.data.arxiv_id_check)
            self.data.arxiv_id = self.data.arxiv_id_check
        self.data.preprint_date = self.q("metadata.preprint_date")
        self.data.pub_date = self.q("metadata.imprints.0.date")
        self.data.created_date = self.q("created")
        self.data.created_date_noT = str(self.q("created")).split("T")[0]
        self.data.updated_date = self.q("updated")
        self.data.legacy_creation_date = self.q("metadata.legacy_creation_date")
        for d in [
            self.data_preprint_date,
            self.data.created_date_noT,
            self.data.legacy_creation_date,
            "1977-11-16",
        ]:
            if d:
                self.data.date_guess = d
                break

        self.data.citation_count_wsc = self.q(
            "metadata.citation_count_without_self_citations"
        )
        self.data.citation_count = self.q("metadata.citation_count")

        self.data.refers_to = self.query(
            f"https://inspirehep.net/api/literature?q=refersto:recid:{self.data.inspire_id}"
        )
        self.data.refers_to_count = self.data.refers_to["hits"]["total"]

        try:
            self.data.title = self.data.inspire_record_json["metadata"]["titles"][0]["title"]
        except:
            self.data.title = "* Failed title parsing *"
            self.is_valid = False
        try:
            self.data.url_arxiv = f"https://arxiv.org/abs/{self.data.arxiv_id}"
            ## this is a check - trusting this works (tested!)
            # feedr = self.read_url_data(self.url_arxiv)
            # if feedr is None:
            # 	self.url_arxiv = None
        except:
            pass
        self.data.citeable = self.q("metadata.citeable")

    def int_or_string(self, s):
        if s.isnumeric():
            return int(s)
        return s

    # short for query json
    def q(self, what):
        try:
            _val = self.data.inspire_record_json
            for e in what.split("."):
                _val = _val[self.int_or_string(e)]
        except:
            return None
        return _val

    def query(self, url_inspire, parse_json=True, update=False):
        if self.verbose:
            print("[i] query string", url_inspire)
        retval = None
        if self.update or update:
            try:
                if self.verbose:
                    print("[i] fetching data from the web")
                feedr = urllib.request.urlopen(url_inspire).read()
                self.read_from_web = True
            except urllib.error.URLError as e:
                print(
                    "[e] unable to read from the web - link tried",
                    url_inspire,
                    file=sys.stderr,
                )
                print(" . ", e)
                return None
            except http.client.IncompleteRead as e:
                _part = e.partial
                print("[e] got incomplete read from", url_inspire, file=sys.stderr)
                print("    trying one more time...", file=sys.stderr)
                try:
                    feedr = urllib.request.urlopen(url_inspire).read()
                except:
                    print("   failed. skipping.", file=sys.stderr)
                    return None
            except http.client.RemoteDisconnected as e:
                print("[e] got disconnected while", url_inspire, file=sys.stderr)
                print("    trying one more time...", file=sys.stderr)
                try:
                    feedr = urllib.request.urlopen(url_inspire).read()
                except:
                    print("   failed. skipping.", file=sys.stderr)
                    return None
            self.cache.save_query(url_inspire=url_inspire, feedr=feedr)
            if parse_json:
                retval = json.loads(feedr)
            else:
                retval = feedr
            return retval
        else:
            feedr = self.cache.read_query(url_inspire=url_inspire)
            if feedr:
                if parse_json:
                    retval = json.loads(feedr)
                else:
                    retval = feedr
                return retval
            else:
                return self.query(url_inspire, parse_json=parse_json, update=True)

    def protect_latex(self):
        if self.data.title is None:
            print(self.data)
        self.data.title = self.data.title.replace("{{", "{ {")  # jekyll...
        self.data.title = self.data.title.replace("|", "\\|")  # md table...

# --- record.py

class Record(GenericObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def basic_dict(self):
        data = {
            "id": self.id,
            "source": self.source
        }
        return data

    def write_yaml(self, filename):
        data = {
            "id": self.id,
            "source": self.source,
            "note": self.note,
            "PI": self.PI,
        }
        with open(filename, "w") as f:
            yaml.dump(data, f)

    def read_yaml(self, filename):
        with open(filename, "r") as f:
            data = yaml.load(f)
        self.init_from_dict(data)

# --- records_db.py

class RecordsDB(GenericObject):

    def __init__(self, filename, **kwargs):
        super().__init__(**kwargs)
        self.filename = filename
        if self.verbose:
            print("[i] reading from", filename)
        self.records = []
        self.arxiv_list = []
        self.inspire_list = []
        self.read_yaml(filename)
        self.process()

    def process(self):
        if self.records:
            for p in self.records:
                if p["source"].lower().startswith("arxiv"):
                    self.arxiv_list.append("{}".format(p["id"]))
                if p["source"].lower().startswith("inspire"):
                    self.inspire_list.append("{}".format(p["id"]))
        self.prescan_with_threading()

    def read_yaml(self, filename):
        _tmp_records = GenericObject(init_yaml=filename)
        if _tmp_records.records:
            for _r in _tmp_records.records:
                self.records.append(Record(init_dict=_r))

    @staticmethod
    def get_record_thread(record, args):
        _ = InspireRecord(from_record=record, update=args.download, verbose=args.debug)

    @staticmethod
    def count_threads_alive(threads):
        _count = len([thr for thr in threads if thr.is_alive()])
        return _count

    def prescan_with_threading(self):
        threads = list()
        pbar = tqdm.tqdm(self.records, desc="prescanning records (downloading if needed or requested)")
        for record in self.records:
            x = threading.Thread(
                target=RecordsDB.get_record_thread,
                args=(
                    record,
                    self.args,
                ),
            )
            threads.append(x)
            x.start()
            pbar.update(1)
            while RecordsDB.count_threads_alive(threads) >= multiprocessing.cpu_count() * 2:
                _ = [thr.join(0.1) for thr in threads if thr.is_alive()]
        pbar.close()

# --- utils.py

def starting_record_from_string(sid):
    _r = Record()
    if 'arxiv' in sid or 'inspire' in sid:
        if 'arxiv' in sid:
            _r.id = sid.split('/')[-1]
            if '.' not in _r.id:
                _r.id = sid.replace('https://arxiv.org/abs/', '')
            _r.source = 'arxiv'
        elif 'inspire' in sid:
            _r.id = sid.split('/')[-1]
            _r.source = 'inspire'
    else:
        if '/' in sid:
            _r.id = sid.replace('https://arxiv.org/abs/', '')
            _r.source = 'arxiv'
        else:
            if '.' in sid:
                _r.id = sid
                _r.source = 'arxiv'
            else:
                _r.id = sid
                _r.source = 'inspire'
    return _r

def get_record_thread(record, args):
    _ = InspireRecord(from_record=record, update=args.download, verbose=args.debug)


def prescan_with_threading_nothread_limit(records, args):
    threads = list()
    for record in tqdm.tqdm(records, desc="threads start"):
        x = threading.Thread(
            target=get_record_thread,
            args=(
                record,
                args,
            ),
        )
        threads.append(x)
        x.start()
    for thr in tqdm.tqdm(threads, desc="completed"):
        thr.join()


def count_threads_alive(threads):
    _count = len([thr for thr in threads if thr.is_alive()])
    return _count


def prescan_with_threading(records, args):
    threads = list()
    pbar = tqdm.tqdm(records, desc="threads")
    for record in records:
        x = threading.Thread(
            target=get_record_thread,
            args=(
                record,
                args,
            ),
        )
        threads.append(x)
        x.start()
        pbar.update(1)
        while count_threads_alive(threads) >= multiprocessing.cpu_count() * 2:
            _ = [thr.join(0.1) for thr in threads if thr.is_alive()]
    pbar.close()


def formatted_output(sformat, rd):
    regex = r"{\.[a-zA-Z0-9_]+}*"
    matches = re.finditer(regex, sformat, re.MULTILINE)
    for m in matches:
        _tag = m.group(0).split(".")[1].strip("}")
        _val = rd[_tag]
        # print(isinstance(_val, str), type(_val))
        if isinstance(_val, str):
            _val = _val
            # print('string instance -*-', type(_val))
        else:
            # print('NOT string instance -*-', type(_val))
            if isinstance(_val, bytes):
                _val = _val.decode()
            else:
                _val = str(_val)
        sformat = sformat.replace(m.group(0), _val)
    # print('->>>', sformat)
    return sformat


def sorted_arxiv(records):
    _old = []
    _new = []
    for a in records:
        if "/" in a.split()[0]:
            _old.append(a)
        else:
            _new.append(a)
    out = []
    _new = sorted(_new, reverse=True)
    _old = sorted(_old, reverse=True)
    for a in _new:
        out.append(a)
    for a in _old:
        out.append(a)
    return out


def sorted_with_inspire_date(records):
    return sorted(records, key=lambda x: x.data.created_date, reverse=True)


def sorted_with_preprint_date(records):
    return sorted(records, key=lambda x: x.data.preprint_date, reverse=True)


def str_to_record_dict(s):
    pairs = re.findall(r'(\w+)=([\w\.]+)', s)
    d = {key: f'{value}' for key, value in pairs}
    return d


def rewrite_text_to_yaml(filename, assume_id='arxiv_id'):
    _d = dict()
    _d['records'] = []
    with open(filename, "r") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        line = line.split(' ')[0]
        if len(line) < 1:
            continue
        _rtmp = starting_record_from_string(line.strip())
        _d['records'].append(_rtmp.basic_dict())
    foutputname = filename + ".yaml"
    with open(foutputname, "w") as f:
        yaml.dump(_d, f)
    return foutputname

# --- main.py

def main():
    parser = argparse.ArgumentParser(description='test getting informaion from inspire', prog=os.path.basename(__file__))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--absid', help="arXiv absid", type=str)
    group.add_argument("--iid", help="INSPIRE id", type=str)
    group.add_argument("-f", "--file", help="file with arXiv absids", type=str)
    parser.add_argument('-d', '--download', help="ignore local copy if exists", action='store_true')
    parser.add_argument('-l', '--latex', help='print latex strings', action='store_true', default=False)
    parser.add_argument('-m', '--md', help='print md strings', action='store_true', default=True)
    parser.add_argument('-g', '--debug', help='print some extra info', action='store_true', default=False)
    parser.add_argument('-j', '--debug-json', help='print json', action='store_true', default=False)
    parser.add_argument('-i', '--debug-json-iter', help='print json', action='store_true', default=False)
    parser.add_argument('-x', '--query-json', help='print stuff from json', type=str, default='')
    parser.add_argument('--format', help='specify format for output using .property to InspireRecordData - example csv: {.absid},{.id},{.preprint_date},{.pub_date},\"{.title}\"', type=str, default='')
    parser.add_argument('-o', '--output', help='output file for formatter output', type=str, default='')
    parser.add_argument('--protect-latex', help='modify latex text - protection for jekyll for example', action='store_true', default=False)

    args = parser.parse_args()

    global gDebug
    gDebug = args.debug
    if gDebug:
        print('[i] debug mode on')

    records = []
    if args.absid:
        # record = InspireRecord(from_string = f'{args.absid}', update=args.download, verbose=args.debug)
        _r = starting_record_from_string(args.absid)
        record = InspireRecord(from_record = _r, update=args.download, verbose=args.debug)
        records.append(record)

    if args.iid:
        # _r = Record(id=f"{args.iid}", source="INSPIRE", note="test", PI="test")
        _r = starting_record_from_string(args.iid)
        record = InspireRecord(from_record = _r, update=args.download, verbose=args.debug)
        records.append(record)

    ids_all = []
    ids_duplicates = []
    db = None
    if args.file:
        # if file extension is .txt, convert to .yaml
        # if args.file.endswith('.txt'):
        if not args.file.endswith('.yaml'):
            args.file = rewrite_text_to_yaml(args.file)
        db = RecordsDB(args.file, args=args, verbose=args.debug)
        for _r in tqdm.tqdm(db.records, desc='reading records'):
            # don't update - done in multithreaded prescan...
            record = InspireRecord(from_record = _r, update=False, verbose=args.debug)
            if record.is_valid is False:
                continue
            if record.data.inspire_not_found is True:
                print('warning] no entry for: {_r}.", file=sys.stderr')
                pass
            else:
                if args.protect_latex:
                    record.protect_latex()
                aid = record.data.arxiv_id
                if aid == 'n/a':
                    aid = record.data.inspire_id
                if aid and aid in ids_all:
                    ids_duplicates.append(aid)
                else:
                    ids_all.append(aid)
                    records.append(record)
    # print(db)

    header = 0
    # for record in sorted_with_inspire_date(records=records):
    fout = sys.stdout
    if args.output:
        fout = open(args.output, 'w')
    for record in sorted_with_preprint_date(records=records):
        if record is None:
            continue
        if args.format:
            _s = formatted_output(args.format, record.data)
            if header == 0:
                header = 1
                print(args.format.replace(".", "").replace("{", "").replace("}", ""), file=fout)
            print(_s, file=fout)
            continue
        if args.debug_json:
            print(json.dumps(record.record_json, indent=2))
            continue
        if args.query_json:
            _squery = args.query_json
            _subquery = None
            do_iter = args.debug_json_iter
            if args.query_json == ".":
                _x = record.record_json
            else:
                if '@' in args.query_json:
                    _squery = args.query_json.split('@')[0]
                    _subquery = args.query_json.split('@')[1]
                    do_iter = True
                _x = record.q(_squery)
            if do_iter:
                print("[x]", args.query_json)
                if type(_x) is str:
                    print("    =", _x)
                else:
                    try:
                        for _i, _e in enumerate(_x):
                            if type(_e) is dict and _subquery:
                                print(' ', _i, json.dumps(_e[_subquery], indent=2))
                            else:
                                print(' ', _i, type(_e), _e)
                    except:
                        print("    =", _x)
            else:
                print(
                    "[x]",
                    args.query_json,
                    "=",
                    json.dumps(record.q(args.query_json), indent=2),
                )
            continue
        print(record.data)
    if args.output:
        fout.close()

    if len(ids_duplicates) > 0:
        for aid in ids_duplicates:
            print(f"[warning] absid: {aid} duplicated in the input.", file=sys.stderr)


if __name__=="__main__":
    main()
