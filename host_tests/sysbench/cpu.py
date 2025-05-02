import re
import csv

# Regex patterns (more tolerant to varying whitespace)
cpu_speed_re = re.compile(r"events\s+per\s+second:\s*([0-9.]+)")
total_time_re = re.compile(r"total time:\s*([0-9.]+)s")
total_events_re = re.compile(r"total number of events:\s*(\d+)")
latency_re = {
    "min": re.compile(r"min:\s*([0-9.]+)"),
    "avg": re.compile(r"avg:\s*([0-9.]+)"),
    "max": re.compile(r"max:\s*([0-9.]+)"),
    "95th": re.compile(r"95th percentile:\s*([0-9.]+)"),
    "sum": re.compile(r"sum:\s*([0-9.]+)")
}
fairness_events_re = re.compile(r"events \(avg/stddev\):\s*([0-9.]+)/([0-9.]+)")
fairness_time_re = re.compile(r"execution time \(avg/stddev\):\s*([0-9.]+)/([0-9.]+)")

results = []

for i in range(1,6):
    with open(f"sysbench_cpu_result_{i}.txt", "r") as f:
        block = ""
        for line in f:
            block += line
            if "execution time (avg/stddev)" in line:
                data = {}
                # Extract and check matches
                def safe_match(pattern, label, is_float=True):
                    match = pattern.search(block)
                    if not match:
                        print(f"Warning: '{label}' not found in block")
                        return None
                    return float(match.group(1)) if is_float else int(match.group(1))

                data["events_per_sec"] = safe_match(cpu_speed_re, "events per second")
                data["total_time"] = safe_match(total_time_re, "total time")
                data["total_events"] = safe_match(total_events_re, "total events", is_float=False)

                for key, pattern in latency_re.items():
                    val = safe_match(pattern, f"latency {key}")
                    data[f"latency_{key}"] = val

                # Fairness (events)
                fe = fairness_events_re.search(block)
                if fe:
                    data["fairness_events_avg"] = float(fe.group(1))
                    data["fairness_events_stddev"] = float(fe.group(2))
                else:
                    print("Warning: 'fairness events' not found")
                    continue

                # Fairness (time)
                ft = fairness_time_re.search(block)
                if ft:
                    data["fairness_time_avg"] = float(ft.group(1))
                    data["fairness_time_stddev"] = float(ft.group(2))
                else:
                    print("Warning: 'fairness time' not found")
                    continue

                # Ensure no missing values before appending
                if all(v is not None for v in data.values()):
                    results.append(data)
                else:
                    print("Warning: incomplete block skipped")
                block = ""

# Write to CSV
fieldnames = list(results[0].keys())
with open("sysbench_cpu.csv", "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in results:
        writer.writerow(row)