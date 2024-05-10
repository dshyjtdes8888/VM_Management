from django.urls import path
from .views import distribute_control_view

urlpatterns = [
    # 子结点管理api
    path('ssh-connect/<str:type>/', distribute_control_view, name='ssh_connect'),
]
