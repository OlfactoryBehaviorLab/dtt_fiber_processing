import numpy as np
import pandas as pd

from pathlib import Path
from tkinter import filedialog
from tqdm import tqdm


def get_folder(default_dir='R:') -> Path:
    default_dir = Path(default_dir)

    if not default_dir.exists():
        default_dir = Path('C:')


    file_dialog = filedialog.askdirectory(title='Select QuPath Output Folder', initialdir=default_dir)
    file_path = Path(file_dialog)
    return file_path


def parse_datafile_paths(data_dir) -> tuple:
    query_file = []
    data_dir_contents = list(data_dir.glob('*.csv')) # Get all CSV Files

    for file in data_dir_contents: # Find the query file, set it aside, and remove it from the list
        if 'query' in file.stem:
            query_file = file
            data_dir_contents.remove(file)

    return query_file, data_dir_contents
    



def main():
    #data_dir = get_folder()

    data_dir = Path('R:\\3_Histology\Qupath Projects\export measurements Test65')
    query_file, data_files = parse_datafile_paths(data_dir)
    data_file = data_files[0] # We're going to work with one file for now


if __name__ == "__main__":
    main()