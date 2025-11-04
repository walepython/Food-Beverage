from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser


USER_TYPE = (
    ("Vendor","Vendor"),
    ("Customer", "Customer"),
)
# Create your models here.
class Users(AbstractUser):
    username = models.CharField(max_length=255,unique=True,null=True,blank=True)
    email = models.EmailField(unique=True,blank=True)
    user_type = models.CharField(max_length=255, choices=USER_TYPE, null=True, blank=True, default=None)

    def __str__(self):
        return self.username

    # --- this we automatically store a new user when ever we create it
    # --- or instance and update the recode
    def save(self, *args, **kwargs):
        if not self.username:
            # Ensure the generated username is unique
            base_username = self.email.split('@')[0]
            username = base_username
            counter = 1
            while Users.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            self.username = username
        super().save(*args, **kwargs)


class Profile(models.Model):
    GENDER = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, null=True,blank=True)
    DOB = models.DateField(blank=True, null=True, verbose_name="Date of Birth")
    gender = models.CharField(max_length=10, choices=GENDER, default='Male')
    image = models.ImageField(upload_to='picture', null=True, blank=True)


    def __str__(self):
        return f"Profile for {self.user.username}"

    # --- this we automatically store a new user when ever we create it
    # --- or instance and update the recode
    def save(self, *args, **kwargs):
        email_username = self.user.email.split("@")
        if not self.user.first_name:
            self.user.first_name = email_username[0]
        super(Profile, self).save(*args, **kwargs)


class Product(models.Model):
        COLOR = [
            ('Black', 'Black'),
            ('Gray', 'Gray'),
            ('Blue', 'Blue'),
            ('Pink', 'Pink'),
        ]

        SIZE = [
            ('S', 'Small'),
            ('M', 'Medium'),
            ('L', 'Large'),
        ]
        PRICE_CHOICES = [
            ('Per_paint', 'Per_paint'),
            ('Per_bag', 'Per_bag'),
        ]

        name = models.CharField(max_length=255)
        slug = models.SlugField(unique=True, blank=True)
        description = models.TextField(blank=True, null=True)

        price_per_paint = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
        price_per_bag = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

        price_choice = models.CharField(max_length=30, choices= PRICE_CHOICES, default='Per_bag')
        quantity = models.IntegerField(null=True,blank=True)
        old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
        discount_percent = models.PositiveIntegerField(blank=True, null=True, editable=False)

        stock_quantity = models.PositiveIntegerField(default=0,blank=True, null=True)
        average_rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
        review_count = models.IntegerField(default=0,blank=True, null=True)

        size = models.CharField(max_length=2, choices=SIZE, default='M')
        price = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
        # color = models.CharField(max_length=30, choices=COLOR, default='Black')
        category = models.CharField(max_length=200, default="")

        sub_category = models.CharField(max_length=200, default="")
        is_available = models.BooleanField(default=True)
        image = models.ImageField(upload_to='products/', null=True, blank=True)

        vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="products")

        created_at = models.DateTimeField(auto_now_add=True)

        def save(self, *args, **kwargs):
            if not self.slug:
                self.slug = slugify(self.name)
            if self.old_price and self.price < self.old_price:
                self.discount_percent = round(((self.old_price - self.price) / self.old_price) * 100)
            else:
                self.discount_percent = 0
            super().save(*args, **kwargs)

        def __str__(self):
            return self.name



class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.product.name} - {self.rating}⭐"

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())

    def __str__(self):
        return f"Cart ({self.user})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    package = models.CharField(max_length=50, blank=True, null=True)
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def subtotal(self):
        return (self.custom_price or self.product.price) * self.quantity

    @property
    def old_total_price(self):
        old_price = self.product.old_price or self.product.price
        return old_price * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

class Contact(models.Model):
    name = models.CharField(max_length=20,null=True)
    email = models.EmailField()
    subject = models.CharField(max_length=20,null=True)
    message = models.TextField(max_length=220,null=True)



class DeliveryAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')

    # --- Address Fields ---
    address_line_1 = models.CharField(max_length=255, help_text="Street address, P.O. box, company name")
    address_line_2 = models.CharField(max_length=255, blank=True, null=True,
                                      help_text="Apartment, suite, unit, building, floor, etc.")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, verbose_name="State / Province / Region")
    postal_zip_code = models.CharField(max_length=20, verbose_name="Postal / Zip Code")
    country = models.CharField(max_length=100)

    # --- Contact Info for this Address ---
    contact_name = models.CharField(max_length=100, help_text="Full name of the recipient")
    contact_phone = models.CharField(max_length=20, blank=True, null=True)

    # --- Metadata ---
    is_default = models.BooleanField(default=False, help_text="Is this the user's default shipping address?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Delivery Address"
        verbose_name_plural = "Delivery Addresses"
        ordering = ['-is_default', '-updated_at']  # Show default address first, then the most recently used

    def __str__(self):

        return f"{self.contact_name}, {self.address_line_1}, {self.city}, {self.country}"

    def save(self, *args, **kwargs):

        if self.is_default:
            # Select all other addresses for this user and set their is_default to False.
            DeliveryAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super(DeliveryAddress, self).save(*args, **kwargs)

class Order(models.Model):
    STATUS_CHOICES = [
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('shipped', 'Shipped'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
        ]

    user = models.ForeignKey(Users, on_delete=models.CASCADE, blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    date_ordered = models.DateTimeField(auto_now_add=True,blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', blank=True, null=True)
    reference_code = models.CharField(max_length=20, unique=True, editable=False,blank=True, null=True)

    def save(self, *args, **kwargs):
        import uuid
        if not self.reference_code:
            self.reference_code = str(uuid.uuid4()).split('-')[0].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items",blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE,blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    package = models.CharField(max_length=50, blank=True, null=True)

    def get_subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"
