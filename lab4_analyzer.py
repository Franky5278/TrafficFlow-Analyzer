#这个lab code让我查找了大量的原理资料，尤其是对依赖的初步理解，涉及到原理的代码我反复写了好几次
#!/usr/bin/env python3     让类 Unix 系统用 python3 解释器运行此文件（命令行直接执行时有效）
# -*- coding: utf-8 -*-    源文件编码声明：确保中文注释/字符串能被正确解析
"""
Lab 4 Traffic Log Analyzer (sFlow/NetFlow CSV)
Exercises 4A–4E, 输出 Excel / PNG / TXT 到脚本同目录
"""

# import 依赖
import argparse                 # 解析命令行参数，如文件路径，top等
import os                       # 与操作系统交互，生成绝对路径打印
import socket                   # DNS反查域名，IP推出主机名/域名，用于推断Organisation，但我感觉实战上不是很有用，我最后自己手动查的还是
import pandas as pd             # 数据处理
import matplotlib.pyplot as plt # 可视化，一些绘图
import networkx as nx           # 4E 的图片，网络分析+可视化

# 20/21列表头 自动的命名要求设计
EXPECTED_COLS_20 = [
    "type", "sflow_agent_address", "inputPort", "outputPort",
    "src_MAC", "dst_MAC", "ethernet_type", "in_vlan", "out_vlan",
    "src_IP", "dst_IP", "IP_protocol", "ip_tos", "ip_ttl",
    "src_port", "dst_port", "tcp_flags", "packet_size", "IP_size", "sampling_rate"
]
EXPECTED_COLS_21 = EXPECTED_COLS_20 + ["extra"] #我想，如果检测到 21 列，则在末尾补一列名 "extra"

# 常见端口/协议映射
PORT_MAP = {  #查找的目的端口号，常见应用服务名的字典；便于 4C 映射显示
    20: "FTP-Data", 21: "FTP-Control", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    67: "DHCP", 68: "DHCP", 69: "TFTP", 80: "HTTP", 110: "POP3", 123: "NTP",
    143: "IMAP", 161: "SNMP", 443: "HTTPS", 445: "SMB", 3306: "MySQL",
    3389: "RDP", 8080: "HTTP-Alt"
}
PROTO_MAP = {1: "ICMP", 2: "IGMP", 6: "TCP", 17: "UDP", 41: "IPv6", 47: "GRE", 50: "ESP", 89: "OSPF"}
#查找的通用协议号对应的协议名，来源于 IP 报头 Protocol 字段的标准分配

# 辅助函数
def is_ipv4(s: str) -> bool:
    #判断是否合法 IPv4
    try:
        parts = str(s).split(".")  #把值转字符串并按点号分割；IPv4 要有 4 段
        return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
        #条件1：正好 4 段；条件2：每段都是 0..255 的十进制数字
    except Exception:
        return False  #异常按照非法处理

def coerce_numeric(series, default=None):
    #把列转为数值，失败记作 NaN；选用默认值填充
    s = pd.to_numeric(series, errors="coerce")  # pandas 向量化转换；非法字符串变成NaN
    if default is not None:
        s = s.fillna(default)   #若提供 default，用它填 NaN；利于后续计算
    return s

def read_csv_safely(path: str) -> pd.DataFrame:
    #根据首行逗号数选择 20/21 列头读取，兼容无 Header 导出
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline()    #只读首行，粗略估计列数（简单鲁棒性）
    num_tokens = len(first.strip().split(",")) #逗号分割计数（CSV 常见做法）
    cols = EXPECTED_COLS_21 if num_tokens >= 21 else EXPECTED_COLS_20
    return pd.read_csv(path, names=cols, header=None)
    #强制使用定义的列名（names=...），并声明原文件无表头（header=None）

def resolve_org(ip: str) -> str:
    #反查 Organisation（主机名/域名），失败返回 Unknown
    try:
        return socket.gethostbyaddr(ip)[0]  #反向解析 PTR 记录：IP推断 主机名；返回元组第 0 项是主机名
    except Exception:
        return "Unknown"   #这里如果有DNS 失败/私网地址等情况，就返回 Unknown

