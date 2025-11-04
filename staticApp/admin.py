from django.contrib import admin

from .models import Product, Users, Contact, DeliveryAddress, Cart, CartItem, Profile

item = (Product,Users,Contact,DeliveryAddress,Cart,CartItem,Profile,
)

# Register your models here.
for i in item:
    admin.site.register(i)

