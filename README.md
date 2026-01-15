# TrafficFlow-Analyzer
A lightweight Python network traffic log analyzer. It reads sFlow/NetFlow-style CSV flow records and produces top talkers/listeners, protocol distribution, top application ports, and a sampling-aware total traffic estimate. It also exports results to Excel, generates PNG visualizations, and writes a plain-text report.
Key Features
1) Top Talkers / Top Listeners (by packet count)

Top Talkers: most frequent src_IP

Top Listeners: most frequent dst_IP

Optional reverse DNS lookup (socket.gethostbyaddr) to attach a best-effort Organisation/hostname label (may fail and fall back to Unknown)

Excel output:

4A_Talkers: Rank, IP address, # of packets, Organisation

4A_Listeners: Rank, IP address, # of packets, Organisation


2) Transport Protocol Breakdown (IP protocol field)

Counts IP_protocol values (e.g., 6/TCP, 17/UDP) and maps common protocol numbers via an internal PROTO_MAP

Outputs both packet counts and percentages of total traffic

Excel output:

4B_Transport: Header value, Transport layer protocol, # of packets, % of total


3) Top Applications / Services (by destination port)

Finds the most common dst_port values (Top-N)

Maps common ports to service names using an internal PORT_MAP (HTTP/HTTPS/DNS/SSH, etc.); unknown ports remain Unknown

Excel output:

4C_Applications: Destination IP port number, # of packets, Service


4) Sampling-aware Total Traffic Estimation

Estimates total bytes using packet_size × sampling_rate per record (useful for sampled telemetry exports)

Reports totals in both:

MB (decimal) = bytes / 1e6

MiB (binary) = bytes / 1024²

If sampling_rate is missing or 0, the script uses --default-sampling (default: 2048)

Excel output:

4D_Traffic: Total Traffic (MB, 10^6), Total Traffic (MiB, 1024^2)


5) Top Bidirectional Communication Pairs

Treats (src_IP, dst_IP) as an undirected pair by sorting the two IPs so that A→B and B→A are aggregated together

Outputs Top-N communication pairs ranked by total packet counts

Excel output:

4E_Pairs: # of packets, Host1, Host2



Visual Outputs (PNG)

The script generates three figures (filenames are currently hardcoded in the script):

lab4_4E_bar.png

Horizontal bar chart of top bidirectional pairs (packet counts)

lab4_4E_talker_network.png

Star-shaped network graph: Top Talker → its main targets

Edge width encodes traffic volume

lab4_4E_listener_network.png

Star-shaped network graph: Sources → Top Listener

Edge width encodes traffic volume



Text Report Output (TXT)

lab4_report.txt

Prints the Top bidirectional pairs table (pair_counts.to_string())

Lists the generated PNG filenames

Note: The report header string in the script currently contains legacy wording. You can rename it to any project-specific title by editing the corresponding write() line.



Input CSV Format

The script assumes the CSV has no header row and supports two layouts by checking the number of columns in the first line:


20-column layout (default)

type

sflow_agent_address

inputPort

outputPort

src_MAC

dst_MAC

ethernet_type

in_vlan

out_vlan

src_IP

dst_IP

IP_protocol

ip_tos

ip_ttl

src_port

dst_port

tcp_flags

packet_size

IP_size

sampling_rate

21-column layout

If 21 columns are detected, an extra trailing column named extra is added (core analysis is unaffected).


Installation
pip install pandas matplotlib networkx xlsxwriter


Usage
python lab4_analyzer.py Data_2.csv --top 5 --default-sampling 2048



Arguments:

csv_path (positional): path to the input CSV log

--top: Top-N size (default: 5)

--default-sampling: fallback sampling rate when missing/0 (default: 2048)

Outputs created in the working directory:

lab4_results.xlsx

lab4_report.txt

lab4_4E_bar.png

lab4_4E_talker_network.png

lab4_4E_listener_network.png
