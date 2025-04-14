import pandas as pd

# File path
file_path = 'datasets/combined_holiday_properties.csv'

# Column to translate
column_name = 'rantatyyppi' # Assuming the Finnish header is now in place

# Translation mapping
value_map = {
    'with': 'ranta',
    'without': 'ei_rantaa'
}

try:
    # Read the CSV file
    # Using low_memory=False as before, just in case
    df = pd.read_csv(file_path, sep=';', encoding='utf-8', low_memory=False)

    # Check if the column exists
    if column_name not in df.columns:
        print(f"Error: Column '{column_name}' not found in {file_path}.")
        # Attempt with the English name as a fallback, in case the header wasn't updated
        column_name_en = 'shoreline_type'
        if column_name_en in df.columns:
             print(f"Attempting with English column name '{column_name_en}'...")
             column_name = column_name_en
        else:
             print(f"English column name '{column_name_en}' also not found. Aborting.")
             exit()

    # Perform the replacement
    df[column_name] = df[column_name].replace(value_map)

    # Check if replacements happened (optional, good for verification)
    # print("Value counts after replacement:")
    # print(df[column_name].value_counts())

    # Save the modified dataframe back to the same file
    df.to_csv(file_path, index=False, sep=';', encoding='utf-8')

    print(f"Successfully translated values in column '{column_name}' in {file_path}")

except FileNotFoundError:
    print(f"Error: File not found at {file_path}")
except Exception as e:
    print(f"An error occurred: {e}") 