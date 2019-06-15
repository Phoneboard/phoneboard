#!/usr/bin/env python3

########################################################################
#
# Copyright 2019 Crazor <crazor@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
########################################################################

import argparse
import fitz
from fitz import Point
import re


def main():
    parser = argparse.ArgumentParser(
        description='Process iPhone schematic PDFs')
    parser.add_argument('infile',
                        metavar='INPUT',
                        type=argparse.FileType('rb'),
                        help='The PDF file name to process')
    parser.add_argument('outfile',
                        metavar='OUTPUT',
                        help='The file name to write the processed PDF to')
    parser.add_argument('--drop',
                        action='append',
                        help='A range of pages to drop, e.g. 1 or 1,3,7 or 1,5-14. Can be specified multiple times.')
    parser.add_argument('--strip-annotations',
                        action='store_true',
                        help='Remove annotations')
    parser.add_argument('--toc',
                        action='store_true',
                        help='Build table of contents')
    parser.add_argument('--nostuff',
                        action='store_true',
                        help='Output a list of designators marked NOSTUFF')
    parser.add_argument('--debug',
                        action='store_true',
                        help='Add visual debugging information to output file')
    args = parser.parse_args()

    document = fitz.open('PDF', args.infile.read())

    if args.drop is not None:
        remove_pages(document, args.drop)
    if args.strip_annotations:
        remove_annotations(document)
    if args.toc:
        build_toc(document)
    if args.nostuff:
        list_nostuffs(document, args.debug)
    document.save(args.outfile)
    args.infile.close()


def remove_pages(document, drop_list):
    dropped = 0
    for drop in drop_list:
        for range in drop.split(','):
            if '-' in range:
                beginning, end = range.split('-')
                beginning, end = int(beginning), int(end)
                print(f'Dropping page {beginning} to {end}')
                document.deletePageRange(beginning-dropped-1, end-dropped-1)
                dropped += end-beginning
            else:
                print(f'Dropping page {range}')
                document.deletePage(int(range)-dropped-1)
                dropped += 1
    print(f'Dropped {dropped} pages.')


def remove_annotations(document):
    for page_number in range(0, document.pageCount):
        page = document[page_number]
        if page.firstAnnot is not None:
            page.deleteAnnot(page.firstAnnot)


def build_toc(document):
    toc = []
    current_chapter = ''
    for page_number in range(0, document.pageCount):
        page = document[page_number]
        text = page.getText(output='dict')
        # Find the largest text on the page:
        max_size = 0
        max_text = ''
        for b in text['blocks']:
            if b['type'] is 0:
                for l in b['lines']:
                    for s in l['spans']:
                        if s['size'] > max_size:
                            max_size = s['size']
                            max_text = s['text']
        # Strip "(1 of 2)" and "(1)":
        match = re.search(r'(.*) (?:\((\d) OF (\d)\)|\((\d)\))', max_text)
        if match:
            if match.groups()[1] == '1' or match.groups()[3] == '1':
                toc.append([1, match.groups()[0], page_number+1])
        # Split titles like "FIJI: (...)" into chapters
        elif ':' in max_text:
            chapter, topic = max_text.split(':')
            if chapter != current_chapter:
                toc.append([1, chapter, page_number+1])
                current_chapter = chapter
            toc.append([2, topic, page_number+1])
        else:
            if max_text != current_chapter:
                toc.append([1, max_text, page_number+1])
                current_chapter = max_text
    # Update the ToC
    document.setToC(toc)


def list_nostuffs(document, debug=False):
    nostuffs = []
    designators = []

    for page_number in range(0, document.pageCount):
        page = document[page_number]
        for word in page.getTextWords():
            if 'NOSTUFF' in word[4]:
                box = word[0:4]
                if debug:
                    document[page_number].drawRect(box,
                                                 fitz.utils.getColor("orange"))
                center = Point((box[0] + box[2])/2, (box[1] + box[3])/2)
                nostuffs.append({'page': page_number,
                                 'box': box,
                                 'center': center,
                                 'designators': []})

            if re.match(r'([CDFJLQRUVWXYZ]{1,2}\d{4}|(U|FL|F|T)\w+(RF|TX))',
                        word[4]):
                # Missing: U_QPOET, U_LBPAD, U_VLBPAD, U_LB_SW, U_VLB_SW,
                # U_MBPAD FL_B17LP, FL_B39LP, FT40A41A, FT_B40,
                # SAW-BAND-41B-41C-TDD-TX, FRX34B39, FR40A41A, FR38X40B,
                # *_COAX, U_GPSLNA, UAT_METR, *_ANT, *_CN
                # False positive: UART_TX
                box = word[0:4]
                if debug:
                    document[page_number].drawRect(box,
                                                   fitz.utils.getColor("green"))
                center = Point((box[0] + box[2])/2, (box[1] + box[3])/2)
                designators.append({'name': word[4],
                                    'page': page_number,
                                    'box': box,
                                    'center': center})

    for n in nostuffs:
        for d in designators:
            if d['page'] is n['page']:
                d['distance'] = d['center'].distance_to(n['center'])
                n['designators'].append(d)
        n['designators'] = sorted(n['designators'],
                                  key=lambda k: k['distance'])
        if debug:
            document[n['page']].drawLine(n['center'],
                                        n['designators'][0]['center'],
                                        fitz.utils.getColor("orange"))
        # Problematic matches in iPhone 6 schematic: R0943, R0944, XW1610, C4512, R5502

    for n in nostuffs:
        print(n['designators'][0]['name'])


main()
