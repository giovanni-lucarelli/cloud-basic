# Comparative Performance Evaluation of Virtual Machine (VirtualBox) and Container (Docker) Environments for a Cluster of Nodes

## Table of Contents
- [Comparative Performance Evaluation of Virtual Machine (VirtualBox) and Container (Docker) Environments for a Cluster of Nodes](#comparative-performance-evaluation-of-virtual-machine-virtualbox-and-container-docker-environments-for-a-cluster-of-nodes)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Methodology](#methodology)
    - [Host System Specifications](#host-system-specifications)
    - [Virtual Machine (VM) Setup](#virtual-machine-vm-setup)
      - [Template Machine Creation](#template-machine-creation)
      - [Network Adapters and Port Forwardig](#network-adapters-and-port-forwardig)
      - [Master Node Configuration](#master-node-configuration)
      - [Worker Nodes Configuration](#worker-nodes-configuration)
    - [Container Setup](#container-setup)
    - [Benchmarking Tools](#benchmarking-tools)
    - [Test Procedures](#test-procedures)
  - [Results and Discussion](#results-and-discussion)
  - [Conclusion](#conclusion)


## Introduction

Contemporary computing relies heavily on technologies that optimize resource allocation and application management. Virtualization, primarily implemented via Virtual Machines (VMs), provides hardware abstraction, allowing the execution of multiple, fully independent guest operating systems on a single physical host, ensuring strong isolation. In contrast, containerization, exemplified by Docker, offers OS-level virtualization. It isolates application processes within containers that share the host's kernel but have their own filesystem and dependencies, resulting in lower overhead and faster instantiation. The widespread adoption of both VMs and containers underscores their importance in enabling server consolidation, simplifying deployment pipelines, facilitating microservices architectures, and forming the bedrock of cloud-based services.

The objective of this project is to conduct a comparative performance evaluation of Virtual Machines (VMs) and Containers, specifically focusing on VirtualBox and Docker. The evaluation will be based on a series of benchmarks that measure various performance metrics, including CPU, memory, disk I/O, and network throughput. The report is structured as follows:
1. **Methodology**: This section outlines the specifications of the host system, the setup of the virtual machines and containers, and the benchmarking tools used for the evaluation.
2. **Results and Discussion**: This section presents the results of the performance benchmarks, along with a discussion of the implications of these results.
3. **Conclusion**: This section summarizes the key findings of the report and provides recommendations for future work.

## Methodology

### Host System Specifications 

    CPU Model: Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz
    Cores / Threads: 4 Cores / 8 Threads (4 cores x 2 threads/core)
    RAM: 8 GB
    Disk: SanDisk SD9SN8W2 (256 GB SSD)
    Operating System: Ubuntu 24.04.2 LTS
    Kernel Version: Linux 6.11.0-21-generic 


### Virtual Machine (VM) Setup

The cluster is built in Oracle VirtualBox (`version ???`) and it is made up by one master node `cluster01` and two worker nodes, namely `node01` and `node02`. The three of them are interconnected using an internal network and the workers inherited the Internet access through the master node, which act as DNS, DHCP and gateway of the cluster.

#### Template Machine Creation

All the VMs have the same specifications:

    # CPU: 2
    RAM: 2048 MB
    Disk: 20 GB
    Operating System: Ubuntu 22.04.5 live server (amd64)

and they are built as clones of the same "template". After completing the installation of the OS in the template VMs, it has been configured using the following commands:

```{bash}

sudo apt update && sudo apt upgrade

sudo apt install build-essential wget curl \\
# network service
dnsmasq ssh iptables-persistent\\
# assessment
iozone3 iperf3 netcat stress-ng sysbench openmpi-bin libopenmpi-dev hpcc \\
nof-common nfs-kernel-server

sudo shutdown -h now
```

The assessment tools are described in details in section {#test-procedures}. 
The template VM has been cloned to create `cluster01` (master) and `node01` (worker); the second worker has been cloned from the first one after its conficuration. 

> **Note:** when cloning the template VM, it is important to select the option "Reinitialize the MAC address of all network cards" in order to avoid conflicts in the network configuration.

#### Network Adapters and Port Forwardig 

The network configuration is done using the VirtualBox GUI. Two network adapters are created:
1. **Adapter 1**: NAT, which allows the master to access the Internet through the host machine.
2. **Adapter 2**: Internal Network, which allows the VMs to communicate with each other. To each VM is assigned a dynamic IP address.

The port forwarding is configured in the VirtualBox GUI, so that the SSH service can be accessed from the host machine. The following ports are used:

| Name | Protocol | Host IP | Host Port | Guest Port |
|------|----------|---------|-----------|------------|
| ssh | TCP | 127.0.0.1 | 2222 | 22 |

The SSH service is configured to allow the host machine to connect to the VMs using the following command (after starting the master VM):

```{bash}
// on the host machine
ssh-keygen
cd ~/.ssh
scp -P 2222 key_id.pub user01@127.0.0.1:~
```

In this way it is possible to connect to the master VM using the following command:

```{bash}  
ssh -p 2222 user01@127.0.0.1
```

#### Master Node Configuration

Since the node has been copied from the template, it has the same username, password but also the same hostname. In order to avoid conflicts, the hostname of the master node has been changed using the following command:

```{bash}
sudo nano /etc/hostname
```
The hostname has been changed from `template` to `cluster01`. The same change has been done in the `/etc/hosts` file. 

```{yaml}
127.0.0.1 localhost
192.168.0.1 master
```

then the VM has been restarted in order to apply the changes.

The master node is configured to act as DNS, DHCP and gateway of the cluster. The network interfaces available on the master node are:

| Name | Type |
|------|------|
| enp0s3 | NAT |
| enp0s8 | Internal Network |

The configuration is done using the `netplan` tool. The configuration file is located in `/etc/netplan/50-cloud-init.yaml` and it is as follows:

```{yaml}
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      dhcp4: false
      addresses: [192.168.0.1/28]
      nameservers:
        addresses: [192.168.0.1]
```

in order to apply the configuration, the following command is used:

```{bash}
sudo netplan apply
```

**DNS Configuration**

The DHCP server is configured using the `dnsmasq` tool. The configuration file is located in `/etc/dnsmasq.conf` and it is as follows:

```{yaml}
port=53
bogus-priv
strict-order
interface=enp0s8
listen-address=::1,127.0.0.1,192.168.0.1
bind-interfaces
log-queries
log-dhcp
dhcp-range=192.168.0.2,192.168.0.14,255.255.255.240,12h
dhcp-option=option:dns-server,192.168.0.1
dhcp-option=3
```

in order to control the way `dnsmasq` interacts with `resolv.conf`, the following lines have been uncommented in the `/etc/default/dnsmasq` file:

```{yaml}
IGNORE_RESOLVCONF=yes
DNSMASQ_EXCEPT="lo"
```
the application of the changes is done using the following command:

```{bash}
sudo systemctl restart dnsmasq systemd-resolved
```

**Gateway Configuration**

The gateway is configured by creating the file `etc/sysctl.d/99-sysctl.conf` with the following content:

```{yaml}
net.ipv4.ip_forward=1
```
and then applying the changes using the following command:

```{bash}
sudo sysctl --system
```

To configure the IP tables, the following command is used:

```{bash}
sudo iptables -t nat -A POSTROUTING -o enp0s3 -j MASQUERADE
sudo netfilter-persistent save
```

**Distributed File System Configuration**

A shared directory is created in the master node using the following command:

```{bash}
sudo mkdir /shared
sudo chmod 777 /shared
sudo nano /etc/exports
```

The content of the `/etc/exports` file is as follows:

```{yaml}
/shared/ 192.168.0.0/255.255.255.240(rw,sync,no_root_squash,no_subtree_check)
```

and then the NFS service is enabled and restarted using the following command:

```{bash}
sudo systemctl enable nfs-kernel-server
sudo systemctl restart nfs-kernel-server
```

#### Worker Nodes Configuration

### Container Setup

### Benchmarking Tools
### Test Procedures

## Results and Discussion
## Conclusion
