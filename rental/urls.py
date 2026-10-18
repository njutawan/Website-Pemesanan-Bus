from django.urls import path

from rental import views

app_name = 'rental'

urlpatterns = [
    path('', views.VehicleListView.as_view(), name='index'),
    path('mobil/<slug:slug>/', views.VehicleDetailView.as_view(), name='detail'),
    path('mobil/<slug:slug>/sewa/', views.CreateRentalView.as_view(), name='book'),
    path('sewa/<str:code>/', views.RentalDetailView.as_view(), name='detail_booking'),
    path('sewa/<str:code>/upload/', views.UploadRentalProofView.as_view(), name='upload_proof'),
]
