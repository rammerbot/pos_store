from django.urls import path

from . import views
from . import reports


app_name = "purchases"
urlpatterns = [
    # Supplier URLs
    path('suppliers/', views.SupplierListView.as_view(), name='suppliers_list'),
    path('create/', views.CreateSupplierView.as_view(), name='create_supplier'),
    path('toggle_status/', views.ToggleSupplierStatusView.as_view(), name='toggle_supplier_status'),
    path('update/<int:pk>/', views.UpdateSupplierView.as_view(), name='update_supplier'),

    # Purchases URLs
    path('purchases/', views.PurchasesListView.as_view(), name='purchase_list'),
    path('purchase/', views.purchase_order_view, name='purchase_create'),
    path('purchase/update/<int:purchase_id>',views.purchase_order_view, name="purchase_update"),
    path('delete/<int:purchase_id>/<int:pk>/', views.PurchaseDeleteView.as_view(), name='purchase_delete'),
    path('purchases/report/pdf/',reports.purshase_repotr_to_pdf, name='purchase_report_pdf'),
    path('purchases/report/filter/', reports.purchase_report_filter, name='purchase_report_filter'),
    path('purchases/report/print/<int:purchase_id>', reports.print_purchase_report, name='pirnt_purchase_report'),
]