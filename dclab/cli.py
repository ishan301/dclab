"""command line interface"""
import argparse
import pathlib

from .rtdc_dataset import fmt_tdms, load
from . import definitions as dfn


def tdms2rtdc():
    """Convert .tdms data sets to the hdf5-based .rtdc file format"""
    parser = tdms2rtdc_parser()
    args = parser.parse_args()

    path_tdms = pathlib.Path(args.tdms_path).resolve()
    path_rtdc = pathlib.Path(args.rtdc_path)

    # Determine whether input path is a tdms file or a directory
    if path_tdms.is_dir():
        files_tdms = fmt_tdms.get_tdms_files(path_tdms)
        if path_rtdc.is_file():
            raise ValueError("rtdc_path is a file: {}".format(path_rtdc))
    else:
        files_tdms = [path_tdms]

    for ii, ff in enumerate(files_tdms):
        ff = pathlib.Path(ff)
        relpath = ff.relative_to(path_tdms)
        print("\033[1mConverting {:d}/{:d}: {}\033[0m".format(
              ii + 1, len(files_tdms), relpath))
        # load dataset
        ds = load.load_file(ff)
        # determine output file name (same relative path)
        fr = path_rtdc / relpath.with_suffix(".rtdc")
        if not fr.parent.exists():
            fr.parent.mkdir(parents=True)
        # determine features to export
        features = []
        if args.compute_features:
            tocomp = dfn.feature_names + ["contour", "image", "trace"]
        else:
            tocomp = ds._events
        for feat in tocomp:
            if feat in ["contour", "image", "trace"]:
                if not ds[feat]:
                    # ignore non-existent c/i/t
                    continue
            elif feat not in ds:
                # ignore non-existent feature
                continue
            features.append(feat)
        # export as hdf5
        ds.export.hdf5(path=fr,
                       features=features,
                       filtered=False,
                       override=True)


def tdms2rtdc_parser():
    descr = "Convert RT-DC .tdms files to the hdf5-based .rtdc file format. " \
            + "Note: Do not delete original .tdms files after conversion. " \
            + "The conversion might be incomplete."
    parser = argparse.ArgumentParser(description=descr)
    parser.add_argument('--compute-ancillary-features',
                        dest='compute_features',
                        action='store_true',
                        help='Compute features, such as volume or emodulus, '
                             + 'that are otherwise computed on-the-fly. '
                             + 'Use this if you want to minimize analysis '
                             + 'time in e.g. ShapeOut. CAUTION: ancillary '
                             + 'feature recipes might be subject to change '
                             + '(e.g. if an error is found in the recipe). '
                             + 'Disabling this option maximizes '
                             + 'compatibility with future versions and '
                             + 'allows to isolate the original data.')
    parser.set_defaults(compute_features=False)
    parser.add_argument('tdms_path', metavar='tdms-path', type=str,
                        help='Input path (tdms file or folder containing '
                             + 'tdms files)')
    parser.add_argument('rtdc_path', metavar='rtdc-path', type=str,
                        help='Output path (file or folder), existing data '
                             + 'will be overridden')
    return parser


def verify_dataset():
    """Perform checks on experimental data sets"""
    parser = verify_dataset_parser()
    args = parser.parse_args()
    path_in = pathlib.Path(args.path).resolve()
    load.check_dataset(path_in)


def verify_dataset_parser():
    descr = "Check experimental data sets for completeness. Note that old " \
            + "measurements will most likely fail this verification step. " \
            + "This program is used to enforce data integrity with future " \
            + "implementations of RT-DC recording software (e.g. ShapeIn)."
    parser = argparse.ArgumentParser(description=descr)
    parser.add_argument('path', metavar='path', type=str,
                        help='Path to experimental dataset')
    return parser