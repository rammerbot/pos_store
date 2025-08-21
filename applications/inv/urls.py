from django.contrib import admin
from django.urls import path

from . import views

app_name = 'inv'
urlpatterns = [
    path('category/', views.CategoryListView.as_view(), name='category_list'),
    path('create_category/', views.CreateCategoryView.as_view(), name='create_category'),
    path('update_category/<pk>/', views.UpdateCategoryView.as_view(), name='update_category'),
    path('toggle-category-status/', views.ToggleCategoryStatusView.as_view(), name='toggle_category_status'),
    # SubCategory URLs
    path('sub_category/', views.SubCategoryListView.as_view(), name='sub_category_list'),
    path('create_sub_category/', views.CreateSubCategoryView.as_view(), name='create_sub_category'),
    path('update_sub_category/<pk>/', views.UpdateSubCategoryView.as_view(), name='update_sub_category'),
    path('toggle-sub-category-status/', views.ToggleSubCategoryStatusView.as_view(), name='toggle_sub_category_status'),
    # Brand URLs
    path('brand/', views.BrandListView.as_view(), name='brand_list'),
    path('create_brand/', views.CreateBrandView.as_view(), name='create_brand'),
    path('update_brand/<pk>/', views.UpdateBrandView.as_view(), name='update_brand'),
    path('toggle-brand-status/', views.ToggleBrandStatusView.as_view(), name='toggle_brand_status'),
    # Unit Measure URLs
    path('unit_measure/', views.UnitMeasureListView.as_view(), name='unit_measure_list'),
    path('create_unit_measure/', views.CreateUnitMeasureView.as_view(), name='create_unit_measure'),
    path('update_unit_measure/<pk>/', views.UpdateUnitMeasureView.as_view(), name='update_unit_measure'),
    path('toggle-unit_measure-status/', views.ToggleUnitMeasureStatusView.as_view(), name='toggle_unit_measure_status'),
    # product URLs
    path('product/', views.ProductListView.as_view(), name='products_list'),
    path('create_product/', views.CreateProductView.as_view(), name='create_product'),
    path('update_product/<pk>/', views.UpdateProductView.as_view(), name='update_product'),
    path('toggle-product-status/', views.ToggleProductStatusView.as_view(), name='toggle_product_status'),
]