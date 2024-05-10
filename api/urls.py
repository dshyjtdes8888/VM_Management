from django.contrib import admin
from django.urls import include, path
from .views import vm_control_api_view, vm_create_list_api_view, vm_snapshot_control_api_view

urlpatterns = [
        # 虚拟机创建和列表api
        path('vms/', vm_create_list_api_view, name='vm-list-create'),

        # 虚拟机操作api
        path('vms/<str:vm_name>/<str:action>/<str:node_name>/', vm_control_api_view, name='vm-control'),
        path('vms/<str:vm_name>/<str:action>/<str:node_name>/<str:snapshot_name>/', vm_control_api_view, name='vm-create-snapshot'),
        path('vms/<str:vm_name>/<str:action>/<str:node_name>/<str:snapshot_name>/<str:destination_node_name>/',  vm_control_api_view, name='vm-migrate'),

        # 虚拟机快照操作api
        path('vms/snapshot/todo/<str:vm_name>/<str:action>/<str:node_name>/<str:snapshot_name>/', vm_snapshot_control_api_view, name='vm-snapshot-control'),
        path('vms/snapshot/todo/<str:vm_name>/<str:action>/<str:node_name>/', vm_snapshot_control_api_view, name='vm-snapshot-list-no-snapshot'),
]
