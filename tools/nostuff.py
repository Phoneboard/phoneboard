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

# This script reads an iPhone schematic called nostuff.pdf
# It depends on PyMuPDF, which you can install with pip3
# A list of components that are marked as "NOSTUFF" will be printed to stdout.
# A file called debug.pdf will be produced that marks all component designators
# in green, all NOSTUFF marks in orange and has lines connecting the marks to
# the respective designators.

import fitz
from fitz import Point
import re


#print(fitz.__doc__)

doc = fitz.open('nostuff.pdf')

nostuffs = []
designators = []

for page_number in range(0, doc.pageCount):
    page = doc[page_number]
    page.deleteAnnot(page.firstAnnot)
    for word in page.getTextWords():
        if 'NOSTUFF' in word[4]:
            nostuffs.append({'page': page_number, 'box': word[0:4]})

        if re.match(r'([CDFJLQRUVWXYZ]{1,2}\d{4}|(U|FL|F|T)\w+(RF|TX))', word[4]):
            # Missing: U_QPOET, U_LBPAD, U_VLBPAD, U_LB_SW, U_VLB_SW, U_MBPAD FL_B17LP, FL_B39LP, FT40A41A, FT_B40, SAW-BAND-41B-41C-TDD-TX, FRX34B39, FR40A41A, FR38X40B, *_COAX, U_GPSLNA, UAT_METR, *_ANT, *_CN
            # False positive: UART_TX
            designators.append({'name': word[4], 'page': page_number, 'box': word[0:4]})


for d in designators:
    box = d['box']
    doc[d['page']].drawRect(box, fitz.utils.getColor("green"))
    d['center'] = Point((box[0] + box[2])/2, (box[1] + box[3])/2)


for n in nostuffs:
    box = n['box']
    doc[n['page']].drawRect(n['box'], fitz.utils.getColor("orange"))
    n['center'] = Point((box[0] + box[2])/2, (box[1] + box[3])/2)
    n['designators'] = []

    for d in designators:
        if d['page'] is n['page']:
            d['distance'] = d['center'].distance_to(n['center'])
            n['designators'].append(d)
    n['designators'] = sorted(n['designators'], key=lambda k: k['distance'])
    doc[n['page']].drawLine(n['center'], n['designators'][0]['center'], fitz.utils.getColor("orange"))
# Problematic matches in iPhone 6 schematic: R0944, XW1610, C4512, R5502

for n in nostuffs:
    print(n['designators'][0]['name'])

doc.save('debug.pdf')
