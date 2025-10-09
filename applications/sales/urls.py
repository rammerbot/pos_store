from django.urls import path

from . import views



app_name = "sales"
urlpatterns = [
    # customer URLs
    path('customers/', views.CustomerListView.as_view(), name='customers_list'),
    path('create/', views.CreateCustomerView.as_view(), name='create_customer'),
    path('toggle_status/', views.ToggleCustomerStatusView.as_view(), name='toggle_customer_status'),
    path('update/<int:pk>/', views.UpdateCustomerView.as_view(), name='update_customer'),

    # sale URLs
    path('sales/', views.SalesListView.as_view(), name='sales_list'),
    path('sales/create/', views.sale_order_view, name='sale_create'),
    path('sales/update/<int:sale_id>/', views.sale_order_view, name='sale_update'),
    path('sales/delete/<int:sale_id>/<int:pk>/', views.SaleDeleteView.as_view(), name='sale_delete'),
]