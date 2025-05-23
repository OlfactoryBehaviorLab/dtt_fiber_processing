import os, sys
from pathlib import Path
import pandas as pd

from allensdk.core.reference_space_cache import ReferenceSpaceCache
from allensdk.core import structure_tree
from tqdm.auto import tqdm

try:
    from PySide6.QtWidgets import QApplication, QFileDialog
    import qdarktheme
except ImportError:
    print("GUI Components not found, folder selection dialog not available!")
    os.environ['GUI'] = '0'
else:
    os.environ['GUI'] = '1'

pd.options.mode.chained_assignment = None
pd.options.mode.copy_on_write = False

WINDOWS_DEFAULT_PATH = 'R:'
NIX_DEFAULT_PATH = '/mnt/r2d2'

MAX_RETRIES = 10

def get_folder(default_dir='.', file_folder=None) -> Path:

    if file_folder is not None:
        file_folder = Path(file_folder)
        if file_folder.exists():
            return file_folder

    default_dir = Path(default_dir)
    if not default_dir.exists():
        default_dir = Path('..')

    if os.environ['GUI'] == '1':
        app = QApplication(sys.argv)
        qdarktheme.setup_theme()
        file = QFileDialog.getExistingDirectory(None, "Open Directory", str(default_dir), QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontUseNativeDialog)
        app.exit()

        if len(file) == 0:
            print('No directory selected. Using default directory.')
            file = default_dir
    else:
        print('No directory provided and file selection not available. Using default directory.')
        file = default_dir

    file_path = Path(file)
    return file_path


def parse_datafile_paths(data_dir) -> list:
    data_dir_contents = list(data_dir.glob('*sum_data.xlsx')) # Get all CSV Files
    return data_dir_contents


def get_atlas_components() -> tuple[structure_tree, dict, dict]:
    # Modified from
    # https://allensdk.readthedocs.io/en/latest/_static/examples/nb/reference_space.html#Using-a-StructureTree

    output_dir = Path('../ABA')
    output_dir.mkdir(exist_ok=True)
    reference_space_key = Path('annotation', 'ccf_2017')

    resolution = 25
    rspc = ReferenceSpaceCache(resolution, reference_space_key, manifest=output_dir.joinpath('manifest.json'))

    # ID 1 is the adult mouse structure graph
    tree = rspc.get_structure_tree(structure_graph_id=1)
    id_map = tree.get_id_acronym_map()
    structure_map = tree.get_ancestor_id_map()

    return tree, id_map, structure_map


def split_data(data: pd.DataFrame) -> tuple:
    classification = data['Classification']

    left_items_mask = classification.str.contains('Left')
    right_items_mask = classification.str.contains('Right')

    left_data = data.loc[left_items_mask]  # Select only left regions
    right_data = data.loc[right_items_mask]  # Select only right regions

    left_data.insert(0, 'old_classification', left_data['Classification'])
    right_data.insert(0, 'old_classification', right_data['Classification'])

    left_data['Classification'] = left_data['Classification'].apply(strip_sides)
    right_data['Classification'] = right_data['Classification'].apply(strip_sides)

    return left_data, right_data


def strip_sides(value):
    split_vals = value.split(" ")
    if len(split_vals) > 2:
        return " ".join(split_vals[1:])
    return split_vals[1]  # Split at the space and take the right side [LEFT/RIGHT], [Brain Region]


def _subtract_and_null_side(side_data, ids_to_remove, tree, inv_id_map):
    for ID in ids_to_remove:
        _tree = tree.parents(ID)[0] # Get tree for this ID
        current_structure = _tree['acronym'] # Get the name of this region
        parents = _tree["structure_id_path"][:-1] # The parents tree includes the current region
        current_value = side_data.loc[current_structure]['Total_Value'] # Get the value to subtract
        parent_names = [inv_id_map[key] for key in parents] # Get the name of each parent region
        side_data.loc[parent_names, 'Total_Value'].sub(current_value)  # Subtract current region from every parent
        descendants = tree.descendants(ID)[0] # Get all children for our current region, including itself
        items_to_null = [item['acronym'] for item in descendants if item['acronym'] in side_data.index]  # Sometimes the descendants are not included in our sheet, remove any that are not
        side_data.loc[items_to_null, ['Total_Value', 'Percentage_of_Largest']] = pd.NA # Null the current item and its children


