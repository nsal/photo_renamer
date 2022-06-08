"""
Script to rename photos in a folder based on EXIF data:
    capture time
    location
"""

import os
import sys
from typing import NamedTuple
import exifread
from geopy import Nominatim



class ParsedExif(NamedTuple):
    """ Named tuple for parsed exif data """
    date: str | None
    address: str | None

def get_working_dir() -> str:
    """ Get workdir from command line argument
    or use current working dir """
    wdir = sys.argv[1:]
    return wdir[0] if wdir else os.getcwd()

def get_photo_files(wdir: str) -> list[str]:
    """ Get list of photo files in workdir """
    file_names = os.listdir(wdir)
    photo_extensions = ('.jpg', '.jpeg', '.heic')
    return [f for f in file_names if f.lower().endswith(photo_extensions)]

def get_exif_data(photo: str) -> dict:
    """ Get EXIF data from photo file """
    with open(photo, 'rb') as filename:
        tags = exifread.process_file(filename)
    return tags

def get_exif_date(date_tag: exifread.classes.IfdTag) -> str | None:
    """ Get EXIF date from photo file """
    try:
        date = date_tag.values.split(' ')[0].replace(':', '-')
        return date
    except AttributeError:
        return None

def get_get_gps_coords(gps_tag: exifread.classes.IfdTag,
                 gps_ref: exifread.classes.IfdTag) -> float | None:
    """ Get EXIF gps from photo file """
    try:
        coord = float(gps_tag.values[0]) + \
                float(gps_tag.values[1]/60) + \
                float(gps_tag.values[2]/3600)
        if gps_ref.values in ('S', 'W'):
            coord = -coord
        return coord
    except AttributeError:
        return None

def parse_exif_data(tags: dict) -> ParsedExif:
    """ Parse EXIF data """
    if 'EXIF DateTimeOriginal' in tags:
        image_taken_date = get_exif_date(tags['EXIF DateTimeOriginal'])
    elif 'EXIF DateTimeDigitized' in tags:
        image_taken_date = get_exif_date(tags['EXIF DateTimeDigitized'])
    elif 'EXIF SceneCaptureType' in tags:
        image_taken_date = get_exif_date(tags['EXIF SceneCaptureType'])
    else:
        image_taken_date = None

    try:
        latitude = get_get_gps_coords(tags['GPS GPSLatitude'], tags['GPS GPSLatitudeRef'])
        longitude = get_get_gps_coords(tags['GPS GPSLongitude'], tags['GPS GPSLongitudeRef'])
    except KeyError:
        latitude, longitude, address = None, None, None
    else:
        address = get_address(latitude, longitude) if latitude and longitude else None

    parsed = ParsedExif(image_taken_date, address)
    return parsed

def get_address(lat: float, lon: float) -> str:
    """ Get address from lat/lon """
    geolocator = Nominatim(user_agent='photo-renamer')
    location = geolocator.reverse((lat, lon), zoom=8)
    try:
        return location.address.split(',')[0]
    except IndexError:
        return location.address

def rename_photo(wdir: str, old_name: str, new_name_values: ParsedExif) -> None:
    """ Rename photo based on EXIF data """
    if new_name_values.date:
        new_name = new_name_values.date

        if new_name_values.address:
            new_name = new_name + '-' + new_name_values.address

        new_name = new_name + '_' + old_name
        os.rename(os.path.join(wdir, old_name), os.path.join(wdir, new_name))


if __name__ == '__main__':
    workdir = get_working_dir()
    photo_files = get_photo_files(workdir)

    if not photo_files:
        sys.exit('No photos found')

    for photo_file in photo_files:
        exif_data = get_exif_data(os.path.join(workdir, photo_file))
        if not exif_data:
            continue
        parsed_exif = parse_exif_data(exif_data)
        rename_photo(workdir, photo_file, parsed_exif)
