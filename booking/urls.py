from django.urls import path

from booking import views

app_name = 'booking'

urlpatterns = [
    path('', views.SearchView.as_view(), name='search'),
    path('kursi/<int:schedule_id>/', views.SeatSelectionView.as_view(), name='seats'),
    path('pesan/<int:schedule_id>/', views.CreateBookingView.as_view(), name='create'),
    path('booking/<str:code>/', views.BookingDetailView.as_view(), name='detail'),
    path('booking/<str:code>/upload/', views.UploadProofView.as_view(), name='upload_proof'),
    path('cek-booking/', views.CheckBookingView.as_view(), name='check'),
    path('rute/', views.RouteHubView.as_view(), name='route_hub'),
    path('rute/<slug:slug>/', views.RouteDetailView.as_view(), name='route_detail'),
]
