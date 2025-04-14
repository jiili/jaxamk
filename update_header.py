import csv

# File path
file_path = 'datasets/combined_holiday_properties.csv'

# New header
new_header = ['vuosi', 'aluejakotunniste', 'aluejakoselite', 'lukumäärä', 'ka_pinta_ala_m2', 'mediaanihinta_eur', 'keskihinta_eur', 'rantatyyppi']

try:
    # Read all rows first
    with open(file_path, 'r', encoding='utf-8', newline='') as infile:
        reader = csv.reader(infile, delimiter=';')
        # Read the header (and discard it)
        _ = next(reader)
        # Read the rest of the data rows
        data_rows = list(reader)

    # Write the new header and the data rows back
    with open(file_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile, delimiter=';')
        writer.writerow(new_header)
        writer.writerows(data_rows)

    print(f"Successfully updated header in {file_path}")

except FileNotFoundError:
    print(f"Error: File not found at {file_path}")
except Exception as e:
    print(f"An error occurred: {e}") 