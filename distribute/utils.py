import os
import tempfile

import paramiko
import re
import time
import threading
import time
from django.utils import timezone
from scp import SCPClient


class DistributeWrapper:

    def __init__(self):
        self.ssh2 = self.connect_ssh('node2', 'mpiuser')
        self.ssh4 = self.connect_ssh('node4', 'mpiuser')
        self.ssh5 = self.connect_ssh('node5', 'mpiuser')
        self.last_heartbeat_times = {'node2': None, 'node4': None, 'node5': None}
        self.heart_beat_thread = threading.Thread(target=self.heart_beat)
        self.stop_heart_beat_event = threading.Event()  # 添加一个 Event 作为停止心跳线程的标志

    def connect_ssh(self, hostname, username):
        """
        利用 paramiko 的ssh客户端创建ssh连接。
        """
        try:
            SSH_PRIVATE_KEY = '/home/ly/.ssh/id_rsa'
            key = paramiko.RSAKey.from_private_key_file(SSH_PRIVATE_KEY)
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(hostname=hostname, username=username, pkey=key)
            print(f"Connected to {hostname} successfully.")
            return ssh_client
        except Exception as e:
            print(f"Error connecting to {hostname}: {e}")
            return None

    def start_heart_beat(self):
        """
        开启心跳监听。
        """
        if not self.heart_beat_thread.is_alive():
            self.stop_heart_beat_event.clear()  # 重置停止心跳线程的标志
            self.heart_beat_thread.start()

    def stop_heart_beat(self):
        """
        停止心跳监听。
        """
        self.stop_heart_beat_event.set()  # 设置停止心跳线程的标志

    def heart_beat(self):
        """
        心跳获取。
        利用ssh客户端的连接是否成功来判断是否有心跳。
        """
        while not self.stop_heart_beat_event.is_set():  # 在每次迭代中检查标志
            self.ssh2 = self.connect_ssh('node2', 'mpiuser')
            self.ssh4 = self.connect_ssh('node4', 'mpiuser')
            self.ssh5 = self.connect_ssh('node5', 'mpiuser')

            # 检查连接是否成功
            if all(ssh is not None for ssh in [self.ssh2, self.ssh4, self.ssh5]):
                print("All connections are successful.")
            else:
                failed_nodes = [node for node, ssh in [('node2', self.ssh2), ('node4', self.ssh4), ('node5', self.ssh5)]
                                if ssh is None]
                print(f"Connection failed for nodes: {failed_nodes}")

            # 记录每个节点的最后心跳时间
            self.last_heartbeat_times['node2'] = timezone.now() if self.ssh2 else None
            self.last_heartbeat_times['node4'] = timezone.now() if self.ssh4 else None
            self.last_heartbeat_times['node5'] = timezone.now() if self.ssh5 else None

            # 间隔 10 秒执行一次连接
            time.sleep(10)

    def get_last_heartbeat_times(self):
        """
        获取每个节点的最后心跳时间。
        """
        return self.last_heartbeat_times

    def get_cpu_info(self, ssh, node_name):
        """
        获取子节点cpu数据。
        """
        try:
            stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep 'Cpu(s)'")
            top_output = stdout.read().decode()
            print(top_output)

            data = self.parse_cpu_info(top_output, node_name)

            return data

        except Exception as e:
            print("错误:", e)
            return []

    def parse_cpu_info(self, top_output, node_name):
        """
        序列化cpu数据。
        """
        lines = top_output.split('\n')
        data = []

        for line in lines:
            if line.startswith("%Cpu(s):"):
                fields = re.split(r'\s+', line)

                # 去除逗号
                fields = [field.replace(',', '') for field in fields]

                # 打印每个CPU状态的详细信息
                print("cpu_info:", fields)

                data.append({
                    'node_name': node_name,
                    'cpu_name': '总体',  # 如果你想获取每个CPU核心的信息，可以进行调整
                    'user': fields[1],
                    'system': fields[3],
                    'nice': fields[5],
                    'idle': fields[7],
                    'iowait': fields[9],
                    'hardirq': fields[11],
                    'softirq': fields[13],
                    'st': fields[15]
                })

        print(f"解析 {node_name} 的CPU信息:", data)
        return data

    def get_memory_info(self, ssh, node_name):
        """
        获取子结点内存数据。
        """
        try:
            stdin, stdout, stderr = ssh.exec_command("free -h")
            memory_info = stdout.read().decode()

            data = self.parse_memory_info(memory_info, node_name)

            return data

        except Exception as e:
            print("Error:", e)
            return []

    def parse_memory_info(self, memory_info, node_name):
        """
        序列化内存数据。
        """
        lines = memory_info.split('\n')
        data = []

        for line in lines:
            if not line:
                continue

            # 检查行中是否包含内存信息，这里仅为示例，实际检测逻辑可能需要更详细的处理
            if line.startswith("Mem:"):
                fields = re.split(r'\s+', line)
                data.append({
                    'node_name': node_name,
                    'total_memory': fields[1],
                    'used_memory': fields[2],
                    'free_memory': fields[3],
                    # 'percent_used': float(fields[2]) / float(fields[1]) * 100
                })

        print(f"Parsed memory data for {node_name}:", data)
        return data

    def get_disk_info(self, ssh, node_name):
        """
        获取子结点磁盘数据。
        """
        try:
            # 获取node2磁盘信息
            stdin, stdout, stderr = ssh.exec_command("df -h")
            result = stdout.read().decode()

            data = self.parse_disk_info(result, node_name)

            # 返回所有节点的磁盘信息
            return data

        except Exception as e:
            print("Error:", e)
            return []

    def parse_disk_info(self, result, node_name):
        """
        序列化磁盘数据。
        """
        # 使用正则表达式提取每个字段
        lines = result.split('\n')
        data = []

        for line in lines:
            # 跳过空行
            if not line:
                continue

            fields = re.split(r'\s+', line)

            # 检查字段数量是否足够
            if len(fields) >= 6 and fields[0] != '文件系统':
                data.append({
                    'node_name': node_name,
                    'filesystem': fields[0],
                    'size': fields[1],
                    'used': fields[2],
                    'free': fields[3],
                    'percent': fields[4],
                    'mounted_on': fields[5]
                })

        print(f"Parsed data for {node_name}:", data)
        return data


class DistributeClient:
    distribute_client = DistributeWrapper()
