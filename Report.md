# Comparative Performance Evaluation of Virtual Machine (VirtualBox) and Container (Docker) Environments

**Author:** Giovanni Lucarelli


## Table of Contents


- [Table of Contents](#table-of-contents)
- [Introduction](#introduction)
- [Methodology](#methodology)
  - [Host System Specifications](#host-system-specifications)
  - [Virtual Machine (VM) Setup](#virtual-machine-vm-setup)
    - [Template Machine Configuration](#template-machine-configuration)
    - [Network Adapters Configuration](#network-adapters-configuration)
    - [Master Node Configuration](#master-node-configuration)
    - [Worker Nodes Configuration](#worker-nodes-configuration)
  - [Container Setup](#container-setup)
    - [Template Machine Configuration (Dockerfile)](#template-machine-configuration-dockerfile)
    - [Cluster Configuration (Docker Compose)](#cluster-configuration-docker-compose)
    - [Starting the Cluster](#starting-the-cluster)
  - [Benchmarking Tools](#benchmarking-tools)
  - [Testing Procedures](#testing-procedures)
    - [CPU Benchmarking](#cpu-benchmarking)
- [Results and Discussion](#results-and-discussion)
- [Conclusion](#conclusion)

## Introduction

The objective of this project is to conduct a comparative performance evaluation of Virtual Machines (VMs) and Containers, specifically focusing on VirtualBox and Docker. The evaluation will be based on a series of benchmarks that measure various performance metrics, including CPU, memory, disk I/O, and network throughput. 
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

#### Template Machine Configuration

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

#### Network Adapters Configuration

The network configuration is done using the VirtualBox GUI. Two network adapters are created:
1. **Adapter 1**: NAT, which allows the master to access the Internet through the host machine.
2. **Adapter 2**: Internal Network, which allows the VMs to communicate with each other. To each VM is assigned a dynamic IP address.

The port forwarding is configured in the VirtualBox GUI, so that the SSH service can be accessed from the host machine. The following ports are used:

| Name | Protocol | Host IP | Host Port | Guest Port |
|------|----------|---------|-----------|------------|
| ssh | TCP | 127.0.0.1 | 3333 | 22 |

The SSH service is configured to allow the host machine to connect to the VMs using the following command (after starting the master VM):

```{bash}
// on the host machine
ssh-keygen
cd ~/.ssh
scp -P 3333 key_id.pub user01@127.0.0.1:~
```

In this way it is possible to connect to the master VM using the following command:

```{bash}  
ssh -p 3333 user01@127.0.0.1
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

>**Note**:
>Disabling cloud-init ensures your netplan changes remain after reboot.
>```
>sudo touch /etc/cloud/cloud-init.disabled
>```

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

Analogously to the master node, the hostname of the worker nodes has been changed using the following command:

```{bash}
sudo nano /etc/hostname
```
The hostname has been changed from `template` to `node01`. 

**Network Configuration**

The network configuration file, located in `/etc/netplan/50-cloud-init.yaml`, it has been modified as follows:

```{yaml}
network:
  ethernets:
    enp0s8:
      dhcp4: true
      dhcp-identifier: mac
      nameservers:
        addresses: [192.168.0.1]
      routes:
        - to: 0.0.0.0/0
          via: 192.168.0.1
```

and applied using

```{bash}
sudo netplan apply
```
The DNS server has been configured using:

```{bash}
sudo ln -fs /run/systemd/resolve/resolv.conf /etc/resolv.conf
```

**SSH Configuration**

In order to access the worker nodes through the master (not from the host, because of the internal network), the SSH service has been configured using the following command:

```{bash}
// on the master node
ssh-keygen -t rsa -b 4096
ssh-copy-id node01
```

after doing this it is possible to access the worker nodes using

```{bash}
ssh node01
```

**Distributed File System Configuration**

To create a mount point for the shared directory, the following command is used:
```
sudo mkdir /shared
```
then to Mount the shared directory from the master node to this folder:
```
sudo mount 192.168.0.1:/shared /shared
```

and to make the mount persistent across reboots the package AutoFS is installed

```{bash}
sudo apt -y install autofs
```

then in the `auto.master` configuration file the following line has been added in order to include the mount point

```
/- /etc/auto.mount
```

In order to define the NFS mount the AutoFS configuration file (`auto.mount`) has been created and the following line has been added:
```yaml
/shared -fstype=nfs,rw  192.168.0.1:/shared
```

and to apply changes

```
sudo systemctl restart autofs
```

**Clone the Worker Node**

The second worker node has been cloned from the first one after its configuration. The hostname of the second worker node has been changed in the usual way in `node02`. 

### Container Setup

Firt of all, the Docker service has been installed according to the documentation available at [docker website](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository).

#### Template Machine Configuration (Dockerfile)

The Dockerfile is used to create the image of the container. The content of the Dockerfile is as follows:

```{dockerfile}
FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential wget curl \
    openssh-server rsync iputils-ping \
    dnsmasq ssh iptables-persistent \
    iozone3 iperf3 netcat-openbsd \
    stress-ng sysbench openmpi-bin libopenmpi-dev hpcc \
    nfs-common nfs-kernel-server sudo \
    && rm -rf /var/lib/apt/lists/*

# Add the user
RUN useradd -m -s /bin/bash user01 && echo "user01:0000" | chpasswd \
    && echo "user01 ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Create SSH directory and generate keys for user01
RUN mkdir -p /home/user01/.ssh && \
    ssh-keygen -t rsa -N '' -f /home/user01/.ssh/id_rsa && \
    cat /home/user01/.ssh/id_rsa.pub > /home/user01/.ssh/authorized_keys && \
    chmod 700 /home/user01/.ssh && \
    chmod 600 /home/user01/.ssh/id_rsa /home/user01/.ssh/authorized_keys && \
    chown -R user01:user01 /home/user01/.ssh

# Copy the public key to a shared location (optional)
RUN cp /home/user01/.ssh/id_rsa.pub /tmp/user01_rsa.pub

# Create the directory for privilege separation
RUN mkdir -p /run/sshd

# Generating the host keys is important for SSH to work properly
# The -A flag generates all the default keys
RUN ssh-keygen -A

# Expose the SSH port
EXPOSE 22

# Switch to user01
USER user01
WORKDIR /home/user01

# Start the SSH server
# The -D flag runs the server in the foreground
# The -e flag enables logging to stderr
CMD ["sudo", "/usr/sbin/sshd", "-D", "-e"]

```

#### Cluster Configuration (Docker Compose)

The cluster is built using Docker Compose. The `docker-compose.yml` file is as follows:

```{yaml}
services:
  cluster01:
    build: .
    container_name: cluster01
    hostname: cluster01
    networks:
      internal-net:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
    ports:
      - "2220:22"
    volumes:
      - shared-data:/shared

  node01:
    build: .
    container_name: node01
    hostname: node01
    depends_on:
      - cluster01
    networks:
      internal-net:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
    ports:
      - "2221:22"
    volumes:
      - shared-data:/shared


  node02:
    build: .
    container_name: node02
    hostname: node02
    depends_on:
      - cluster01
    networks:
      internal-net:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
    ports:
      - "2222:22"
    volumes:
      - shared-data:/shared

networks:
  internal-net:
    driver: bridge

volumes:
  shared-data:
    driver: local
```

#### Starting the Cluster
The cluster is started using the following command:

```{bash}
docker-compose --build up -d
```
This command will build the images and start the containers in detached mode. The containers can be accessed using the following command:

```{bash}
docker exec -it cluster01 bash
# or
ssh -p 2220 user01@localhost
```
In order to give the user01 the permission to access the shared directory, the following command is used:

```{bash}
sudo chown -R user01:user01 /shared
```

In order to access the each node from each other, the SSH service has been configured manually using , from `cluster01` for example:

```{bash}
ssh node01
exit
ssh node02
exit
```

and analogously for the other nodes.

### Benchmarking Tools
In order to perform the analysis the following tools have been used:

//TODO: write about each benchmarking score and its semantic meaning

- **CPU benchmarking**: HPC Challenge Benchmark for high-performance computation benchmarking
- **General System Test**: `stress-ng` and `sysbench` to evaluate CPU and memory performance.
- **Disk I/O Test**: Use `iozone` to test local and NFS filesystem I/O.
- **Network Test**: `iperf` to measure network throughput and latency between nodes.

### Testing Procedures
In order to have meaningful measurements, the tests have been performed in a controlled environment. The following steps have been followed:
1. The host machine has been rebooted before starting the tests.
2. The VMs and containers have been started and the tests have been performed in the same order for both environments.
3. Same version of the tools have been used in both environments, and the same parameters have been used for the tests.
4. Ensured that no other heavy processes were running on the host machine during the tests.
5. Each test has been performed 5 times and the average value has been taken into account, in order to reduce the impact of random fluctuations in the measurements.
6. Each benchmark has been tested on: VMs, containers and local host (when possible, *i.e.* ...)

>**Note:** Since both the VMs and containers are running on the same OS, the same scripts have been used to perform the tests.

Since we're testing the cluster environment and most of the tests need passwordless ssh protocol (from master to workers) is a good practice to run the following command befor running the tests (both no VMs and containers):

```
mpirun -np 4 -hostfile hosts hostname
```

the expected output is

```
node01
node01
node02
node02
```

#### CPU Benchmarking

##### HPCC

The configuration file for the HPCC:

```
HPLinpack benchmark input file
Innovative Computing Laboratory, University of Tennessee
HPL.out      output file name (if any) 
6            device out (6=stdout,7=stderr,file)
1            # of problems sizes (N)
20352         Ns
1            # of NBs
192           NBs
0            PMAP process mapping (0=Row-,1=Column-major)
1            # of process grids (P x Q)
2            Ps
2            Qs
16.0         threshold
1            # of panel fact
2            PFACTs (0=left, 1=Crout, 2=Right)
1            # of recursive stopping criterium
4            NBMINs (>= 1)
1            # of panels in recursion
2            NDIVs
1            # of recursive panel fact.
1            RFACTs (0=left, 1=Crout, 2=Right)
1            # of broadcast
1            BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)
1            # of lookahead depth
1            DEPTHs (>=0)
2            SWAP (0=bin-exch,1=long,2=mix)
64           swapping threshold
0            L1 in (0=transposed,1=no-transposed) form
0            U  in (0=transposed,1=no-transposed) form
1            Equilibration (0=no,1=yes)
8            memory alignment in double (> 0)
##### This line (no. 32) is ignored (it serves as a separator). ######
0                               Number of additional problem sizes for PTRANS
1200 10000 30000                values of N
0                               number of additional blocking sizes for PTRANS
40 9 8 13 13 20 16 32 64        values of NB
```

and the test has been repeated three times using the command:

```
mpirun -np 4 -hostfile hosts hpcc
```

##### stress-ng

basic stressng command

```
mpirun -np 4 -hostfile hosts stress-ng --cpu 1 --timeout 60s --metrics-brief | tee stress_ng_cpu_results.txt
mpirun -np 4 -hostfile hosts stress-ng --vm 1 --vm-bytes 1G --timeout 60s --metrics-brief | tee stress_ng_vm_results.txt
mpirun -np 4 -hostfile hosts stress-ng --hdd 1 --timeout 60s --metrics-brief | tee stress_ng_hdd_results.txt
```

advanced stress-ng bash script to repeat the experiment multiple times

```
#!/bin/bash

# File hosts MPI
HOSTFILE="hosts"

# number of repetitions for each test
REPEAT=5

# duration of each test
DURATION="60s"

# function to execute the test
run_test() {
    local TEST_TYPE=$1
    local OPTIONS=$2
    for i in $(seq 1 $REPEAT); do
        echo "Esecuzione $i - Test: $TEST_TYPE"
        mpirun -np 2 -hostfile "$HOSTFILE" stress-ng $OPTIONS --timeout "$DURATION" --metrics-brief \
            | tee "stress_ng_${TEST_TYPE}_results_${i}.txt"
        echo "---- Completato: stress_ng_${TEST_TYPE}_results_${i}.txt ----"
        echo ""
    done
}

# CPU: 2 workers per node
run_test "cpu" "--cpu 2"

# RAM: 1 worker with 1GB per node
run_test "vm" "--vm 1 --vm-bytes 1G"

# HDD ???
```

##### sysbench

Basic command

```bash
mpirun -np 4 -hostfile hosts sysbench --test=cpu --cpu-max-prime=20000 run | tee sysbench_cpu_results.txt
mpirun -np 4 -hostfile hosts sysbench --test=memory --memory-total-size=10G run | tee sysbench_mem_results.txt
```

bash script to repeat the experiment multiple times

##### iozone

test the the local filesystem:
```bash
iozone -a -R -O | tee iozone_results.txt
```

test the sared file system
```bash
touch /shared/testfile
nano machines.txt
```

I modify the file to obtain:
```
node01 /shared /usr/bin/iozone 
node02 /shared /usr/bin/iozone
```

```bash
export ssh=rsh
iozone -+m /shared/machines.txt -f /shared/testfile -a -R -O | tee iozone_shared_results.txt
```


##### iperf

Basic commands

On master node:

```bash
sudo killall iperf3 
iperf3 -s | tee iperf3_results.txt
```

On worker nodes:

```bash
iperf3 -c cluster01 # TCP test
iperf3 -c cluster01 -u #UDP test
iperf3 -c cluster01 -R # Reverse test: the client receives
```

bash script to repeat the experiment multiple times


## Results and Discussion

## Conclusion
