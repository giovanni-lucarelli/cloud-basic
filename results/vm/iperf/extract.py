import csv
import re

# Column headers that may appear
headers_map = {
    'standard': ['Interval', 'Transfer', 'Bitrate'],
    'udp': ['Interval', 'Transfer', 'Bitrate', 'Jitter', 'Lost/Total Datagrams'],
    'retrans': ['Interval', 'Transfer', 'Bitrate', 'Retr', 'Cwnd']
}

def detect_format(header_line):
    """Detects which format the upcoming data lines follow."""
    if "Lost/Total" in header_line:
        return 'udp'
    elif "Retr" in header_line:
        return 'retrans'
    else:
        return 'standard'

def parse_data_line(line, fmt):
    # Remove ID prefix
    parts = re.split(r'\s{2,}|\t', line.strip())
    if parts[0].startswith('['):
        parts = parts[1:]  # Drop the "[ 5]" column
    return parts if len(parts) >= len(headers_map[fmt]) else None

def extract_and_write_csv(input_path, output_path):
    with open(input_path, 'r') as infile, open(output_path, 'w', newline='') as outfile:
        writer = None
        current_format = None

        for line in infile:
            line = line.strip()

            if line.startswith('[ ID]'):
                current_format = detect_format(line)
                writer = csv.writer(outfile)
                writer.writerow(['Format'] + headers_map[current_format])  # Add format info in CSV
                continue

            if line.startswith('[  '):
                if 'sec' not in line or 'receiver' in line or 'sender' in line:
                    continue  # Skip summary lines
                data = parse_data_line(line, current_format)
                if data:
                    writer.writerow([current_format] + data)

# Define input and output file paths
input_file = 'iperf3_s02c01.txt'
output_file = 'iperf3_s02c01.csv'

# Run the script
extract_and_write_csv(input_file, output_file)