# 主要的函数
def analyze(csv_path: str, top_n: int, default_sampling: int):
    df = read_csv_safely(csv_path)

    # 数值清洗
    for col in ["packet_size", "IP_size", "sampling_rate", "IP_protocol", "src_port", "dst_port"]:
        df[col] = coerce_numeric(df[col])
    df["sampling_rate"] = df["sampling_rate"].fillna(default_sampling).replace(0, default_sampling)

    # 4A：Top Talkers & Listeners（含 Organisation）
    src_mask = df["src_IP"].astype(str).apply(is_ipv4) #这个是布尔掩码，用于筛出合法源 IP 行
    dst_mask = df["dst_IP"].astype(str).apply(is_ipv4) #布尔掩码：筛出合法源 IP 行

    talkers = df.loc[src_mask, "src_IP"].value_counts().head(top_n) #统计出现次数最多的源 IP（按包数计数）并取前 N
    listeners = df.loc[dst_mask, "dst_IP"].value_counts().head(top_n) #同理：目的 IP 的出现次数（收到的包）

    talkers_df = (
        talkers.reset_index()
               .rename(columns={"index": "IP address", "src_IP": "IP address",  "count": "# of packets"})
    )
    # value_counts() 返回 Series，索引是 IP，需要 reset_index() 变成两列；统一列名为模板需要的标题
    talkers_df.insert(0, "Rank", range(1, len(talkers_df) + 1))  #在第0列插入排名（1..N）
    talkers_df["# of packets"] = talkers_df["# of packets"].astype(int)  #计数为整型
    talkers_df["Organisation"] = talkers_df["IP address"].apply(resolve_org)  # DNS 反查主机名/机构

    listeners_df = (
        listeners.reset_index()
                 .rename(columns={"index": "IP address", "dst_IP": "IP address", "count": "# of packets"})
    )
    listeners_df.insert(0, "Rank", range(1, len(listeners_df) + 1))
    listeners_df["# of packets"] = listeners_df["# of packets"].astype(int)
    listeners_df["Organisation"] = listeners_df["IP address"].apply(resolve_org)

    # 4B：Transport Layer Protocol（百分比两位小数）
    proto_counts = (
        df["IP_protocol"].dropna().astype(int).value_counts().sort_values(ascending=False)
    )
    
    #这里要对 IP 报头的 Protocol 字段计数（去 NaN，转 int），得到各协议包数，这里折了几次
    proto_df = pd.DataFrame({
        "Header value": proto_counts.index,
        "Transport layer protocol": [PROTO_MAP.get(int(v), "Other/Unknown") for v in proto_counts.index],
        "# of packets": proto_counts.values
    })
    total_proto = int(proto_df["# of packets"].sum())
    proto_df["% of total"] = proto_df["# of packets"].apply(
        lambda x: f"{(x / total_proto * 100):.2f}%" if total_proto > 0 else "0.00%"
    )
    # 计算百分比并格式化为字符串保留两位小数；避免除零

    # 4C：应用层端口（目的端口 TopN + 服务名）
    dst_port_counts = df["dst_port"].dropna().astype(int).value_counts().head(top_n)
    # 统计最常见的目的端口
    app_df = pd.DataFrame({
        "Destination IP port number": dst_port_counts.index,
        "# of packets": dst_port_counts.values,
        "Service": [PORT_MAP.get(int(p), "Unknown") for p in dst_port_counts.index]
    })

    # 4D：估算总流量（链路层口径：packet_size × sampling_rate）
    DURATION_SECONDS = 15  # 监测窗口（仅用于可选的平均吞吐率）
    DEFAULT_SAMPLING = default_sampling  # 与前面保持一致，例：2048

    # 列的清洗：确保为数值、补空、把 0 采样率回填为默认值
    df["packet_size"]   = coerce_numeric(df["packet_size"],   default=0)
    df["sampling_rate"] = coerce_numeric(df["sampling_rate"], default=DEFAULT_SAMPLING)
    df["sampling_rate"] = df["sampling_rate"].replace(0, DEFAULT_SAMPLING)

    # 放大抽样、累加得到总字节 sFlow 是“1/N 采样”
    estimated_total_bytes = (df["packet_size"] * df["sampling_rate"]).sum()

    # 因为对原来的题目理解有疑惑，我打算用两种单位同步计算
    # 十进制 MB
    total_mb = estimated_total_bytes / 1_000_000
    # 二进制 MiB
    total_mib = estimated_total_bytes / (1024 * 1024)
    
    # 4E-1: 双向通信对的统计（Host1/Host2）
    pairs = df.loc[src_mask & dst_mask, ["src_IP", "dst_IP"]].copy()
    pairs["Pair"] = pairs.apply(lambda row: tuple(sorted([row["src_IP"], row["dst_IP"]])), axis=1)
    #对 (src, dst) 排序后作为无向对（Host1, Host2），这样双向都可以计入同一“配对”
    pair_counts = (
        pairs["Pair"].value_counts()
             .reset_index(name="# of packets")
             .rename(columns={"index": "Pair"})
             .head(top_n)
    )

    # 拆列并重命名为 Host1 / Host2
    pair_counts[["Host1", "Host2"]] = pd.DataFrame(pair_counts["Pair"].tolist(), index=pair_counts.index)
    pair_counts.drop(columns=["Pair"], inplace=True)
    pair_counts["# of packets"] = pair_counts["# of packets"].astype(int)

    # 4E-2: 条形图可视化（Top 双向通信对）
    pair_counts["Pair"] = pair_counts.apply(lambda r: f"({r['Host1']}, {r['Host2']})", axis=1)

    plt.figure(figsize=(10, 5))
    plt.barh(pair_counts["Pair"], pair_counts["# of packets"], color="cornflowerblue", edgecolor="black")
    plt.gca().invert_yaxis()
    plt.xlabel("Total Number of Packets (Bidirectional)")
    plt.ylabel("Communication Pair (Host1, Host2)")
    plt.title("Top Communication Pairs (Bidirectional)")
    for i, v in enumerate(pair_counts["# of packets"]):
        plt.text(v + max(pair_counts["# of packets"]) * 0.01, i, str(v), va='center', fontsize=8)
    plt.tight_layout()
    plt.savefig("lab4_4E_bar.png", dpi=300, bbox_inches="tight")
    plt.close()

    # 4E-3: Extra Visualization A – Top Talker 的通信图
    top_talker = talkers_df.iloc[0]["IP address"]
    talker_edges = df.loc[df["src_IP"] == top_talker, ["src_IP", "dst_IP"]].dropna()
    talker_targets = talker_edges["dst_IP"].value_counts().head(10)  # 取前10个目标

    G_talker = nx.DiGraph()
    for dst_ip, count in talker_targets.items():
        G_talker.add_edge(top_talker, dst_ip, weight=count) #边上带权重（包数）

    plt.figure(figsize=(8, 5))
    pos = nx.spring_layout(G_talker, k=0.8)   #弹簧布局：力导向排布
    nx.draw(G_talker, pos,
            with_labels=True,
            node_color="lightgreen",
            node_size=1000,
            font_size=8,
            arrows=True,
            width=[G_talker[u][v]['weight']/talker_targets.max()*3 for u,v in G_talker.edges()])
    
    #这里，边宽按权重归一化（最大值映射到 3 像素）
    plt.title(f"Top Talker ({top_talker}) → Communication Targets")
    plt.tight_layout()
    plt.savefig("lab4_4E_talker_network.png", dpi=300, bbox_inches="tight")
    plt.close()

    #4E-4: Extra Visualization B – Top Listener 的通信图
    top_listener = listeners_df.iloc[0]["IP address"]
    listener_edges = df.loc[df["dst_IP"] == top_listener, ["src_IP", "dst_IP"]].dropna()
    listener_sources = listener_edges["src_IP"].value_counts().head(10)

    G_listener = nx.DiGraph()
    for src_ip, count in listener_sources.items():
        G_listener.add_edge(src_ip, top_listener, weight=count)

    plt.figure(figsize=(8, 5))
    pos = nx.spring_layout(G_listener, k=0.8)
    nx.draw(G_listener, pos,
            with_labels=True,
            node_color="lightcoral",
            node_size=1000,
            font_size=8,
            arrows=True,
            width=[G_listener[u][v]['weight']/listener_sources.max()*3 for u,v in G_listener.edges()])
    plt.title(f"Sources → Top Listener ({top_listener})")
    plt.tight_layout()
    plt.savefig("lab4_4E_listener_network.png", dpi=300, bbox_inches="tight")
    plt.close()

  
    # 保存分析结果到 Excel 与文本
    xlsx_path = "lab4_results.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="xlsxwriter") as writer:
        talkers_df.to_excel(writer, sheet_name="4A_Talkers", index=False)
        listeners_df.to_excel(writer, sheet_name="4A_Listeners", index=False)
        proto_df.to_excel(writer, sheet_name="4B_Transport", index=False)
        app_df.to_excel(writer, sheet_name="4C_Applications", index=False)

