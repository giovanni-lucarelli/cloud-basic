import re
import csv

# input_file = "stress_ng_hdd_run_1.txt"
# output_file = "stressng_hdd.csv"

pattern = re.compile(
    r"stress-ng: metrc: \[\d+\] (?P<stressor>\w+)\s+(?P<bogo_ops>\d+)\s+(?P<real_time>\d+\.\d+)\s+(?P<usr_time>\d+\.\d+)\s+(?P<sys_time>\d+\.\d+)\s+(?P<bogo_ops_real>\d+\.\d+)\s+(?P<bogo_ops_cpu>\d+\.\d+)"
)

rows = []

for j in range(1,6):
    with open(f"stress_ng_hdd_run_{j}.txt", "r") as infile:
        for line in infile:
            match = pattern.search(line)
            if match:
                rows.append(match.groupdict())

    # Write to CSV
with open("stress_ng_hdd.csv", "w", newline="") as csvfile:
    fieldnames = ["stressor", "bogo_ops", "real_time", "usr_time", "sys_time", "bogo_ops_real", "bogo_ops_cpu"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
