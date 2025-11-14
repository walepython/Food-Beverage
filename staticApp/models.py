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

        price_choice = models.CharField(max_length=30, choices= PRICE_CHOICES, default='Per_paint')
        quantity = models.IntegerField(null=True,blank=True)
        old_per_bag = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
        discount_percent = models.PositiveIntegerField(blank=True, null=True, editable=False)

        stock_quantity = models.PositiveIntegerField(default=0,blank=True, null=True)
        average_rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
        review_count = models.IntegerField(default=0,blank=True, null=True)

        size = models.CharField(max_length=2, choices=SIZE, default='M')
        old_per_paint = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
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

            if self.pk:
                old_instance = Product.objects.get(pk=self.pk)

                # If price choice is Per_bag
                if self.price_choice == "Per_bag":
                    if old_instance.price_per_bag != self.price_per_bag:
                        self.old_per_bag = old_instance.price_per_bag

                # If price choice is Per_paint
                else:
                    if old_instance.price_per_paint != self.price_per_paint:
                        self.old_per_paint = old_instance.price_per_paint


            # Calculate discount based on price_choice
            if self.price_choice == 'Per_bag':
                current_price = self.price_per_bag
                old_price = self.old_per_bag
            else:  # Per_paint
                current_price = self.price_per_paint
                old_price = self.old_per_paint

            # Calculate discount percentage if both prices exist and current is lower
            if (old_price and current_price and
                current_price < old_price and
                old_price > 0):  # Prevent division by zero

                self.discount_percent = round(((old_price - current_price) / old_price) * 100)

                if self.discount_percent > 100:
                    self.discount_percent = 100
            else:
                self.discount_percent = 0

            super().save(*args, **kwargs)

        @property
        def current_price(self):
            """Get the current price based on price_choice"""
            if self.price_choice == 'Per_bag':
                return self.price_per_bag
            else:  # Per_paint
                return self.price_per_paint

        @property
        def old_price(self):
            """Get the old price based on price_choice for discount display"""
            if self.price_choice == 'Per_bag':
                return self.old_per_bag
            else:  # Per_paint
                return self.old_per_paint

        @property
        def has_discount(self):
            """Check if product has discount"""
            return self.discount_percent > 0

        @property
        def discount_amount(self):
            """Calculate the actual discount amount"""
            if self.has_discount:
                return (self.old_price or 0) - (self.current_price or 0)
            return 0

        def __str__(self):
            return self.name

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
        """Calculate current subtotal"""
        if self.custom_price:
            return self.custom_price * self.quantity

        # Use price based on the package selected for this cart item
        if self.package == 'Per_bag' and self.product.price_per_bag:
            return self.product.price_per_bag * self.quantity
        elif self.package == 'Per_paint' and self.product.price_per_paint:
            return self.product.price_per_paint * self.quantity
        else:
            return (getattr(self.product, 'current_price', 0) or 0) * self.quantity

    @property
    def old_total_price(self):
        """Calculate old price total for discount comparison"""
        if self.package == 'Per_bag' and self.product.old_per_bag:
            old_price = self.product.old_per_bag
        elif self.package == 'Per_paint' and self.product.old_per_paint:
            old_price = self.product.old_per_paint
        else:
            old_price = getattr(self.product, 'old_price', 0) or 0

        return old_price * self.quantity

    @property
    def display_unit_price(self):
        """Get the unit price for display"""
        if self.custom_price:
            return self.custom_price
        elif self.package == 'Per_bag' and self.product.price_per_bag:
            return self.product.price_per_bag
        elif self.package == 'Per_paint' and self.product.price_per_paint:
            return self.product.price_per_paint
        else:
            return getattr(self.product, 'current_price', 0) or 0

    @property
    def discount_amount(self):
        """Calculate actual discount amount for this item"""
        return max(0, self.old_total_price - self.subtotal())

    @property
    def has_discount(self):
        """Check if this specific cart item has a discount"""
        old_price = self.display_old_unit_price
        current_price = self.display_unit_price
        return old_price and current_price and current_price < old_price

    @property
    def display_old_unit_price(self):
        """Get the old unit price for display based on package"""
        if self.package == 'Per_bag' and self.product.old_per_bag:
            return self.product.old_per_bag
        elif self.package == 'Per_paint' and self.product.old_per_paint:
            return self.product.old_per_paint
        else:
            return None

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
