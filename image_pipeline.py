# Import default Python libraries
from argparse import ArgumentParser, RawTextHelpFormatter
import os

# Import installed Python libraries
from astropy.io import fits  # change to table.read?
# from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy import units as u
import numpy as np
from reproject import reproject_interp

from modules.get_ancillary import *
from modules.functions import get_radecfreq
from src import make_images
from src import make_spectra
from src.combine_images import combine_images


###################################################################

parser = ArgumentParser(description="Create images from a SoFiA catalog and cubelets, or fits file. \n"
                                    "Only works with SoFiA-2 and wcs=True (for now).",
                        formatter_class=RawTextHelpFormatter)

parser.add_argument('-c', '--catalog', default='test_data/UGC7012_cat.txt',
                    help='Specify the input XML or ascii catalog name (default: %(default)s).')

parser.add_argument('-x', '--suffix', default='png',
                    help='Specify the output image file type: png, pdf, eps, jpeg, tiff, etc (default: %(default)s).')

parser.add_argument('-o', '--original', default=None,
                    help='Specify the original fits data: used for plotting HI spectra *with* noise over \n'
                         'the full frequency range of the cube. Otherwise, plot with noise over frequency \n'
                         'range in the cubelet.  Uses 2D mask to integrate. (No default).')

parser.add_argument('-b', '--beam', default=None,
                    help='Specify the beam dimensions (bmaj,bmin,bpa) in arcsec, arcsec, deg. If only 1 value is\n'
                         'given, assume a circular beam. If 2 values are given, assume PA = 0. (No default).')

parser.add_argument('-i', '--image_size', default=6,
                    help='Specify the minimum optical image size to retrieve in arcmin.  It will be adjusted if\n'
                         'the HI mask is larger. Note max panstarrs image size is 8 arcmin (default: %(default)s).')

parser.add_argument('-s', '--surveys', default=None,
                    help='Specify the surveys to retrieve and on which to overlay HI contours. So far, DSS2 blue\n'
                         'and PanSTARRS alway by default. This allows the option to add COSMO HST for CHILES: -k \'hst\'.')

parser.add_argument('-m', '--imagemagick', default=False,
                    help='If imagemagick is installed on user\'s system, optionally combine main plots into single '
                         'large file',
                    action='store_true')

###################################################################

# Parse the arguments above
args = parser.parse_args()
suffix = args.suffix
original = args.original
imagemagick = args.imagemagick
try:
    beam = [int(b) for b in args.beam.split(',')]
except:
    beam = []
opt_view = float(args.image_size) * u.arcmin
try:
    surveys = [k for k in args.surveys.split(',')]
except:
    surveys = []

print("\n*****************************************************************")
print("\tBeginning SoFiA-image-pipeline (SIP).")

if (suffix == 'eps') | (suffix == 'ps'):
    print("\tWARNING: {} may have issues with transparency or making spectra.".format(suffix))


# Read in the catalog file:
catalog_file = args.catalog

if catalog_file.split(".")[-1] == "xml":
    print("\tReading catalog in XML format.")
    print("\tWARNING: always assumes an xml file comes from SoFiA-2.")
    catalog = Table.read(catalog_file)
    sofia = 2
elif (catalog_file.split(".")[-1] == "txt") | (catalog_file.split(".")[-1] == "ascii"):
    print("\tReading catalog in ascii format.")
    try:
        catalog = Table.read(catalog_file, format='ascii', header_start=18)  # Depends on SoFiA version!!! Do a brute force tes?
        print("\tCatalog generated by SoFiA-2?")
        sofia = 2
        no_cat = False
    except:
        no_cat = True
    if no_cat == True:
        try:
            catalog = Table.read(catalog_file, format='ascii', header_start=1)  # Depends on SoFiA version!!! Do a brute force tes?
            print("\tCatalog generated by SoFiA-1?")
            sofia = 1
            no_cat = False
        except:
            no_cat = True
    if no_cat == True:
        print("\tERROR: Trouble reading ascii format catalog.  A bug or generated by a different version of SoFiA?")
else:
    print("\tERROR: Catalog must be in xml or ascii format.")
    exit()


# Check what's in the catalog; calculate ra, dec if necessary:
if ('ra' not in catalog.colnames) and (not original):
    print("\tERROR: Looks like catalog doesn't contain 'ra' and 'dec' columns. Re-run SoFiA with \n" \
          "\t\t'parameter.wcs = True' or you must include the path to the original fits file to derive \n" \
          "\t\tra, dec from the pixel values in the catalog.")
    print("*****************************************************************\n")
    exit()
elif ('ra' not in catalog.colnames) and (original):
    print("\tWARNING: Looks like catalog doesn't contain 'ra' and 'dec' columns. But can derive them with \n" \
          "\t\tthe pixel positions in the catalog provided.")
    print("\tWARNING: This probably means you ran SoFiA with 'parameter.wcs = False' which means the units \n" \
          "\t\t in your maps may be completely wacky! (Channel width knowledge is not maintained.)")
    ra, dec, freq = get_radecfreq(catalog, original)
    catalog['ra'] = ra
    catalog['dec'] = dec
    catalog['freq'] = freq

# Rename the spectral column if cube was in velocity. For now treat all velocity axes the same (dumb temporary fix)
if 'v_app' in catalog.colnames:
    catalog.rename_column('v_app', 'v_col')
elif 'v_rad' in catalog.colnames:
    catalog.rename_column('v_rad', 'v_col')
elif 'v_opt' in catalog.colnames:
    catalog.rename_column('v_opt', 'v_col')
elif 'freq' not in catalog.colnames:
    print("ERROR: Column name for spectral axis not recognized.")
    exit()

# Allow for some source selection?


# Set up some directories
cubelet_dir = catalog_file.split("_cat.")[0] + '_cubelets/'
if not os.path.isdir(cubelet_dir):
    print("\tERROR: Cubelet directory does not exist. Need to run SoFiA-2 or restructure your directories.")
    exit()

figure_dir = catalog_file.split("_cat.")[0] + '_figures/'
if not os.path.isdir(figure_dir):
    print("\tMaking figure directory.")
    os.system('mkdir {}'.format(figure_dir))

src_basename = cubelet_dir + catalog_file.split("/")[-1].split("_cat.")[0]


# Make all the images on a source-by-source basis.  In future, could parallelize this.
n_src = 0

for source in catalog:

    source['id'] = int(source['id'])  # For SoFiA-1 xml files--this doesn't work bc column type is float.
    make_images.main(source, src_basename, opt_view=opt_view, suffix=suffix, sofia=sofia, beam=beam, surveys=surveys)
    make_spectra.main(source, src_basename, original, suffix=suffix, beam=beam)

    if imagemagick:
        combine_images(source, src_basename)

    n_src += 1


print("\n\tDONE! Made images for {} sources.".format(n_src))
print("*****************************************************************\n")
