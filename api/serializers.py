from rest_framework import serializers

from pathlib import Path
import getpass

import os
import subprocess


def validate_iso_path(path):
    """
    验证提供的文件路径是否具有 '.iso' 后缀。
    如果不是，则引发 serializers.ValidationError。
    """
    if not Path(path).suffix == '.iso':
        raise serializers.ValidationError("Provided file is not an iso.")


# 表示虚拟机可能状态的枚举
VIR_DOMAIN_NOSTATE = 0
VIR_DOMAIN_RUNNING = 1
VIR_DOMAIN_BLOCKED = 2
VIR_DOMAIN_PAUSED = 3
VIR_DOMAIN_SHUTDOWN = 4
VIR_DOMAIN_SHUTOFF = 5
VIR_DOMAIN_CRASHED = 6
VIR_DOMAIN_PMSUSPENDED = 7

# StatusChoiceField 中使用的选择元组
CHOICES = (
    (VIR_DOMAIN_NOSTATE, '无状态'),
    (VIR_DOMAIN_RUNNING, '虚拟机正在运行'),
    (VIR_DOMAIN_BLOCKED, '虚拟机被资源阻塞'),
    (VIR_DOMAIN_PAUSED, '虚拟机被用户暂停'),
    (VIR_DOMAIN_SHUTDOWN, '虚拟机正在关机'),
    (VIR_DOMAIN_SHUTOFF, '虚拟机已关闭'),
    (VIR_DOMAIN_CRASHED, '虚拟机已崩溃'),
    (VIR_DOMAIN_PMSUSPENDED, '虚拟机被宿主电源管理挂起'),
)


class StatusChoiceField(serializers.ChoiceField):

    def to_representation(self, value):
        """
        将值的类名序列化。
        """
        return {
            "id": value,
            "state": CHOICES[value][1]
        }


class VmReadSerializer(serializers.Serializer):
    """
    用于读取虚拟机信息的序列化器。
    """
    node_name = serializers.CharField()
    uuid = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    ram = serializers.IntegerField(min_value=1)
    cpu = serializers.IntegerField(min_value=1)
    state = StatusChoiceField(choices=CHOICES)


