# -*- coding: utf-8 -*-
from marc21 import *
from marc_data import *
import re
import sys
import json
from collections import defaultdict

def listify(x):
    if type(x) == type([]):
        return x
    return [x]

def valueof(c):
    v = {'M':1000, 'C':100, 'V':5, 'I':1, 'X':10, 'D':500, 'L':50,
         'm':1000, 'c':100, 'v':5, 'i':1, 'x':10, 'd':500, 'l':50}
    return v.get(c, 0)

## given an integer or roman numeral (!), return the integer.
def pagenum(s):
  i = safeint(s)
  if i: return i
  if len(s) == 1:
      return valueof(s)
  tmp = 0
  ret = 0
  last = valueof(s[0])
  if valueof(s[1]) >= last:
    tmp = last
  else:
    ret = last
  for c in s[1:]:
      v = valueof(c)
      if v > last:
        ret += v - tmp
        tmp = 0
      else:
        tmp += v
      last = v
  return ret + tmp

## The 008 record is a terribly cryptic positional (!) field,
## containing lots of useful data like language and pub date.
## funnily enough, some of the field's meanings change with
## the type of record (book, music, etc) but the type is
## not recorded therein.
def parse008(s):
    global country_codes, language_codes

    year = s[0:2]
    month = s[2:4]
    day = s[4:6] #yymmdd, for maximum confusion.
    if len(s) < 7:
        return {}
    date_type =  s[6] # how confident are we? 12 choices.
    ## todo, "continuing resources" dates.
    if date_type in ('s', '|', 't'):
        year = s[7:11]
    else: # Assume window of 1940.
        if safeint(year) < 40:
            year = '20'+year
        else:
            year = '19'+year

    country = country_codes.get(s[15:18].strip(), 'unknown')
    lang = language_codes.get(s[35:38].strip(), 'unknown')
    return {
        'pub_date': '-'.join((year, month, day)),
        'country': country,
        'lang': lang,
    }

def parse008_music(code):
    global music_forms, music_score
    ret = {}
    if len(code) < 21: return
    if music_forms.get(code[18:20]):
        ret['music_form'] = music_forms[code[18:20]]
    if music_score.get(code[20]):
        ret['music_score'] = music_score[code[20]]

    # if score-type is "not applicable", it's a recording.
    if code[20] == 'n':
        ret['type'] = 'audio'

    return ret

# guess at the type of the item being described, and add relevant
# metadata from codes. This is derived from careful reading of the
# spec (confusing), and examintion of how Harvard's data conforms to
# the spec (wrongly, but consistently wrongly).
#
# types:
#   video
#   audio
#   score (music)
#   book
#   map
#   periodical
#   url
#   excerpt
#   pamphlet
#   illustrations
def guess_type(r):
    global video_techniques
    ret = {'type': 'unknown'}

    physical_desc = str(r.get('physical_desc', ''))
    physical_desc_2 = str(r.get('physical_desc_2', ''))

    # definitive and mostly complete.
    # todo: "online reasources"
    if r['r008'][29:34] == '    v' or re.search(r'video', physical_desc):
        ret['type'] = 'video'
        if video_techniques.get(r['r008'][35]):
            ret['video_technique'] = video_techniques.get(r['r008'][35])

    # definitive, but not complete.
    # todo: topo info
    if r['r008'][25:29] == 'a   s':
        ret['type'] = 'map'

    if physical_desc.find('sound disc') > -1:
        ret['type'] = 'audio'

    if r.get('issn'):
        ret['type'] = 'periodical'

    ## Detect books by page count notation in the desecription.
    ## yes, some page counts are in Roman numerals (!!)
    m = re.search(r'\[?(\d+|[cxvi]+)\]?\s*p\b', physical_desc)
    if m:
        ret['type'] = 'book'
        ret['page_count'] = pagenum(m.group(1))

    # excepts have this format: "p. [241]-269"
    m = re.search(r'p?p\.?\s*\[?(\d+)\]?-\[?(\d+)\]?', physical_desc)
    if m:
        ret['type'] = 'excerpt'
        ret['page_count'] = safeint(m.group(2)) - pagenum(m.group(1))

    # "2 v." means two volumes
    m = re.search(r'(\d+)\s*(?:v\.?|parts|volume|vol)\b', physical_desc)
    if m:
        ret['type'] = 'book'

    # various ways to describe pages/sheets/leaves
    m = re.search(r'\[?\d+\]? (?:double|sheet|folded sheet|fold|leaf|leaves|plate|pamphlet|\xe2\x84\x93|\u2113)|Broadside|broadside|\bv\.', physical_desc)
    if m:
        ret['type'] = 'pamphlet'

    # ...except illustrations.
    m = re.search(r'ill\.|illus|sketch|plan|poster|diagr', physical_desc_2)
    if m:
        ret['type'] = 'book'

    m = re.search(r'(\d+)(?: map|maps)\b|maps', physical_desc)
    if m:
        ret['type'] = 'map'

    # very good chance it's music.
    if r.get('lang') == 'No linguistic content' or re.search(r'(?:sound|audio) disc', physical_desc):
        ret['type'] = 'music'
        ret.update(parse008_music(r['r008']))
        #print >> sys.stderr, ret


    if ret['type'] == 'unknown':
        pass # print >> sys.stderr, r

    return ret

## http://www.loc.gov/marc/bibliographic/ecbdorg.html
## ID of this record in a third, non-national system.
# eg, ocm62408612 -> Cincinnati Masonic Temple, book 62408612
def parse035a(s):
    pass

