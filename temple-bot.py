"""
//  Copyright (c) 2015 Keith McQueen
//
//  Permission is hereby granted, free of charge, to any person obtaining a copy
//  of this software and associated documentation files (the "Software"), to deal
//  in the Software without restriction, including without limitation the rights
//  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
//  copies of the Software, and to permit persons to whom the Software is
//  furnished to do so, subject to the following conditions:
//
//  The above copyright notice and this permission notice shall be included in
//  all copies or substantial portions of the Software.
//
//  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
//  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
//  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
//  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
//  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
//  THE SOFTWARE.
"""

import argparse
import json
from bs4 import BeautifulSoup
import requests

TEMPLES_KML_URL = 'http://www.ldschurchtemples.com/maps/downloads/kml.php'
TEMPLES_CSV_URL = 'http://www.ldschurchtemples.com/maps/downloads/gps.php'
TEMPLES_LDS_DOT_ORG_URL = 'http://www.lds.org/church/temples/find-a-temple?lang=eng'
TEMPLES_MEDIA_URL = 'https://www.lds.org/media-library/images/categories/temples_list?lang=eng'

TEMPLE_NAME_SUBSTITUTIONS = [
    (' Temple', ''),
    ('Kinshasa Democratic Republic of the Congo', 'Kinshasa Democratic Republic of Congo')
]


