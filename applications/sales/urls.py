from django.urls import path

from . import views
from . import reports



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
    path('sales/print_invoice/<int:id>', reports.print_invoice, name='print_invoice'),
    
    # Report URLs
    path('sales/report/pdf/', reports.sales_report_to_pdf, name='sales_report_pdf'),
    path('sales/report/filter/', reports.sales_report_filter, name='sales_report_filter'),
    path('sales/print_invoice/<int:sale_id>/', reports.print_sale_invoice, name='print_sale_invoice'),
]