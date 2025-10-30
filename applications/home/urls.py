from django.urls import path

from .views import *

app_name = 'home'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', NewLoginView.as_view(), name='login'),
    path('logout/', NewLogoutView.as_view(), name='logout'),
    path('users', UserListView.as_view(), name='user_list'),
    path('create/', UserCreateView.as_view(), name='create_user'),
    path('update/<int:pk>/', UserUpdateView.as_view(), name='update_user'),
    path('user/<int:pk>/change-password/', UserChangePasswordView.as_view(), name='user_change_password'),
    path('delete/<int:pk>/', UserDeleteView.as_view(), name='user_delete'),
    path('toggle-status/', ToggleUserStatusView.as_view(), name='toggle_user_status'),
    path('dasboards/', dashboard_view, name='dashboard'),

]