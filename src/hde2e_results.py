#!/usr/bin/python3

""" Analyze the results of the HDE2E Latency Benchmark
    (High Density End-2-End)

    What it does:
    - Read the results of file into Pandas data frames. Basically each result
      is mapped into a container of data frame and meta informations.
    - There are separated lists of Latency and Jitter containers each.
    - Resort the results into another list of data frames for statistic usage.
      They are sorted (grouped) by the values measured from each instance.
    - Output:
      - Print (logging) statistics
      - Save statistics into file (csv)
      - Create Box plot for each value
      - Create Scatter plot for each value
      - Save plots as picture (png)
      - Show plots on the screen (limited to small instance count only)

    TODO:
    - The count (x-axis) or index could be converted based on Tasks cycle time
      (e.g.: 5ms or 500us). But as these values are configurable, there is no
      evidence on the real cycle time. More detailed: There is some information
      in the result files, but they do not show the configured
      but only the static interval time.
    - Each E2E instances is started seperately. Means, timewise there is no
      relation between each of the results. BUT, the statistics data frame
      combines them and gives a wrong assumption or relation!!
"""

import argparse
import logging
import glob
import pandas as pd
from matplotlib import pyplot as plt

VERSION = 'v0.3'

# Limit statistics data frame float format
pd.set_option('display.float_format', lambda x: f'{x:.1f}')

#################################################
# Constants
FILE_LATENCY = 'Codesys-*-PubSub_Latency.csv'
FILE_JITTER = 'Codesys-*-PubSub_Jitter.csv'

LAT = 'Latency'
JIT = 'Jitter'

# Columns name in the Latency log files
LABEL_LAT = ['T2-T1', 'T3-T2', 'T4-T3', 'T4-T1']
COLOR_LAT = ['red', 'green', 'gold', 'blue']
# Column name of the Jitter file
LABEL_JIT = 'PubSubCycleTime'

DESCR_LOG = ['mean', 'std', 'min', 'max']
DESCR_BAR = ['mean', 'std', 'min', 'max']
DESCR_CSV = [.9, .99, .999, .9999, .99999]


#################################################
class DataFrameContainer:
    ''' Class to connect a dataframe with metadata like:
        filename, name, type'''
    def __init__(self, filename, path, nrows=None):
        self.filename = filename
        self.name = self.filename.split('-')[2]
        # TODO Change results file name for an easier match here.
        self.type = self.filename.split('-')[3].split('_')[1].split('.')[0]
        self.skiprows = 0
        if self.type == JIT:
            self.skiprows = 6
            # TODO Read metadata (Task configuration) above the measured data:
            # Note: This is not implemented as the values are not reflecting
            # the dynamical configuration, but only show the static PLC config
            #
            # TaskName;CycleTime;Priority
            # PubSubTask;500;1
            # ProcessingTask;5000;2
            # FileLoggingTask;50000;5
            # MainTask;500000;16
            # VISU_TASK;200000;18

        # Read files into data frame
        self.df = pd.read_csv(path + self.filename, sep=';',
                              nrows=nrows, skiprows=self.skiprows)

        # Debug original data frames from file
        logging.debug(self.filename)
        logging.debug(self.df)


