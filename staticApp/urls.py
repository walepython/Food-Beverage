from django.contrib.auth.decorators import login_required
from django.urls import path
from .views import CustomPasswordResetConfirmView
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index/',views.index,name= 'index'),
    path('product/',views.product_page,name= 'product'),
    path('product_detail/<int:id>',views.product_detail,name= 'product_detail'),
    path('about/',views.about,name= 'about'),
    path('contact/',views.contact,name= 'contact'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/remove/<int:item_id>', views.removeincart_view, name='removeInCart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart_quantity, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('password-reset-confirm/<uidb64>/<token>/',
         CustomPasswordResetConfirmView.as_view(
             template_name='password_reset_confirm.html'
         ),
         name='password_reset_confirm'),

    path("dashboard/<str:page>/", views.dashboard_partial, name="dashboard_partial"),
    path('edit-address/', views.edit_address, name='edit_address'),
    path('dashboard/', login_required(views.user_dashboard), name='dashboard'),
    path('user-account/', views.user_account, name='account'),
    path('orders/', views.orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('profile/<int:id>', views.profile_view, name='edit_profile'),
    path('profile-details/', views.profile_details, name='profile_details'),

#     path('profile/', views.profile, name='profile'),
#     path('faq/', views.faq, name='faq'),
#     path('shipping/', views.shipping, name='shipping'),
]