#!/usr/bin/env python 

import os
import logging
import glob
import pyodbc

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from shutil import copyfile

LOGGER = logging.getLogger(__name__)

connection_string = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    r'DBQ=C:\path\to\mydb.accdb;'
    )

select_images_path = """
    SELECT Determinacion.Nombre,
        Determinacion.IdEjemplar,
        ObjetoExterno.Ruta,
        ObjetoExterno.NombreObjeto
    FROM Determinacion 
        INNER JOIN (ObjetoExterno INNER JOIN RelObjetoExternoEjemplar ON ObjetoExterno.IdObjetoExterno = RelObjetoExternoEjemplar.IdObjetoExterno) ON Determinacion.IdEjemplar = RelObjetoExternoEjemplar.IdEjemplar
    ORDER BY Determinacion.Nombre;
"""

pics_final_destination = r'C:\Ruta\al\Destino'

original_pics_common_destination = r'Ruta\Comun\En\El\Herbario'


def main():
    args = _parse_args()
    configure_logging(args.is_debug)
    organize_pics(args)


def organize_pics(args):
    LOGGER.info("Executing query...")
    result_set = execute_query(select_images_path)
    tidy_up_pics(args, result_set)


def tidy_up_pics(args, result_set):
    # Get the total count of rows in the result set in order to calculate a percentage of progress
    total_rows = result_set.rowcount

    # Prepare the destination Folder
    prepare_folder(args.destination)

    sample_counter = 1
    last_species_name = ""


    # If the destination folder is there, iterate over the rows
    # Print the percentage of progress given the number of the row.
    for row_num, row in enumerate(result_set["results"], 1):

        # This will allow us to keep track of the filename counter for the species
        if row_num != 1 and row.nombre != last_species_name:
            sample_counter = 1

        last_species_name = row.nombre
        progress = (row_num * 100) / total_rows
        LOGGER.info("PROGRESS: %i\%" % progress)

        family_folder = ""

        # For each row, check the name of the family (and if it IS a family (id: 9)
        # If it is a family, check/create that a folder exists for the family, if it's not,
        # report it to log and put it in the No Family folder
        if row.nombreid == 9:
            family_folder = os.path.join(args.destination, row.familia)
        else:
            LOGGER.warning("%s seems not to be a family because it has an ID of %i, we're putting it in the default folder" % (row.nombre, row.nombreid))
            family_folder = os.path.join(args.destination, "NoFamily")

        prepare_folder(family_folder)

        # Create a new folder for the Nombre of the sample and prepare to copy the images to that folder
        species_folder = os.path.join(family_folder, row.nombre)

        prepare_folder(species_folder)
        # The name of the file should be: Nombre - ID. We need to keep count of the ID so that it goes in ascendant order
        filename = os.path.join(family_folder, "%s - %s - %i" % (row.nombre, row.nombreArchivo, sample_counter))

        # Copy and rename the file only if the should_write flag is active, otherwise just print to log
        if not len(glob.glob(row.nombreArchivo)) > 0 or args.should_overwrite:
            copy_and_rename_pic(args, filename, row)
        else:
            LOGGER.info("Skipping, as we already have a file for %s" % filename)
        sample_counter += 1

        if args.is_debug and row_num == 64:
            LOGGER.info("Terminating early due to DEBUG mode...")
            break


def copy_and_rename_pic(args, filename, row):
    original_folder = row.ruta.replace(original_pics_common_destination, "")
    source_file = os.path.join(args.source, original_folder, row.nombreArchivo)
    copyfile(source_file, filename)


def prepare_folder(folder):
    if not os.path.exists(folder):
        LOGGER.info("Creating folder %s" % folder)
        os.makedirs(folder)


def execute_query(query, query_params):
    result_set = {
        "titles": [],
        "results": []
    }

    # con = pyodbc.connect('DRIVER={};DBQ={};PWD={}'.format(DRV, MDB, PWD))
    try:
        with pyodbc.connect(connection_string) as con:
            with con.cursor() as cursor:
                # The execute method already prepares the query
                cursor.execute(query)
                res = cursor.fetchall()
                result_set["titles"] = [desc[0] for desc in cursor.description]
                result_set["results"] = res
    except Exception as e:
        LOGGER.error(e)
        raise

    return result_set


def _parse_args():
    parser = ArgumentParser(description="Plant Image Reorganizer",
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--source', '-s',
                        help="Specifies the folder from which to read the pictures.",
                        required=True)

    parser.add_argument('--destination', '-d',
                        help="Specifies the path of the output folder.",
                        default= os.path.join(os.path.expanduser("~"),"PlantReorganizer"))

    parser.add_argument("--debug",
                        dest="is_debug",
                        action="store_true",
                        help="Activates debug mode.")

    parser.add_argument("--write", "-w",
                        dest="should_write",
                        action="store_true",
                        help="Activates the actual writing process to disk, otherwise it is just simulated.")

    parser.add_argument("--overwrite", "-o",
                        dest = "should_overwrite",
                        action = "store_true",
                        help = "Specifies if the files should be overwritten.")

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


if __name__ == '__main__':
    main()