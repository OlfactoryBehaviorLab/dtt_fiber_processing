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



def main():

    

if __name__ == "__main__":
    main()