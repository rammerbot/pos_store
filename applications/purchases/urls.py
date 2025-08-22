from django.urls import path

from . import views

app_name = "purchases"
urlpatterns = [
    # Supplier URLs
    path('suppliers', views.SupplierListView.as_view(), name='suppliers_list'),
    path('create/', views.CreateSupplierView.as_view(), name='create_supplier'),
    path('toggle_status/', views.ToggleSupplierStatusView.as_view(), name='toggle_supplier_status'),
    path('update/<int:pk>/', views.UpdateSupplierView.as_view(), name='update_supplier'),
    
]