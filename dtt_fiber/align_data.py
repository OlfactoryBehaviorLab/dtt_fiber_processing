import pandas as pd
import os
import re

def process_single_excel(file_path):
    """
    Processes a single Excel file to calculate 'Total_Value' and 'Percentage_of_Largest',
    handling potential non-numeric values in the 'Value' column.

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        pandas.DataFrame or None: A DataFrame with 'Classification', 'Total_Value',
                                   and 'Percentage_of_Largest' for the file, or None if an error occurs.
    """
    try:
        df = pd.read_excel(file_path, header=None, names=['Classification', 'Value', 'Unused'])
        if 'Classification' not in df.columns or 'Value' not in df.columns:
            print(f"Warning: '{file_path}' does not have the expected 'Classification' and 'Value' columns. Skipping.")
            return None

        # Attempt to convert the 'Value' column to numeric, coercing errors to NaN
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')

        # Drop rows where 'Value' is NaN after the conversion
        df.dropna(subset=['Value'], inplace=True)

        if df.empty:
            print(f"Warning: No valid numeric data found in the 'Value' column of '{file_path}'. Skipping.")
            return None

        aggregated_df = df.groupby('Classification')['Value'].sum().reset_index()
        aggregated_df.rename(columns={'Value': f'{os.path.splitext(os.path.basename(file_path))[0]}_Total_Value'}, inplace=True)

        if not aggregated_df.empty:
            largest_value = aggregated_df.iloc[:, 1].max() # Assuming 'Total_Value' is the second column
            aggregated_df[f'{os.path.splitext(os.path.basename(file_path))[0]}_Percentage_of_Largest'] = (
                aggregated_df.iloc[:, 1] / largest_value
            ) * 100
            return aggregated_df
        else:
            print(f"Warning: No aggregable data found in '{file_path}'. Skipping.")
            return None

    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'. Skipping.")
        return None
    except Exception as e:
        print(f"An error occurred while processing '{file_path}': {e}")
        return None

def main():
    current_directory = "/mnt/r2d2/3_Histology/Qupath Projects/Combined eGFP/" # Set your directory explicitly
    excel_files_in_directory = [
        os.path.join(current_directory, filename)
        for filename in os.listdir(current_directory)
        if filename.endswith("_sum_data.xlsx") and not re.search(r'~\$', filename)
    ]

    if not excel_files_in_directory:
        print(f"No relevant Excel files found in the directory: {current_directory}")
    else:
        all_processed_data = []
        for excel_file in excel_files_in_directory:
            processed_df = process_single_excel(excel_file)
            if processed_df is not None and not processed_df.empty:
                all_processed_data.append(processed_df)

        if all_processed_data:
            # Merge all DataFrames based on 'Classification'
            merged_df = all_processed_data[0]
            for i in range(1, len(all_processed_data)):
                merged_df = pd.merge(merged_df, all_processed_data[i], on='Classification', how='outer')

            # Sort by 'Classification' for better readability
            merged_df = merged_df.sort_values(by='Classification').fillna(0)

            # Output to an Excel file
            output_excel_file = os.path.join(current_directory, 'aligned_eGFP_data.xlsx') # Save in the same directory
            merged_df.to_excel(output_excel_file, index=False)
            print(f"\nAligned data from relevant Excel files saved to '{output_excel_file}'")
        else:
            print("\nNo valid data to align.")

if __name__ == "__main__":
    main()