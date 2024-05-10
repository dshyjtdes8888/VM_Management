from rest_framework import views, status, generics
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from .utils import DistributeClient


class DistributeControlAPIView(views.APIView, DistributeClient):
    """
    子结点控制 API 视图类，用于执行子结点的不同操作。
    """

    def get(self, request, type):
        """
        处理 GET 请求，获取三个子结点的资源信息。

        参数：
        - request: Django 请求对象
        - type： 请求类型
        返回：
        - 如果操作成功，返回相应的子结点资源详细信息或成功消息。
        - 如果操作失败，返回相应的错误消息。
        """
        if type == 'memory':
            if self.distribute_client.ssh2 is not None:
                memory_info_node2 = self.distribute_client.get_memory_info(self.distribute_client.ssh2, 'node2')
            else:
                memory_info_node2 = None

            if self.distribute_client.ssh5 is not None:
                memory_info_node5 = self.distribute_client.get_memory_info(self.distribute_client.ssh5, 'node5')
            else:
                memory_info_node5 = None

            if self.distribute_client.ssh4 is not None:
                memory_info_node4 = self.distribute_client.get_memory_info(self.distribute_client.ssh4, 'node5')
            else:
                memory_info_node4 = None

            return Response({'memory_info_node2': memory_info_node2,
                             'memory_info_node5': memory_info_node5,
                             'memory_info_node4': memory_info_node4})
        elif type == 'cpu':
            if self.distribute_client.ssh2 is not None:
                cpu_info_node2 = self.distribute_client.get_cpu_info(self.distribute_client.ssh2, 'node2')
            else:
                cpu_info_node2 = None

            if self.distribute_client.ssh5 is not None:
                cpu_info_node5 = self.distribute_client.get_cpu_info(self.distribute_client.ssh5, 'node5')
            else:
                cpu_info_node5 = None

            if self.distribute_client.ssh4 is not None:
                cpu_info_node4 = self.distribute_client.get_cpu_info(self.distribute_client.ssh4, 'node4')
            else:
                cpu_info_node4 = None

            return Response({'cpu_info_node2': cpu_info_node2,
                             'cpu_info_node5': cpu_info_node5,
                             'cpu_info_node4': cpu_info_node4})

        elif type == 'disk':
            if self.distribute_client.ssh2 is not None:
                disk_info_node2 = self.distribute_client.get_disk_info(self.distribute_client.ssh2, 'node2')
            else:
                disk_info_node2 = None

            if self.distribute_client.ssh5 is not None:
                disk_info_node5 = self.distribute_client.get_disk_info(self.distribute_client.ssh5, 'node5')
            else:
                disk_info_node5 = None

            if self.distribute_client.ssh4 is not None:
                disk_info_node4 = self.distribute_client.get_disk_info(self.distribute_client.ssh4, 'node4')
            else:
                disk_info_node4 = None

            return Response({'disk_info_node2': disk_info_node2,
                             'disk_info_node5': disk_info_node5,
                             'disk_info_node4': disk_info_node4})

        elif type == 'heart_beat':
            self.distribute_client.start_heart_beat()
            last_heart_time = self.distribute_client.get_last_heartbeat_times()
            return Response({'last_heart_time': last_heart_time})

        elif type == 'stop_heartbeat':
            self.distribute_client.stop_heart_beat()
            return Response({'stop_heart_beat': True})

        elif type == 'reconnect':
            self.distribute_client.__init__()
            return Response({'reconnect': True})

        else:
            return Response({'message': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)


distribute_control_view = DistributeControlAPIView.as_view()