# 4D我这里有反复的修改，因为对题意的理解之前有歧义。所以我同时写入 MB（10^6）与 MiB（1024^2），并附带平均速率两种口径
        df_4d = pd.DataFrame({
            "Total Traffic (MB, 10^6)":        [round(total_mb, 2)],
            "Total Traffic (MiB, 1024^2)":     [round(total_mib, 2)],
        })
        df_4d.to_excel(writer, sheet_name="4D_Traffic", index=False)

        pair_counts.to_excel(writer, sheet_name="4E_Pairs", index=False)

    # 最后想写一个文本报告+图片的输出
    txt_path = "lab4_report.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Exercise 4E - Additional Analysis\n")
        f.write("Top Communication Pairs (Bidirectional):\n")
        f.write(pair_counts.to_string(index=False))
        f.write("\n\nVisualizations saved as:\n")
        f.write(" - lab4_4E_bar.png\n")
        f.write(" - lab4_4E_talker_network.png\n")
        f.write(" - lab4_4E_listener_network.png\n")

    print("Done. Results saved as:")
    print(f"Excel : {os.path.abspath(xlsx_path)}")
    print(f"Image : {os.path.abspath('lab4_4E_bar.png')}")
    print(f"Image : {os.path.abspath('lab4_4E_talker_network.png')}")
    print(f"Image : {os.path.abspath('lab4_4E_listener_network.png')}")
    print(f"Text  : {os.path.abspath(txt_path)}")

    
# CLI 入口 
def main():
    parser = argparse.ArgumentParser(description="Analyze Lab 4 sFlow/NetFlow CSV with 4E Visualizations")
    parser.add_argument("csv_path", help="Path to CSV file")
    parser.add_argument("--top", type=int, default=5, help="Top N entries (default=5)")
    parser.add_argument("--default-sampling", type=int, default=2048, help="Default sampling rate (default=2048)")
    args = parser.parse_args()
    analyze(args.csv_path, args.top, args.default_sampling)

if __name__ == "__main__":
    main()
