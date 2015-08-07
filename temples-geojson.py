LAT_LON_DELIMITERS = '\xb0|\'|"'
DIRECTION_FACTOR = {'N': 1, 'S': -1, 'E': 1, 'W': -1}
__author__ = 'keith'

from csv2json import Csv2Json
import re


def to_decimal_degrees(lat_or_lon):
    components = re.split(LAT_LON_DELIMITERS, lat_or_lon)
    direction = components.pop()

    components.extend(['0', '0', '0'])

    return sum(float(x) / (60.0 ** n) for n, x in enumerate(components)) * DIRECTION_FACTOR[direction]


class TemplesCsv2GeoJson(Csv2Json):
    def __init__(self):
        Csv2Json.__init__(self)
        self.pk_field = None

    def create_record(self, row):
        record = Csv2Json.create_record(self, row)
        record['marker-size'] = 'small'

        temple = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [
                    to_decimal_degrees(record['Longitude']),
                    to_decimal_degrees(record["Latitude"])
                ]
            },
            'properties': record
        }

        return temple

    def prepare_export_obj(self):
        return []

    def finalize_export_obj(self, obj):
        final_export_obj = {
            'type': 'FeatureCollection',
            'crs': {
                'type': 'name',
                'properties': {
                    'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'
                },
            },
            'features': obj
        }

        return final_export_obj


if __name__ == '__main__':
    c2j = TemplesCsv2GeoJson()
    c2j.load()
    c2j.export()
