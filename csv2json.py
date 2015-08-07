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

__author__ = 'keith'

import argparse
import os
import csv
import sys
import json
import chardet
from StringIO import StringIO

import pypred

get_elements = lambda search_list, indices: [search_list[i] for i in indices]


class Csv2Json:
    def __init__(self):
        self.csv_file_path = None
        self.json_file_path = None
        self.requested_fields = []
        self.pk_field = None
        self.predicate = None
        self.num_rows = -1

        self.available_fields = []
        self.export_fields = []
        self.export_obj = None
        self.encoding = 'UTF-8'

        self.parse_args()

    def parse_args(self):
        # create the argument parser
        parser = argparse.ArgumentParser(description='This program will extract a subset of data from a CSV '
                                                     'file and export it to a JSON file',
                                         add_help=True)

        # add an argument for the input file
        parser.add_argument('-i', '--input',
                            help='path to the CSV input file',
                            required=True,
                            action='store')

        parser.add_argument('-f', '--fields',
                            help='comma-separated list of fields to be exported',
                            required=False,
                            action='store')

        parser.add_argument('-p', '--pk-field',
                            help='the name of the field containing the primary key value.  If supplied, the output '
                                 'JSON will be keyed by this value',
                            required=False,
                            action='store')

        parser.add_argument('-c', '--condition',
                            help='Boolean expression to filter out unwanted data (only matches will be exported)',
                            required=False,
                            action='store')

        parser.add_argument('-n', '--num-rows',
                            help='the maximum number of rows to be exported',
                            required=False,
                            action='store',
                            type=int,
                            default=-1)

        parser.add_argument('-o', '--output',
                            help='path to output file',
                            required=True,
                            action='store')

        # parse the arguments
        args = parser.parse_args()

        # get the input file path
        self.csv_file_path = args.input
        if not os.path.exists(self.csv_file_path):
            raise Exception('File not found: {}'.format(self.csv_file_path))
        if os.path.isdir(self.csv_file_path):
            raise Exception('Input file must be an actual file, not a directory')

        # get the list of fields to export
        if args.fields is not None:
            self.requested_fields = args.fields.split(',')

        # get the name of the field containing the zip code
        self.pk_field = args.pk_field
        self.export_obj = self.prepare_export_obj()

        # get the predicate if there is one
        if args.condition is not None:
            self.predicate = pypred.Predicate(args.condition)

        # get the maximum number of rows to export
        self.num_rows = args.num_rows

        # get the path to the output file
        self.json_file_path = args.output

    def load(self):
        csv_data = self.load_csv_data()

        self.parse_csv_data(csv_data)

    def load_csv_data(self):
        print 'Reading data from {}...'.format(self.csv_file_path)
        return open(self.csv_file_path, 'r').read()

    def parse_csv_data(self, csv_data):
        # get the character encoding
        # self.encoding = chardet.detect(csv_data)['encoding']
        # print 'Detected encoding: {}'.format(self.encoding)

        # use a CSV Dictionary Reader for the rest of file
        # reader = csv.DictReader(csv_data.splitlines())
        reader = csv.DictReader(StringIO(csv_data))
        self.process_fieldnames(reader)

        try:
            for row in reader:
                if self.num_rows < 0 or self.num_rows > 0:
                    if self.predicate is None or self.predicate.evaluate(row):
                        self.num_rows -= 1
                        self.add_record(row)
                else:
                    break
        except csv.Error as e:
            sys.exit('file %s, line %d: %s' % (self.csv_file_path, reader.line_num, e))

    def process_fieldnames(self, reader):
        self.available_fields = reader.fieldnames
        print 'Available fields: {}'.format(', '.join(self.available_fields))

        if self.pk_field and self.pk_field not in self.available_fields:
            raise Exception('The required primary key field "{}" is not one of the available fields'.
                            format(self.pk_field))

        if len(self.requested_fields) == 0:
            # export all fields
            self.export_fields = self.available_fields
            print 'All available fields will be exported'
        else:
            self.export_fields = [f for f in self.requested_fields if f in self.available_fields]

            if len(self.export_fields) == 0:
                self.export_fields = self.available_fields
                print 'All available fields will be exported'
            else:
                print 'The following fields will be exported: {}'.format(', '.join(self.export_fields))

    def add_record(self, row):
        record = self.create_record(row)
        # print record

        if self.pk_field is not None:
            self.export_obj[record[self.pk_field]] = record
        else:
            self.export_obj.append(record)

    def create_record(self, row):
        return {unicode(k, self.encoding): unicode(row[k], self.encoding) for k in self.export_fields}

    def export(self):
        with open(self.json_file_path, 'w') as output:
            json.dump(self.finalize_export_obj(self.export_obj), output, encoding=self.encoding)

    def prepare_export_obj(self):
        if self.pk_field is not None:
            return {}
        else:
            return []

    def finalize_export_obj(self, obj):
        return obj


if __name__ == '__main__':
    c2j = Csv2Json()
    c2j.load()
    c2j.export()