def marc2dict(record, debug=False):
    ret = {}
    if not record: return ret
    for field in sorted(record.fields()):
        for line in listify(record[field]):
            if isControlField(field):
                if debug:
                    print field, line
                ret[field] = stripper(line)
            else:
                for subfield in sorted(line.subfields()):
                    ret[field+subfield] = ret.get(field+subfield, [])
                    for line2 in listify(line[subfield]):
                        if debug:
                            print field, subfield, line2
                        ret[field+subfield].append(stripper(line2))
    return ret

## removes trailing whitepace and punctuation
def stripper(s):
    return re.sub(r'\s*[\:\-\;\,\/\=\.]*$', '', s)


fieldmap = {
    '008': 'r008',
    '001': 'id',
    '005': 'update_date',
    '020a': 'isbn',
    '022a': 'issn',
    '245a': 'title',
    '245b': 'subtitle',
    '246a': 'alt_title',
    '210a': 'title_abbr',
    '222a': 'issn_title',
    '100a': 'author',
    '100d': 'author_dates',
    '700a': 'author2',
    '700d': 'author2_dates',
    '710a': 'corporate_name',
    '260b': 'publisher',
    '260a': 'place_of_pub',
    '250a': 'edition',
    '0822': 'edition_num',
    '260e': 'place_of_manufacture',
    '260f': 'manufacturer_name',
    '260g': 'manufacture_date',
    '245c': 'responsibility_statement',
    '010a': 'loc_code',
    '016a': 'natl_lib_code',
    '035a': 'system_control_number',
    '020c': 'price_availability',
    '020z': 'invalid_isbn',
    '050a': 'loc_class_num',
    '050b': 'loc_item_num',
    '040a': 'catalog_source',
    '040c': 'transcribing_agency',
    '040c': 'modifying_agency',
    '988a': 'catalog_date',     # dates before June 2002 are bogus :(
    '9060': 'governing_source',
    '300a': 'physical_desc',
    '300b': 'physical_desc_2',
    '300c': 'physical_dimensions',
    '650a': 'topical_terms',
    '650b': 'topical_terms_2',
    '651a': 'geo_name',
    '650z': 'geo_subdivision',
    '650x': 'general_subdivision',
    '651x': 'geo_general_subdivision',
    '650x': 'form_subdivision',
    '655a': 'genre',
    '504a': 'bibliography',
    '500a': 'general_note',
    '043a': 'geo_area_code',  ## needs parsing.
    '042a': 'auth_code',      # http://www.loc.gov/standards/valuelist/marcauthen.html
    '082a': 'dewey_decimal',
    '440a': 'series',         # NOT defined in MARC21, but useful
    '490a': 'series2',        # MARC "series statement"
    '600a': 'subject_personal_name',  # eg, person that the bio is about
#    '049a': '049a',           #NOT defined in MARC21
    '090a': 'local_call_number', ## impl. specific, undefined.
    '880a': 'alt_glyph_a',  # eg, chinese glyphs of book title. link ref field.
    '880b': 'alt_glyph_b',
    '880c': 'alt_glyph_c',
    '880d': 'alt_glyph_d',
    '8806': 'alt_glyph_link_ref', # fields refered to by 880a
    '856a': 'url_host',
    '856d': 'url_path',
}

field_counts = defaultdict((lambda: 0))
fields = sorted(fieldmap.values() + [
    'pub_date',
    'country',
    'lang',
    'type',
    'video_technique',
    'page_count',
    'music_form',
    'music_score'
])


def process_file(f, lim=2000000):
    data = MARC21File(f)
    for i in range(lim):
        if i and i % 1000 == 0:
            print >> sys.stderr, i, 'records'
        m = data.next()
        if not m: return
        marc = marc2dict(m)

        for k in marc:
            field_counts[k] +=1

        if '008' not in marc:
            print >> sys.stderr, '008 record not found', marc
            continue

        record = parse008(marc['008'])

        for k,v in fieldmap.iteritems():
            if marc.get(k):
                record[v] = marc[k]

        record.update(guess_type(record))
        yield record




files = [
    'data/HLOM/ab.bib.00.20120331.full.mrc',
    'data/HLOM/ab.bib.01.20120331.full.mrc',
    'data/HLOM/ab.bib.02.20120331.full.mrc',
    'data/HLOM/ab.bib.03.20120331.full.mrc',
    'data/HLOM/ab.bib.04.20120331.full.mrc',
    'data/HLOM/ab.bib.05.20120331.full.mrc',
    'data/HLOM/ab.bib.06.20120331.full.mrc',
    'data/HLOM/ab.bib.07.20120331.full.mrc',
    'data/HLOM/ab.bib.08.20120331.full.mrc',
    'data/HLOM/ab.bib.09.20120331.full.mrc',
    'data/HLOM/ab.bib.10.20120331.full.mrc',
    'data/HLOM/ab.bib.11.20120331.full.mrc',
    'data/HLOM/ab.bib.12.20120331.full.mrc',
    'data/HLOM/ab.bib.13.20120331.full.mrc',
]

if __name__ == '__main__':

    if sys.argv[1] == 'sql':
        print 'drop table harvard;'
        print 'create table harvard ('
        print ','.join(['%s varchar(255)' % f for f in fields])
        print ');'
        for f in files:
            for record in process_file(f):
                sql = "insert into harvard values('"
                sql += "','".join([str(record.get(k, '')).replace("'", r"''") for k in fields])
                sql += "');"
                print sql

    elif sys.argv[1] == 'json':
        for f in files:
            for record in process_file(f):
                print json.dumps(record) + '\n'