def main():
    #################################################
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', metavar='DIR',
                        help='Directory contain measurements')
    parser.add_argument('-d', '--debug',
                        help="Print lots of debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG,
                        default=logging.WARNING)
    parser.add_argument('-v', '--verbose',
                        help="Be verbose",
                        action="store_const", dest="loglevel", const=logging.INFO)
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--save', action=argparse.BooleanOptionalAction,
                        default=False,
                        help='Save figures to a file.')
    parser.add_argument('--show', action=argparse.BooleanOptionalAction,
                        default=False,
                        help='Display all figures interactively.\
                              Use only with 1 instance for test purpose!')
    # parser.add_argument('--skip', type=int, default=0,
    #                    help='Skip first N rows of input data.')
    parser.add_argument('--rows', type=int, default=None,
                        help='Read N rows of input data.')

    args = parser.parse_args()

    # Set loglevel
    logging.basicConfig(level=args.loglevel, format='%(message)s')

    #################################################
    # Gobals
    path = args.directory
    # Add final slash if needed
    if path[-1] != '/':
        path += '/'

    #################################################
    # Load data files into a list of DF Containers
    # which includes the Pandas dataframe and more info.

    # TODO Maybe create a a common list of both Latency and Jitter container
    # Latency
    filenamesLatency = sorted(glob.glob(FILE_LATENCY, root_dir=path))

    lats = []
    for file in filenamesLatency:
        lats.append(DataFrameContainer(file, path, args.rows))

    # Jitter
    filenamesJitter = sorted(glob.glob(FILE_JITTER, root_dir=path))

    jits = []
    for file in filenamesJitter:
        jits.append(DataFrameContainer(file, path, args.rows))

    #################################################
    # Statistic Dataframe
    # Merge related columns of each instance into separate dictonary of dataframes
    df_stat = {}

    for col in LABEL_LAT:
        # Extract the specific column from each DataFrame
        column_data = [dfc.df[col] for dfc in lats]

        # Concatenate the extracted columns along the columns axis
        concatenated_df = pd.concat(column_data, axis=1)

        # Rename the columns to avoid duplication
        concatenated_df.columns = [f'{dfc.name}' for dfc in lats]

        # Store the new DataFrame in the dictionary
        df_stat[col] = concatenated_df

    # Same for the Jitter
    column_data = [dfc.df[LABEL_JIT] for dfc in jits]
    concatenated_df = pd.concat(column_data, axis=1)
    concatenated_df.columns = [f'{dfc.name}' for dfc in jits]
    df_stat[JIT] = concatenated_df

    # Debug statistics data frame
    logging.debug('\n############## Statistic data frame ###############')
    logging.debug(df_stat)

    #################################################
    # Print statistics as transformed table
    for label, df in df_stat.items():
        logging.info('\n#### ' + label + ' ############################')
        logging.info(df.describe().loc[DESCR_LOG].T)

    #################################################
    # Write statistics into files (csv)
    if args.save:
        for label, df in df_stat.items():
            # Generate descriptive statistics and transpose index and columns.
            df_tmp = df.describe(DESCR_CSV).T
            df_tmp.index.name = 'name'
            # Write CSV file
            df_tmp.to_csv(path + 'stat_' + label + '.csv')

    #################################################
    # Create the box, bar and scatter figures
    if args.show or args.save:
        for label, df in df_stat.items():
            # Create combined box plots
            df.plot.box(title=label)
            plt.tight_layout()
            if args.save:
                plt.savefig(path + 'box_' + label + '.png')
                plt.close()

            # Create bar like figures of the statistics
            df.describe().loc[DESCR_BAR].plot.bar(title=label, subplots=False,
                                                  ylabel='time [us]')
            plt.tight_layout()
            if args.save:
                plt.savefig(path + 'bar_' + label + '.png')
                plt.close()

        # Create scatter plots
        # TODO Create common Y-Axis limits (boundaris)
        for lat in lats:
            # Create helper column based on index, required by scatter plot.
            lat.df['count'] = lat.df.index
            for idx, col in enumerate(LABEL_LAT):
                lat.df.plot(kind='scatter', x='count', y=col,
                            title=lat.name + ' - ' + col, color=COLOR_LAT[idx],
                            grid=True, s=1, ylabel='latency [us]')
                if args.save:
                    plt.savefig(path + 'scatter_' + lat.name + '_' + col + '.png',
                                dpi=500)
                    plt.close()

        for jit in jits:
            # Create helper column based on index, required by scatter plot.
            jit.df['count'] = jit.df.index
            jit.df.plot(kind='scatter', x='count', y=LABEL_JIT,
                        title=jit.name + ' - ' + JIT,
                        grid=True, s=1, ylabel='cycle time [us]')
            if args.save:
                plt.savefig(path + 'scatter_' + jit.name + '_' + JIT + '.png',
                            dpi=500)
                plt.close()

    # Show the Plots
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
