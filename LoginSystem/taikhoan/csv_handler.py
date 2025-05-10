import csv
import os

# Get the directory containing the script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def write_data_to_csv(data, filename='data.csv'):
    filepath = os.path.join(CURRENT_DIR, filename)
    with open(filepath, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(data)

def read_data_from_csv(filename='data.csv'):
    data = []
    filepath = os.path.join(CURRENT_DIR, filename)
    if os.path.isfile(filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            for row in reader:
                data.append(row)
        print(f"Loaded {len(data)} records from {filepath}")
    else:
        print(f"CSV file not found at {filepath}")
    return data