class TempleBot:
    def __init__(self, export_file_path, export_num_rows):
        self.temples = {}
        self.temple_images = []
        self.json_file_path = export_file_path
        self.num_rows = export_num_rows

    def load(self):
        # start with data from lds.org
        self.load_temples_from_lds_dot_org()

        # load images from lds.org/media-library
        print # blank line
        self.load_temple_images()

        # add geolocation data from ldschurchtemples.com
        print # blank line
        self.load_temples_from_kml()

    def export(self):
        with open(self.json_file_path, 'w') as output:
            json.dump(self.temples, output)

    def load_temples_from_kml(self):
        # get the Temple data from the .kml file
        soup = self.load_data_from(TEMPLES_KML_URL, log_str='Getting temple geolocation data from {}')

        # print temples_kml_soup.prettify()
        for placemark in soup.find_all('placemark'):
            if 0 < self.num_rows <= len(self.temples):
                break

            temple_obj = {
                'name': self.cleanse_name(placemark.find('name').string),
                'latitude': float(placemark.find('latitude').string),
                'longitude': float(placemark.find('longitude').string)
            }
            self.update_temple(temple_obj, add_if_not_found=False)

    def load_temples_from_lds_dot_org(self):
        soup = self.load_data_from(TEMPLES_LDS_DOT_ORG_URL, log_str='Getting primary temple list from {}')

        # get the temple links
        for temple_row in soup.select('#temple-list-sortable tr'):
            if 0 < self.num_rows <= len(self.temples):
                break

            temple_cells = temple_row.find_all('td')
            if len(temple_cells) != 3:
                raise "Wrong number of data cells in temple row: expected {}, got {}".format(3, len(temple_cells))

            temple_anchor = temple_cells[0].find('a')
            temple_loc = temple_cells[1].string.split(', ')
            temple_dedication = temple_cells[2].string

            temple = {
                'name': self.cleanse_name(temple_anchor.string),
                'url': temple_anchor['href'],
                'dedicated': temple_dedication,
                'city': temple_loc[1] if len(temple_loc) > 1 else '',
                'state': temple_loc[2] if len(temple_loc) > 2 else '',
                'country': temple_loc[0] if len(temple_loc) > 0 else ''
            }

            print # blank line
            self.update_temple(temple)

            self.load_temple_details(temple)

    def load_temple_details(self, temple_obj):
        if temple_obj is None:
            return

        soup = self.load_data_from(temple_obj['url'], log_str="Getting temple details from {}")

        temple = {
            'images': [],
            'address': {
                'physical': [],
                'mailing': []
            },
            'telephone': {},
            'schedule': {
                'endowments': {},
                'baptistry': {}
            }
        }

        # get the main image and title
        photo_main_tabs = soup.select('.photo-main-tabs')[0]
        if photo_main_tabs is not None:
            image = photo_main_tabs.find('img')
            if image is not None:
                img = {
                    'default-url': image['src'].replace('/bc/content', 'https://www.lds.org')
                }
                temple['images'].append(img)

            title = photo_main_tabs.find('span', class_='image-title-detail')
            if title is not None:
                temple['name'] = title.string

        # get the address information
        address_section_columns = soup.select('#address-section .three-column')
        for column in address_section_columns:
            # print column
            h3 = column.find('h3')
            if h3 is not None:
                heading = h3.string
                if heading == u'Physical Address':
                    for line in column.find_all('li'):
                        temple['address']['physical'].append(line.string)
                elif heading == u'Mailing Address':
                    for line in column.find_all('li'):
                        temple['address']['mailing'].append(line.string)
                elif heading == u'Telephone':
                    for index, line in enumerate(column.find_all('li')):
                        if index == 0:
                            temple['telephone']['main'] = line.string
                        elif line.string.find('Facsimile: ') == 0:
                            temple['telephone']['fax'] = line.string.replace('Facsimile: ', '')

        # self.update_temple(temple)
        temple_obj.update(temple)

    def load_temple_images(self):
        soup = self.load_data_from(TEMPLES_MEDIA_URL, log_str='Getting temple media list from {}')

        # get the temple links
        for temple_link in soup.select('#temple-list-sortable tr td a'):
            if 0 < self.num_rows <= len(self.temple_images):
                break

            temple = {
                'name': self.cleanse_name(temple_link.string),
                'media-url': 'https://www.lds.org' + temple_link['href']
            }

            print # blank line
            print u'Adding images for {} Temple'.format(temple['name'])
            self.temple_images.append(temple)

            self.load_temple_image_details(temple)

            self.update_temple(temple)

    def load_temple_image_details(self, temple_obj):
        soup = self.load_data_from(temple_obj['media-url'], log_str='Getting temple media gallery from {}')

        temple = {
            'description': '',
            'images': []
        }

        # get the temple description
        description = soup.select('#primary p')
        if description is not None and len(description) > 0:
            temple['description'] = description[0].string

        # get the image page(s) url(s)
        for thumbnail in soup.select('.image-gallery a'):
            img_page_soup = self.load_data_from('https://www.lds.org' + thumbnail['href'],
                                                log_str='Getting temple image details from {}')

            image = {}

            img_desc = img_page_soup.select('.image-details__description p')
            if img_desc is not None and len(img_desc) > 0:
                image['description'] = img_desc[0].string

            for img_link in img_page_soup.select('.image-details__downloads a'):
                image[img_link.string.lower() + '-url'] = img_link['href']

            temple['images'].append(image)

        temple_obj.update(temple)


    def update_temple(self, other_temple, add_if_not_found=True):
        temple_name = other_temple['name']

        try:
            temple = self.temples[temple_name]
        except KeyError:
            if add_if_not_found:
                print u'Adding {} Temple'.format(temple_name)
                self.temples[temple_name] = other_temple
            else:
                print u'{} not found'.format(temple_name)
        else:
            images = []
            images.extend(temple.setdefault('images', []))
            images.extend(other_temple.setdefault('images', []))

            temple.update(other_temple)
            temple['images'] = images

    @staticmethod
    def cleanse_name(name):
        if name is None:
            return name

        for (to_be_replaced, replacement) in TEMPLE_NAME_SUBSTITUTIONS:
            name = name.replace(to_be_replaced, replacement)

        return name

    @staticmethod
    def load_data_from(url, log_str='Getting temple data from {}'):
        # print #blank line
        print log_str.format(url)

        response = requests.get(url)
        if response.status_code != 200:
            print 'Unable to get data from {}'.format(url)
            print '{}: {}'.format(response.status_code, response.reason)

        return BeautifulSoup(response.text, 'lxml')


if __name__ == '__main__':
    # create the argument parser
    parser = argparse.ArgumentParser(description='This program will extract a subset of data from a CSV '
                                                 'file and export it to a JSON file',
                                     add_help=True)

    parser.add_argument('-o', '--output',
                        help='path to output file',
                        required=True,
                        action='store')

    parser.add_argument('-n', '--num-rows',
                        help='the maximum number of rows to be exported',
                        required=False,
                        action='store',
                        type=int,
                        default=-1)

    # parse the arguments
    args = parser.parse_args()

    # get the path to the output file
    json_file_path = args.output

    # get the maximum number of rows to export
    num_rows = args.num_rows

    temples = TempleBot(export_file_path=args.output, export_num_rows=args.num_rows)
    temples.load()
    temples.export()

