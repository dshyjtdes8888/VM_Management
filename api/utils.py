import libvirt
import untangle
import time
import threading
import psutil
import subprocess

from rest_framework.exceptions import APIException


class LibvirtWrapper:

    def __init__(self):
        # 初始化到 libvirt 的连接，使用不同的 URI
        self.conn1 = self.connect("qemu:///system")
        self.conn2 = self.connect("qemu+ssh://mpiuser@node2/system")
        self.conn4 = self.connect("qemu+ssh://mpiuser@node4/system")
        self.conn5 = self.connect("qemu+ssh://mpiuser@node5/system")

    def connect(self, uri):
        """
        创建 libvirt 连接。
        """
        try:
            # 尝试连接给定的 URI
            connection = libvirt.open(uri)
            if connection is not None:
                print(f"已连接到 {uri}")
            return connection
        except libvirt.libvirtError as e:
            # 处理连接失败
            print(f"无法连接到 {uri}: {e}")
            return None

    def get_domain(self, domain_name, node_name):
        """
        根据虚拟机名称获取虚拟机对象。
        """
        if node_name == "node2":
            domain = self.conn2.lookupByName(domain_name)
            return domain
        if node_name == "node4":
            domain = self.conn4.lookupByName(domain_name)
            return domain
        if node_name == "node5":
            domain = self.conn5.lookupByName(domain_name)
            return domain

    def shutdown_vm(self, domain_name, node_name):
        """
         关闭虚拟机。如果虚拟机正在运行，发出关闭命令，并等待其关闭。
         优雅关闭。
         """

        def timeout_handler():
            try:
                time.sleep(2)  # Wait for 3 seconds
                if not shutdown_event.is_set():
                    raise TimeoutError("Timeout occurred while waiting for the domain to shut off.")
            except TimeoutError as e:
                self.timeout_exception = e

            shutdown_event.set()

        # 创建一个事件以指示关闭完成
        shutdown_event = threading.Event()

        # 初始化超时异常为 None
        self.timeout_exception = None

        # 启动一个线程处理超时
        timeout_thread = threading.Thread(target=timeout_handler)
        timeout_thread.start()

        domain = self.get_domain(domain_name, node_name)

        # 获取虚拟机当前状态
        state, _ = domain.state()

        if state == libvirt.VIR_DOMAIN_RUNNING:
            domain.shutdown()
        else:
            return

        while True:

            # 检查虚拟机是否已关闭
            if state == libvirt.VIR_DOMAIN_SHUTOFF:
                shutdown_event.set()

            # 如果设置了超时事件，则退出循环
            if shutdown_event.is_set():
                break

            print("Shutting down...")
            # 在再次检查之前短暂休眠
            time.sleep(1)

        # 处理超时异常（如果发生）
        if self.timeout_exception:
            # 对异常进行处理
            self.shutdown_vm(domain_name, node_name)

    def snapshot_vm(self, domain_name, node_name, snapshot_name):
        """
        快照虚拟机。创建虚拟机快照。
        """
        domain = self.get_domain(domain_name, node_name)

        # 获取当前时间戳作为快照名称的一部分
        timestamp = int(time.time())

        # 构建快照XML描述
        snapshot_xml = f"""
        <domainsnapshot>
            <name>{snapshot_name}_{timestamp}</name>
            <description>Snapshot taken at {timestamp}</description>
        </domainsnapshot>
        """

        # 创建虚拟机快照
        try:
            snapshot = domain.snapshotCreateXML(snapshot_xml, 0)
            print(f"Snapshot '{snapshot_name}_{timestamp}' created successfully.")
            return f"{snapshot_name}_{timestamp}"
        except libvirt.libvirtError as e:
            print(f"Failed to create snapshot: {e}")
            raise APIException(detail="Failed to create snapshot.")

    def stop_vm(self, domain_name, node_name):
        """
        暂停虚拟机。将虚拟机置于暂停状态，并等待其完成。
        """
        domain = self.get_domain(domain_name, node_name)
        domain.suspend()

        while True:
            # 获取虚拟机当前状态
            state, _ = domain.state()

            # 检查虚拟机是否已暂停
            if state == libvirt.VIR_DOMAIN_PAUSED:
                break

            # 在再次检查之前短暂休眠
            time.sleep(1)

    def delete_vm(self, domain_name, node_name):
        """
        删除虚拟机。如果虚拟机正在运行，先销毁，然后删除。
        """
        domain = self.get_domain(domain_name, node_name)

        # 检查虚拟机是否正在运行
        if domain.isActive():
            # 如果虚拟机处于活动状态，则在删除之前销毁它
            domain.destroy()

        # 取消定义虚拟机
        domain.undefine()

    def resume_vm(self, domain_name, node_name):
        """
        恢复虚拟机。将暂停的虚拟机恢复运行，并等待其完成。
        """
        domain = self.get_domain(domain_name, node_name)
        domain.resume()

        while True:
            # 获取虚拟机当前状态
            state, _ = domain.state()

            # 检查虚拟机是否已运行
            if state == libvirt.VIR_DOMAIN_RUNNING:
                break

            # 在再次检查之前短暂休眠
            time.sleep(1)

    def start_vm(self, domain_name, node_name):
        """
        启动虚拟机。创建虚拟机并等待其完成启动。
        """
        domain = self.get_domain(domain_name, node_name)
        domain.create()

        while True:
            # 获取虚拟机当前状态
            state, _ = domain.state()

            # 检查虚拟机是否已运行
            if state == libvirt.VIR_DOMAIN_RUNNING:
                break

            # 在再次检查之前短暂休眠
            time.sleep(1)

    def destroy_vm(self, domain_name, node_name):
        """
        强制关闭虚拟机。
        强制关闭。
        """
        domain = self.get_domain(domain_name, node_name)

        try:
            # 强制关闭虚拟机
            domain.destroy()
        except libvirt.libvirtError as e:
            print(f"Error destroying domain {domain_name}: {e}")
            return

        while True:
            # 获取虚拟机当前状态
            state, _ = domain.state()

            # 检查虚拟机是否已关闭
            if state == libvirt.VIR_DOMAIN_SHUTOFF:
                break

            # 在再次检查之前短暂休眠
            time.sleep(1)

        print(f"Domain {domain_name} has been forcefully destroyed.")

    def get_vm_sourse(self, domain_name, node_name):
        """
        获取虚拟机资源利用信息。
        """
        domain = self.get_domain(domain_name, node_name)

        parsed_xml = untangle.parse(domain.XMLDesc())
        ram = int(parsed_xml.domain.memory.cdata) // 1e+6
        cpu = int(parsed_xml.domain.vcpu.cdata)

        # 获取CPU使用百分比
        cpu_percent = psutil.cpu_percent()

        # 获取内存使用情况
        memory = psutil.virtual_memory()

        # 获取磁盘使用情况
        disk = psutil.disk_usage('/')

        return {
            "node_name": node_name,
            "name": domain_name,
            "cpu": cpu,
            "cpu_percent": cpu_percent,
            "memory_total": memory.total // 1e+6,  # 单位为MB
            "memory_used": memory.used // 1e+6,  # 单位为MB
            "memory_percent": memory.percent,
            "disk_total": disk.total // 1e+6,  # 单位为GB
            "disk_used": disk.used // 1e+6,  # 单位为GB
            "disk_percent": disk.percent,
        }

    def get_vm_detail(self, uuid, node_name):
        """
        获取虚拟机详细信息。根据虚拟机 UUID 解析 XML 描述。
        """
        if node_name == "node2":
            domain = self.conn2.lookupByUUID(uuid)
        if node_name == "node4":
            domain = self.conn4.lookupByUUID(uuid)
        if node_name == "node5":
            domain = self.conn5.lookupByUUID(uuid)

        parsed_xml = untangle.parse(domain.XMLDesc())
        # id = int(parsed_xml.domain["id"])
        # 虚拟机名称
        name = parsed_xml.domain.name.cdata
        # 虚拟机uuid
        uuid = parsed_xml.domain.uuid.cdata
        # 虚拟机内存
        ram = int(parsed_xml.domain.memory.cdata) // 1e+6
        # 虚拟机cpu数量
        cpu = int(parsed_xml.domain.vcpu.cdata)
        # 虚拟机状态
        state = domain.state()[0]

        return {
            "node_name": node_name,
            "uuid": uuid,
            "name": name,
            "ram": ram,
            "cpu": cpu,
            "state": state,
        }

    def get_vms(self):
        """
        获取所有虚拟机的详细信息。
        """
        vms = []
        if self.conn2 is not None:
            domains2 = self.conn2.listAllDomains()
            for domain in domains2:
                vms.append(self.get_vm_detail(domain.UUID(), "node2"))
        if self.conn4 is not None:
            domains4 = self.conn4.listAllDomains()
            for domain in domains4:
                vms.append(self.get_vm_detail(domain.UUID(), "node4"))
        if self.conn5 is not None:
            domains5 = self.conn5.listAllDomains()
            for domain in domains5:
                vms.append(self.get_vm_detail(domain.UUID(), "node5"))
        return vms


    def create_vm(self, config, node_name):
        """
        创建虚拟机。通过传入的 XML 配置创建虚拟机，并返回其详细信息。
        """
        if node_name == "node2":
            uuid = self.conn2.createXML(config).UUID()
            return self.get_vm_detail(uuid, node_name)
        if node_name == "node4":
            uuid = self.conn4.createXML(config).UUID()
            return self.get_vm_detail(uuid, node_name)
        if node_name == "node5":
            uuid = self.conn5.createXML(config).UUID()
            return self.get_vm_detail(uuid, node_name)

    def get_snapshot_info(self, snapshot):
        """
        获取虚拟机特定快照的信息。
        """
        snapshot_name = snapshot.getName()
        domain = snapshot.getDomain()
        # description = snapshot.getXMLDesc() # 你可能想要解析XML以获取特定的详细信息

        return {
            "snapshot_name": snapshot_name,
            "domain": domain.name(),
            # "description": description,
        }

    def list_snapshots(self, domain_name, node_name):
        """
        列出虚拟机的所有快照。
        """
        domain = self.get_domain(domain_name, node_name)

        try:
            # 获取快照对象列表
            snapshots = domain.listAllSnapshots()

            snapshot_list = []
            for snapshot in snapshots:
                snapshot_info = self.get_snapshot_info(snapshot)
                snapshot_list.append(snapshot_info)

            print("Snapshot List:", snapshot_info)  # 添加此行进行调试
            return snapshot_list

        except libvirt.libvirtError as e:
            print(f"无法列出快照：{e}")
            raise APIException(detail="无法列出快照。")

    def delete_snapshot(self, domain_name, node_name, snapshot_name):
        """
        删除虚拟机的指定快照。
        """
        domain = self.get_domain(domain_name, node_name)

        try:
            # 获取快照对象
            snapshot = domain.snapshotLookupByName(snapshot_name)

            # 删除快照
            snapshot.delete(0)  # 使用0标志表示删除快照及其关联的磁盘镜像

            print(f"Snapshot '{snapshot_name}' deleted successfully.")
            return {"message": f"Snapshot '{snapshot_name}' deleted successfully."}

        except libvirt.libvirtError as e:
            print(f"Failed to delete snapshot '{snapshot_name}': {e}")
            raise APIException(detail="Failed to delete snapshot.")

    def revert_to_snapshot(self, domain_name, node_name, snapshot_name):
        """
        将虚拟机还原到指定快照。
        """
        domain = self.get_domain(domain_name, node_name)

        try:
            # 获取快照对象
            snapshot = domain.snapshotLookupByName(snapshot_name)

            # 还原到快照
            domain.revertToSnapshot(snapshot)

            print(f"Domain '{domain_name}' reverted to snapshot '{snapshot_name}'.")
            return {"message": f"Domain '{domain_name}' reverted to snapshot '{snapshot_name}'."}

        except libvirt.libvirtError as e:
            print(f"Failed to revert to snapshot '{snapshot_name}': {e}")
            raise APIException(detail="Failed to revert to snapshot.")

    def migrate_vm(self, vm_name, node_name, destination_node_name):
        """
        将虚拟机从原节点迁移到目标节点。
        采用快照静态迁移。
        """
        snapshot_name = "snapshot_mig"
        # 获取虚拟机对象
        from_conn = self.get_node_connection(node_name)
        destination_conn = self.get_node_connection(destination_node_name)
        vm0 = from_conn.lookupByName(vm_name)
        if vm0 is None:
            raise Exception(f"Virtual machine {vm_name} not found on node2")

        # 在node4上创建快照
        snapshot0 = vm0.snapshotCreateXML(f"<domainsnapshot><name>{snapshot_name}</name></domainsnapshot>", 0)
        if snapshot0 is None:
            raise Exception("Failed to create snapshot on node2")

        # 获取快照文件路径
        snapshot_xml = snapshot0.getXMLDesc(0)
        snapshot_path_start = snapshot_xml.find("<disksnapshot file='") + len("<disksnapshot file='")
        snapshot_path_end = snapshot_xml.find("'/>", snapshot_path_start)
        snapshot_path = snapshot_xml[snapshot_path_start:snapshot_path_end]

        # 传输快照文件到node2（你可能需要使用scp或其他工具来进行传输）
        # 这里仅作为示例，具体实现取决于你的网络和安全配置
        transfer_command = f"scp mpiuser@{node_name}:{snapshot_path} mpiuser@{destination_node_name}:{snapshot_path}"
        # 执行传输命令，具体方法取决于你的Python环境和需求
        subprocess.run(transfer_command, shell=True)

        # 创建新的虚拟机镜像
        create_new_img_cmd = f"qemu-img create -f qcow2 /var/lib/libvirt/images/{vm_name}.qcow2 15G "
        #os.system(create_new_img_cmd)
        subprocess.run(["ssh", f"mpiuser@{destination_node_name}", create_new_img_cmd], check=True)

        # 在目标节点上创建虚拟机
        vm1 = destination_conn.createXML(vm0.XMLDesc(0), 0)
        if vm1 is None:
            raise Exception("Failed to create virtual machine on destination_node")

        # 加载快照
        vm1.snapshotCreateXML(f"<domainsnapshot><name>{snapshot_name}</name></domainsnapshot>", 0)

        print(f"Migration of {vm_name} completed successfully")


    def get_node_connection(self, node_name):
        """
        获取特定节点的 libvirt 连接对象。
        """
        if node_name == "node2":
            return self.conn2
        elif node_name == "node4":
            return self.conn4
        elif node_name == "node5":
            return self.conn5
        else:
            raise ValueError(f"无效的节点名称：{node_name}")

class LibvirtClient:
    libvirt_client = LibvirtWrapper()