class VmCreateSerializer(serializers.Serializer):
    """
    用于创建虚拟机的序列化器。
    """
    node_name = serializers.CharField()
    name = serializers.CharField(max_length=100)
    ram = serializers.IntegerField(min_value=1, max_value=4)
    cpu = serializers.IntegerField(min_value=1, max_value=4)
    storage = serializers.FloatField(min_value=10, max_value=20)
    iso_path = serializers.CharField(validators=[validate_iso_path])
    network_type = serializers.ChoiceField(choices=['nat', 'bridge'], default='nat')

    def save(self, **kwargs):
        """
        保存虚拟机配置并创建虚拟机镜像。
        """
        libvirt_client = kwargs.get("libvirt_client", None)
        name = self.validated_data["name"]
        ram = self.validated_data["ram"]
        storage = self.validated_data["storage"]
        cpu = self.validated_data["cpu"]
        iso_path = self.validated_data["iso_path"]
        network_type = self.validated_data["network_type"]
        node_name = self.validated_data["node_name"]

        # 创建新的虚拟机镜像
        create_new_img_cmd = f"qemu-img create -f qcow2 /var/lib/libvirt/images/{name}.qcow2 {storage}G "
        # os.system(create_new_img_cmd)
        if node_name == 'node2':
            subprocess.run(["ssh", "mpiuser@node2", create_new_img_cmd], check=True)
        if node_name == 'node4':
            subprocess.run(["ssh", "mpiuser@node4", create_new_img_cmd], check=True)
        if node_name == 'node5':
            subprocess.run(["ssh", "mpiuser@node5", create_new_img_cmd], check=True)

        # 构建虚拟机的 XML 配置
        xml_config1 = f'''
            <domain type="kvm">
                <name>{name}</name>
                <memory unit="GB">{ram}</memory>
                <vcpu placement="static">{cpu}</vcpu>
                
                <os>
                   <type arch="x86_64" machine="pc-q35-6.2">hvm</type>
                   <boot dev="hd" />
                   <boot dev="cdrom" />
                </os>
                
                
                <features>
                   <acpi/>
                   <apic/>
                   <pae/>
                </features>
                
                <clock offset="localtime" />
                <on_poweroff>destroy</on_poweroff>
                <on_reboot>restart</on_reboot>
                <on_crash>destroy</on_crash>
                
                <devices>
                     <disk type='file' device='disk' >
                            <driver name='qemu' type='qcow2'/>
                            <source file='{f"/var/lib/libvirt/images/{name}.qcow2"}'/>
                            <target dev='vda' bus='virtio'/>
                            <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
                    </disk>
                    <disk type='file' device='cdrom'>
                            <driver name='qemu' type='raw'/>
                            <source file='{iso_path}'/>
                            <target dev='sda' bus='sata'/>
                            <readonly/>
                            <address type='drive' controller='0' bus='0' target='0' unit='0'/>
                    </disk>
                    
                    <interface type='network'>
                            <mac address='52:54:00:4e:6f:78'/>
                            <source network='default'/>
                            <model type='virtio'/>
                    </interface>
                    
                    <graphics type="spice" autoport="yes">
                        <listen type="address"/>
                        <image compression="off"/>
                    </graphics>
                    
                
                    <!-- Qemu guest agent -->

                    <channel type="unix">
                        <target type="virtio" name="org.qemu.guest_agent.0"/>
                        <address type="virtio-serial" controller="0" bus="0" port="1"/>
                    </channel>
                
                </devices>
                
                <!-- Other XML elements and structure -->
            </domain>
        '''

        # 构建虚拟机的 XML 配置
        xml_config2 = f'''
            <domain type="kvm">
                <name>{name}</name>
                <memory unit="GB">{ram}</memory>
                <vcpu placement="static">{cpu}</vcpu>

                <os>
                   <type arch="x86_64" machine="pc-q35-6.2">hvm</type>
                   <boot dev="hd" />
                   <boot dev="cdrom" />
                </os>


                <features>
                   <acpi/>
                   <apic/>
                   <pae/>
                </features>

                <clock offset="localtime" />
                <on_poweroff>destroy</on_poweroff>
                <on_reboot>restart</on_reboot>
                <on_crash>destroy</on_crash>

                <devices>
                     <disk type='file' device='disk' >
                            <driver name='qemu' type='qcow2'/>
                            <source file='{f"/var/lib/libvirt/images/{name}.qcow2"}'/>
                            <target dev='vda' bus='virtio'/>
                            <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
                    </disk>
                    <disk type='file' device='cdrom'>
                            <driver name='qemu' type='raw'/>
                            <source file='{iso_path}'/>
                            <target dev='sda' bus='sata'/>
                            <readonly/>
                            <address type='drive' controller='0' bus='0' target='0' unit='0'/>
                    </disk>

                    <interface type='bridge'>
                            <source bridge='virbr0'/>
                            <model type='virtio'/>
                    </interface>

                    <graphics type="spice" autoport="yes">
                        <listen type="address"/>
                        <image compression="off"/>
                    </graphics>


                    <!-- Qemu guest agent -->

                    <channel type="unix">
                        <target type="virtio" name="org.qemu.guest_agent.0"/>
                        <address type="virtio-serial" controller="0" bus="0" port="1"/>
                    </channel>

                </devices>

                <!-- Other XML elements and structure -->
            </domain>
        '''

        # 如果存在 libvirt_client，则通过它创建虚拟机
        if libvirt_client and network_type == 'nat':
            return libvirt_client.create_vm(xml_config1, node_name)
        if libvirt_client and network_type == 'bridge':
            return libvirt_client.create_vm(xml_config2, node_name)