def process_trace_data(data_file, ids_to_remove, tree, inv_id_map):
    data_file_df = pd.read_excel(data_file)
    left_data, right_data = split_data(data_file_df)
    left_data = left_data.set_index('Classification', drop=True)
    right_data = right_data.set_index('Classification', drop=True)

    _subtract_and_null_side(left_data, ids_to_remove, tree, inv_id_map)
    _subtract_and_null_side(right_data, ids_to_remove, tree, inv_id_map)

    left_root = left_data.loc['root']
    right_root = right_data.loc['root']
    total_root = left_root['Total_Value'] + right_root['Total_Value']

    left_data = left_data.rename(columns={'old_classification': 'Classification'})
    right_data = right_data.rename(columns={'old_classification': 'Classification'})
    left_data = left_data.set_index('Classification', drop=True)
    right_data = right_data.set_index('Classification', drop=True)

    combined_df = pd.concat([left_data, right_data], axis=0)
    combined_df.loc[:, 'Percentage_of_Largest'] = (combined_df.loc[:, 'Total_Value'] * 100 / total_root).round(3)
    total_row = pd.DataFrame([[total_root, 100]], index=['root'], columns=['Total_Value', 'Percentage_of_Largest'])
    combined_df = pd.concat([combined_df, total_row], axis=0)
    return combined_df


def aggregate_data(all_processed_data: dict) -> pd.DataFrame:
    aggregated_df = pd.DataFrame()
    for file_name, file_df in tqdm(all_processed_data.items(), desc='Aggregating Files...'):
        file_df = file_df.fillna('D')
        animal_name = file_name.split('_')[0]
        new_cols = [f'{animal_name}_TV', f'{animal_name}_Perc']
        file_df.columns = new_cols
        aggregated_df = pd.concat([aggregated_df, file_df], axis=1)

    aggregated_df = aggregated_df.fillna('X')

    return aggregated_df


def save_file(data, output_dir, file_name):
    output_file = output_dir.joinpath(file_name)
    success = False
    temp_counter = 0

    while not success:
        if temp_counter > MAX_RETRIES:
            raise PermissionError(
              f'Max number of retries met for saving {file_name}. Ensure the file is closed and the save location is available.'
          )

        if temp_counter > 0:
            _temp_path = output_file.with_stem("_".join([output_file.stem, str(temp_counter)]))
        else:
            _temp_path = output_file

        try:
            data.to_excel(_temp_path)
        except PermissionError:
            if temp_counter == 0:
                print(f'\nError saving {output_file.name} using expected name, the file must be open. Using temporary name and retrying...')

            temp_counter += 1
        else:
            success = True


def main():

    if sys.platform.startswith('win32'):
        default_dir = WINDOWS_DEFAULT_PATH
    elif sys.platform.startswith('linux'):
        default_dir = NIX_DEFAULT_PATH
    else:
        default_dir = '..'

    _data_dir = None

    data_dir = get_folder(default_dir, _data_dir)
    data_files = parse_datafile_paths(data_dir)

    output_dir = data_dir.joinpath('output')
    output_dir.mkdir(exist_ok=True, parents=True)

    input_file_path = data_dir.joinpath('input.xlsx')
    try:
        ids_to_remove = pd.read_excel(input_file_path, header=None).values
    except FileNotFoundError:
        print(f'Error! Cannot find the input.xlsx file in {{{data_dir}}}')
        return 0

    tree, id_map, structure_map = get_atlas_components()
    inv_id_map = {value: key for key, value in id_map.items()}

    all_processed_data = {}
    for file in tqdm(data_files, desc='Preprocessing Files: '):
        processed_data = process_trace_data(file, ids_to_remove, tree, inv_id_map)
        save_file(processed_data, output_dir, file.name)
        all_processed_data[file.stem] = processed_data

    print('Preprocessing Complete! Beginning data aggregation...')

    aggregated_df = aggregate_data(all_processed_data)
    save_file(aggregated_df, output_dir, 'aligned_eGFP_data.xlsx')

    print('Data aggregation complete!')

if __name__ == "__main__":
    main()
