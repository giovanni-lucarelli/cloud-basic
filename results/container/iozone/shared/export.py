import re
import csv

def parse_reports(text):
    reports = {}
    current_report = None
    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect report headers like "Writer report"
        if re.match(r'^".*report"$', line):
            current_report = line.strip('"').replace(" ", "_").lower()
            reports[current_report] = {'header': [], 'rows': []}
            continue

        if current_report is None:
            continue

        # Header line: contains quoted numbers
        if line.startswith('"') and reports[current_report]['header'] == []:
            headers = re.findall(r'\d+', line)
            reports[current_report]['header'] = ["block_size"] + headers
        else:
            parts = re.findall(r'\d+', line)
            if parts:
                reports[current_report]['rows'].append(parts)

    return reports

def save_reports_to_csv(reports, output_prefix=""):
    for report_name, data in reports.items():
        filename = f"{output_prefix}{report_name}.csv"
        with open(filename, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(data['header'])
            for row in data['rows']:
                writer.writerow(row)

if __name__ == "__main__":
    with open("iozone_shared_results.txt", "r") as f:
        raw_text = f.read()

    reports = parse_reports(raw_text)
    save_reports_to_csv(reports)
    print("CSV files generated successfully.")
