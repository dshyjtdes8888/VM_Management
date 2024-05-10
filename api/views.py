from rest_framework import views, status, generics
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from libvirt import libvirtError

from .utils import LibvirtClient
from .serializers import VmReadSerializer, VmCreateSerializer


class VirtualMachineControlAPIView(views.APIView, LibvirtClient):
    """
    虚拟机控制 API 视图类，用于执行虚拟机的不同操作。
    """

    def get(self, request, vm_name, action, node_name, snapshot_name=None, destination_node_name=None):
        """
        处理 GET 请求，根据指定的操作执行虚拟机控制操作。

        参数：
        - request: Django 请求对象
        - vm_name: 虚拟机名称
        - action: 控制操作
        - node_name: 虚拟机所属子结点

        返回：
        - 如果操作成功，返回相应的虚拟机详细信息或成功消息。
        - 如果操作失败，返回相应的错误消息。
        """
        if action == 'sourse':
            result = self.libvirt_client.get_vm_sourse(vm_name, node_name)
            return Response(result, status=status.HTTP_200_OK)
        if action == 'reconnect':
            self.libvirt_client.__init__()
            return Response("reconnect successfully", status=status.HTTP_200_OK)

        return Response({'message': 'Invalid action for GET request'}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, vm_name, action, node_name, snapshot_name=None, destination_node_name=None):
        """
        处理 POST 请求，根据指定的操作执行虚拟机控制操作。

        参数：
        - request: Django 请求对象
        - vm_name: 虚拟机名称
        - action: 控制操作
        - node_name: 虚拟机所属子结点
        - snapshot_name: 虚拟机快照名称
        - destination_node_name: 虚拟机迁移目标结点

        返回：
        - 如果操作成功，返回相应的虚拟机详细信息或成功消息。
        - 如果操作失败，返回相应的错误消息。
        """

        try:
            if action == 'resume':
                self.libvirt_client.resume_vm(vm_name, node_name)

            elif action == 'stop':
                self.libvirt_client.stop_vm(vm_name, node_name)

            elif action == 'delete':
                self.libvirt_client.delete_vm(vm_name, node_name)

            elif action == 'start':
                self.libvirt_client.start_vm(vm_name, node_name)

            elif action == 'shutdown':
                self.libvirt_client.shutdown_vm(vm_name, node_name)

            elif action == 'destroy':
                self.libvirt_client.destroy_vm(vm_name, node_name)

            elif action == 'snapshot' and snapshot_name is not None:
                self.libvirt_client.snapshot_vm(vm_name, node_name, snapshot_name)

            elif action == 'migrate' and destination_node_name is not None:
                self.libvirt_client.migrate_vm(vm_name, node_name, destination_node_name)

            else:
                return Response({'message': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        except libvirtError as e:
            if hasattr(self, 'exception'):
                # 在超时期间引发的异常
                return Response({'message': str(self.exception)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # 其他异常
                return Response({'message': e.get_error_message()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not action == "delete":
            # 如果不是删除操作，则返回虚拟机详细信息
            domain = self.libvirt_client.get_domain(vm_name, node_name)
            serializer = VmReadSerializer(self.libvirt_client.get_vm_detail(domain.UUID(), node_name))
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "message": "OK"
            },
            status=status.HTTP_200_OK
        )


vm_control_api_view = VirtualMachineControlAPIView.as_view()


class VirtualMachineCreateListAPIView(generics.ListCreateAPIView, LibvirtClient):
    """
    虚拟机创建和列表 API 视图类，支持虚拟机的创建和列表展示。
    """

    def get_serializer_class(self):
        """
        根据请求方法返回相应的序列化器类。
        """
        if self.request.method == 'POST':
            return VmCreateSerializer
        return VmReadSerializer

    def get_queryset(self):
        """
        获取虚拟机列表。
        """
        return self.libvirt_client.get_vms()

    def create(self, request, *args, **kwargs):
        """
        处理 POST 请求，创建新的虚拟机。

        参数：
        - request: Django 请求对象

        返回：
        - 如果创建成功，返回新创建虚拟机的详细信息。
        - 如果创建失败，返回相应的错误消息。
        """
        # 创建虚拟机
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取创建的虚拟机详细信息
        created_domain = self.perform_create(serializer)
        serializer = VmReadSerializer(created_domain)
        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        执行虚拟机的创建。

        参数：
        - serializer: 使用 VmCreateSerializer 的序列化器

        返回：
        - 如果创建成功，返回新创建虚拟机的详细信息。
        - 如果创建失败，引发 APIException。
        """
        try:
            return serializer.save(libvirt_client=self.libvirt_client)
        except libvirtError as e:
            raise APIException(
                {'message': e.get_error_message()}
            )


vm_create_list_api_view = VirtualMachineCreateListAPIView.as_view()


class VirtualMachineSnapshotControlAPIView(views.APIView, LibvirtClient):
    """
    虚拟机快照列表 API 视图类，支持获取虚拟机的快照列表。
    """

    def get(self, request, vm_name, action, node_name, snapshot_name=None):
        """
        处理 GET 请求，获取虚拟机快照列表。

        参数：
        - request: Django 请求对象
        - vm_name: 快照所属虚拟机名称
        - node_name: 虚拟机所属子结点
        - snapshot_name: 快照名称

        返回：
        - 如果获取成功，返回快照信息。
        - 如果获取失败，返回相应的错误消息。
        """
        if action == 'list':
            print("Entering get method of VirtualMachineSnapshotListAPIView")
            snapshots = self.libvirt_client.list_snapshots(vm_name, node_name)
            return Response(snapshots, status=status.HTTP_200_OK)
        return Response({'message': 'Invalid action for GET request'}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, vm_name, action, node_name, snapshot_name):
        """
        处理 POST 请求，对虚拟机的快照进行操作。

        参数：
        - request: Django 请求对象
        - vm_name: 快照所属虚拟机名称
        - action： 快照操作
        - node_name: 虚拟机所属子结点
        - snapshot_name: 快照名称

        返回：
        - 如果执行成功，返回操作快照的响应信息。
        - 如果执行失败，返回相应的错误消息。
        """
        if action == 'delete':
            result = self.libvirt_client.delete_snapshot(vm_name, node_name, snapshot_name)
            return Response(result, status=status.HTTP_200_OK)

        if action == 'revert':
            result = self.libvirt_client.revert_to_snapshot(vm_name, node_name, snapshot_name)
            return Response(result, status=status.HTTP_200_OK)


vm_snapshot_control_api_view = VirtualMachineSnapshotControlAPIView.as_view()
