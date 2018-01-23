#!/usr/bin/env python 

import os
import logging
import csv

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from shutil import copyfile

LOGGER = logging.getLogger(__name__)

original_pics_common_destination = r'Users\Herbario\Desktop\Proyecto Flora'

csv_file_location = r'test.csv'

debug_limit = 50


def main():
    args = _parse_args()
    configure_logging(args.is_debug)

    try:
        organize_pics(args)
    except Exception as e:
        LOGGER.exception(e)
        raise


def organize_pics(args):
    LOGGER.info("Organizing pics...")
    # result_set = execute_query(select_images_path)
    result_set = get_pic_info_from_csv(csv_file_location)
    tidy_up_pics(args, result_set)
    LOGGER.info("DONE!!!")


def get_pic_info_from_csv(file_location):
    result_set = []

    with open(file_location, "r", encoding="UTF-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            row = [str.strip(x) for x in row]
            LOGGER.debug(row)
            result_set.append(Pic(
                row[0],
                int(row[1]),
                row[2],
                row[3],
                row[4],
                row[5]
            ))

    return result_set


def tidy_up_pics(args, result_set):
    # Get the total count of rows in the result set in order to calculate a percentage of progress
    total_rows = len(result_set)

    # Prepare the destination Folder
    prepare_folder(args.destination)

    sample_counter = 1
    last_species_name = ""

    # If the destination folder is there, iterate over the rows
    # Print the percentage of progress given the number of the row.
    for pic_idx, pic in enumerate(result_set, 1):

        # This will allow us to keep track of the filename counter for the species
        if pic_idx != 1 and pic.nombre != last_species_name:
            sample_counter = 1

        last_species_name = pic.nombre
        LOGGER.info("PROGRESS: %d/%d" % (pic_idx, total_rows))

        family_folder = os.path.join(args.destination, pic.familia)

        prepare_folder(family_folder)

        # Create a new folder for the Nombre of the sample and prepare to copy the images to that folder
        species_folder = os.path.join(family_folder, pic.nombre)

        prepare_folder(species_folder)

        # The name of the file should be: Nombre - ID. We need to keep count of the ID so that it goes in ascendant order
        filename = generate_filename(species_folder, pic.nombre, pic.nombre_archivo, sample_counter)

        # Copy and rename the file only if the should_write flag is active, otherwise just print to log
        if not os.path.exists(filename) or args.should_overwrite:
            copy_and_rename_pic(args, filename, pic)
        else:
            LOGGER.info("Skipping, as we already have a file for %s" % filename)
        sample_counter += 1

        if args.is_debug and pic_idx == debug_limit:
            LOGGER.info("Terminating early due to DEBUG mode...")
            break


def generate_filename(folder, nombre, nombre_archivo, sample_counter):
    extension = os.path.splitext(nombre_archivo)[1]
    return os.path.join(folder, "%s - %d%s" % (nombre, sample_counter, extension))


def copy_and_rename_pic(args, filename, pic):
    source_file = os.path.join(args.source, pic.ruta)

    if args.should_write:
        LOGGER.info("Renaming and copying %s to %s" % (source_file, filename))

        if not os.path.exists(source_file):
            if args.should_skip_files_not_found:
                LOGGER.error(
                    "%s was not found, skipping since the skip not-found files flag was provided..." % source_file)
                return
            else:
                raise FileNotFoundError(source_file)

        copyfile(source_file, filename)

    else:
        LOGGER.info("Write switch is OFF, simulating renaming and copying %s to %s" % (source_file, filename))


def prepare_folder(folder):
    if not os.path.exists(folder):
        LOGGER.info("Creating folder %s" % folder)
        os.makedirs(folder)
    else:
        LOGGER.info("Skipping creation of %s, we already have it" % folder)


def _parse_args():
    parser = ArgumentParser(description="Plant Image Reorganizer",
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--source', '-s',
                        help="Specifies the folder from which to read the pictures.",
                        required=True)

    parser.add_argument('--destination', '-d',
                        help="Specifies the path of the output folder.",
                        default=os.path.join(os.path.expanduser("~"), "PlantReorganizer"))

    parser.add_argument("--debug",
                        dest="is_debug",
                        action="store_true",
                        help="Activates debug mode.")

    parser.add_argument("--write", "-w",
                        dest="should_write",
                        action="store_true",
                        help="Activates the actual writing process to disk, otherwise it is just simulated.")

    parser.add_argument("--skip", "-k",
                        dest="should_skip_files_not_found",
                        action="store_true",
                        help="Determines whether invalid files should be skipped. If not, the script will exit with an error.")

    parser.add_argument("--overwrite", "-o",
                        dest="should_overwrite",
                        action="store_true",
                        help="Specifies if the files should be overwritten.")

    args = parser.parse_args()

    return args


def configure_logging(is_debug=True):
    log_format = "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
    logging.basicConfig(format=log_format,
                        level=logging.DEBUG if is_debug else logging.INFO,
                        filename="PlantReorganizer.log")
    logging.getLogger().addHandler(logging.StreamHandler())

    LOGGER.info("******* Plant Image Reorganizer *******")
    LOGGER.debug("Ready to DEBUG!")


class Pic():

    def __init__(self, nombre, id_ejemplar, ruta, nombre_objeto, genero, familia):
        self.nombreid = id_ejemplar
        self.nombre = nombre[:nombre.find("-")].strip()
        self.familia = familia

        # We remove the leading '\'
        original_folder = ruta.replace(original_pics_common_destination, "")[1:]
        self.ruta = os.path.join(original_folder, nombre_objeto.strip(" "))
        self.nombre_archivo = nombre_objeto


if __name__ == '__main__':
    main()