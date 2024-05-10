from rest_framework import serializers


class MemorySerializer(serializers.Serializer):
    """
    用于读取节点内存信息的序列化器。
    """
    node_name = serializers.CharField(max_length=100)
    total_memory = serializers.CharField(max_length=100)
    used_memory = serializers.CharField(max_length=100)
    free_memory = serializers.CharField(max_length=100)
    percent_used = serializers.CharField(max_length=100)

class CPUSerializer(serializers.Serializer):
    """
    用于读取节点CPU信息的序列化器。
    """

    node_name = serializers.CharField(max_length=100)
    cpu_total = serializers.CharField(max_length=100)
    cpu_user = serializers.CharField(max_length=100)
    cpu_system = serializers.CharField(max_length=100)
    cpu_nice = serializers.CharField(max_length=100)
    cpu_idle = serializers.CharField(max_length=100)
    cpu_iowait = serializers.CharField(max_length=100)
    cpu_hardirq = serializers.CharField(max_length=100)
    cpu_softirq = serializers.CharField(max_length=100)
    cpu_steal = serializers.CharField(max_length=100)


class DiskSerializer(serializers.Serializer):
    """
    用于读取节点磁盘信息的序列化器。
    """
    node_name = serializers.CharField(max_length=100)
    filesystem = serializers.CharField(max_length=100)
    size = serializers.CharField(max_length=100)
    used = serializers.CharField(max_length=100)
    free = serializers.CharField(max_length=100)
    percent = serializers.CharField(max_length=100)
    mounted_on = serializers.CharField(max_length=100)


