import re
import csv

input_file = "sysbench_memory_output.log"  # Change if needed
output_file = "sysbench_memory_metrics.csv"

# Regex patterns
ops_total_re = re.compile(r"Total operations:\s+(\d+)\s+\(([0-9.]+) per second\)")
transfer_re = re.compile(r"([\d.]+) MiB transferred \(([\d.]+) MiB/sec\)")
total_time_re = re.compile(r"total time:\s+([\d.]+)s")
latency_re = {
    "min": re.compile(r"min:\s*([\d.]+)"),
    "avg": re.compile(r"avg:\s*([\d.]+)"),
    "max": re.compile(r"max:\s*([\d.]+)"),
    "95th": re.compile(r"95th percentile:\s*([\d.]+)"),
    "sum": re.compile(r"sum:\s*([\d.]+)")
}
fairness_events_re = re.compile(r"events \(avg/stddev\):\s*([\d.]+)/([\d.]+)")
fairness_time_re = re.compile(r"execution time \(avg/stddev\):\s*([\d.]+)/([\d.]+)")

results = []

for i in range(1,6):
    with open(f"sysbench_mem_result_{i}.txt", "r") as f:
        block = ""
        for line in f:
            block += line
            if "execution time (avg/stddev)" in line:
                data = {}

                def safe_match(pattern, label, group_index=1):
                    match = pattern.search(block)
                    if not match:
                        print(f"Warning: '{label}' not found.")
                        return None
                    return float(match.group(group_index))

                # Extract metrics
                data["total_operations"] = safe_match(ops_total_re, "total operations", 1)
                data["ops_per_sec"] = safe_match(ops_total_re, "ops per second", 2)

                data["transfer_mib"] = safe_match(transfer_re, "transfer MiB", 1)
                data["transfer_rate_mibs"] = safe_match(transfer_re, "transfer rate MiB/sec", 2)

                data["total_time"] = safe_match(total_time_re, "total time")

                for key, pattern in latency_re.items():
                    data[f"latency_{key}"] = safe_match(pattern, f"latency {key}")

                fe = fairness_events_re.search(block)
                if fe:
                    data["fairness_events_avg"] = float(fe.group(1))
                    data["fairness_events_stddev"] = float(fe.group(2))
                else:
                    print("Warning: fairness events not found.")
                    continue

                ft = fairness_time_re.search(block)
                if ft:
                    data["fairness_time_avg"] = float(ft.group(1))
                    data["fairness_time_stddev"] = float(ft.group(2))
                else:
                    print("Warning: fairness time not found.")
                    continue

                if all(v is not None for v in data.values()):
                    results.append(data)
                else:
                    print("Warning: incomplete block skipped")
                block = ""

# Write CSV output
if results:
    fieldnames = list(results[0].keys())
    with open("mem.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"✅ Memory metrics saved to '{output_file}'")
else:
    print("⚠️ No valid memory test data extracted.")
