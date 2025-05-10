import csv
import os

def write_data_to_csv(data, filename='data.csv'):
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(data)

def read_data_from_csv(filename='data.csv'):
    data = []
    if os.path.isfile(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                data.append(row)
    return data