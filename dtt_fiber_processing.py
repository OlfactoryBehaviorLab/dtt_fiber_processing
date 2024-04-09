import numpy as np
import pandas as pd
from allensdk.core.reference_space_cache import ReferenceSpaceCache
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


def get_atlas_components() -> tuple[ReferenceSpaceCache, dict, dict]:
    # Modified from
    # https://allensdk.readthedocs.io/en/latest/_static/examples/nb/reference_space.html#Using-a-StructureTree
    
    output_dir = Path('./ABA')
    output_dir.mkdir(exist_ok=True)
    reference_space_key = Path('annotation', 'ccf_2017')

    resolution = 25
    rspc = ReferenceSpaceCache(resolution, reference_space_key, manifest=output_dir.joinpath('manifest.json'))

    # ID 1 is the adult mouse structure graph
    tree = rspc.get_structure_tree(structure_graph_id=1)
    id_map = tree.get_id_acronym_map()
    structure_map = tree.get_ancestor_id_map()

    return tree, id_map, structure_map

def parse_datafile_paths(data_dir) -> tuple:
    query_file = []
    data_dir_contents = list(data_dir.glob('*.csv')) # Get all CSV Files

    for file in data_dir_contents: # Find the query file, set it aside, and remove it from the list
        if 'query' in file.stem:
            query_file = file
            data_dir_contents.remove(file)

    return query_file, data_dir_contents
    

def split_data(data: pd.DataFrame) -> tuple:
    left_data_index = []
    right_data_index = []
    classification = data['Classification']


    for index, value in classification.items():
        if pd.isna(value):  # The total value lists NaN as its classification
            left_data_index.append(index)
            right_data_index.append(index)
        elif 'Left' in value:  # If the class includes Left, put it in one bin, otherwise, its certainly a right
            left_data_index.append(index)
        else:
            right_data_index.append(index)

    left_data = data.iloc[left_data_index]  # Select only left regions
    right_data = data.iloc[right_data_index] # Select only right regions

    left_data['Classification'] = left_data['Classification'].apply(strip_sides)
    right_data['Classification'] = right_data['Classification'].apply(strip_sides)

    return left_data, right_data


def strip_sides(value):
    if pd.isna(value):
        return 'Total_Brain'
    else:
        return value.split(" ")[1]  # Split at the space and take the right side [LEFT/RIGHT], [Brain Region]


def get_region_ids(query_data, side_data):
    id_nums = []
    acronyms = query_data['acronym']
    data_classes = side_data['Classification'].str.lower()
    for brain_region in data_classes:
        index = np.where(acronyms == brain_region)[0]
        if len(index) == 0:
            print(brain_region)
        id_num = query_data['id'].iloc[index].values
        id_nums.extend(id_num)

    return id_nums


def split_structure_id_path(path):
    new_path = path[1:-1]  # remove leading and trailing slash
    new_path = new_path.split('/')  # Separate by slashes

    return new_path

def main():
    #data_dir = get_folder()

    data_dir = Path('R:\\3_Histology\Qupath Projects\export measurements Test65')
    query_file, data_files = parse_datafile_paths(data_dir)
    data_file = data_files[0] # We're going to work with one file for now

    data_file = pd.DataFrame(data_file)


if __name__ == "__main__":
    main()