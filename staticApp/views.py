from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F, Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import views as auth_views
from django.template import TemplateDoesNotExist
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime
import uuid



from .models import Product, Review, CartItem, Cart, DeliveryAddress, Order, Users, Profile, OrderItem


# Create your views here.


def index(request):
    latest_products = Product.objects.filter(is_available=True).order_by('-created_at')[:6]

    all_categories = Product.objects.values_list('category', flat=True).distinct().exclude(category__exact='')

    context = {
        'product': latest_products,  # Your template uses the name 'product'
        'cats': all_categories,
    }

    return render(request, 'index.html', context)

def about(request):
    return render(request,'about.html')


def product_page(request):
    products = Product.objects.filter(is_available=True).order_by('-created_at')
    category_filter = request.GET.get('category')

    search_query = request.GET.get('q')

    if category_filter:

        products = products.filter(category__iexact=category_filter)

    if search_query:
        # If a search query is provided, filter by name or description
        products = products.filter(name__icontains=search_query)

    # Get all unique categories for the filter menu
    all_categories = Product.objects.values_list('category', flat=True).distinct().exclude(category__exact='')

    context = {
        'product': products,  # Pass the (potentially filtered) list of products
        'cats': all_categories,
        'selected_category': category_filter,  # Pass this back to highlight the active filter
    }

    return render(request, 'products.html', context)

def product_detail(request, id):
    product = get_object_or_404(Product, id=id, is_available=True)


    Product.objects.filter(id=id).update(review_count=F('review_count') + 1)

    product.refresh_from_db()

    price_options = []
    if product.category.lower() in ['rice', 'beans']:
        price_options = Product.PRICE_CHOICES
    elif product.category.lower() in ['yam', 'potato']:
        price_options = [
            ('Per_pack', 'Per_pack'),
            ('Per_tuba', 'Per_tuba'),

        ]
    else:
        # Default to model's defined choices
        price_options = Product.PRICE_CHOICES

    return render(request, 'productDetails.html', {
        'product': product,
        'price_options': price_options
    })


def contact(request):
    return render(request,'contact.html')


@login_required
def cart_view(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
    except Cart.DoesNotExist:
        cart = None
        cart_items = []

    # Use model methods for totals
    cart_total = cart.total_price() if cart else 0
    cart_total_before_discount = sum(item.old_total_price for item in cart_items)
    cart_discount_total = cart_total_before_discount - cart_total

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_total_before_discount': cart_total_before_discount,
        'cart_discount_total': cart_discount_total,
    }
    return render(request, 'cart.html', context)


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    package = request.POST.get("price_choice")
    selected_price = request.POST.get("selected_price")
    quantity = int(request.POST.get("quantity", 1))

    # Determine the actual price to use
    if selected_price:
        try:
            custom_price = Decimal(selected_price)
        except:
            custom_price = product.price
    else:
        # Fallback to product price based on package
        if package == 'Per_paint' and product.price_per_paint:
            custom_price = product.price_per_paint
        elif package == 'Per_bag' and product.price_per_bag:
            custom_price = product.price_per_bag
        else:
            custom_price = product.price

    # Check if same product with same package already exists
    cart_item = CartItem.objects.filter(
        cart=cart,
        product=product,
        package=package
    ).first()

    if cart_item:
        # Update existing item
        cart_item.quantity += quantity
        cart_item.custom_price = custom_price
        cart_item.save()
        message = f"Updated '{product.name}' ({package}) quantity in your cart."
    else:
        # Create new item
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            package=package,
            custom_price=custom_price,
            quantity=quantity
        )
        message = f"'{product.name}' ({package}) has been added to your cart."

    messages.success(request, message)
    return redirect('cart')  # Redirect to cart page instead


@require_POST
@login_required
def removeincart_view(request,item_id):
    try:
        item = CartItem.objects.get(pk=item_id, cart__user=request.user)
        item_name = item.product.name
        item.delete()
        messages.success(request, f"'{item_name}' removed from cart.")
    except CartItem.DoesNotExist:
        messages.error(request, "Item not found in your cart.")

    return redirect('cart')

@csrf_exempt
@login_required
def update_cart_quantity(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        action = request.POST.get("action")  # "increase" or "decrease"

        try:
            cart_item = CartItem.objects.get(cart__user=request.user, product_id=product_id)
        except CartItem.DoesNotExist:
            return JsonResponse({"error": "Item not found"}, status=404)

        if action == "increase":
            cart_item.quantity += 1
        elif action == "decrease" and cart_item.quantity > 1:
            cart_item.quantity -= 1

        cart_item.save()

        cart = cart_item.cart
        cart_items = cart.items.all()

        cart_total = cart.total_price()
        cart_total_before_discount = sum(item.old_total_price for item in cart_items)
        cart_discount_total = cart_total_before_discount - cart_total

        return JsonResponse({
            "quantity": cart_item.quantity,
            "item_total": f"₦{cart_item.subtotal():,.2f}",
            "cart_total": f"₦{cart_total:,.2f}",
            "cart_total_before_discount": f"₦{cart_total_before_discount:,.2f}",
            "cart_discount_total": f"₦{cart_discount_total:,.2f}",
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


def checkout(request):
    if request.method == "POST":
        try:
            # Get form data
            name = request.POST.get("contact_name", "").strip()
            phone_no = request.POST.get("contact_phone", "").strip()
            address1 = request.POST.get("address_line_1", "").strip()
            address2 = request.POST.get("address_line_2", "").strip() or None
            city = request.POST.get("city", "").strip()
            state = request.POST.get("state", "").strip()
            postal = request.POST.get("postal_zip_code", "").strip()
            country = request.POST.get("country", "").strip()
            is_default = request.POST.get("is_default") == 'on'

            # Validation
            if not all([name, phone_no, address1, city, state, postal, country]):
                messages.error(request, "Please fill in all required fields")
                return render(request, 'checkout.html')

            # --- 🛒 Get user's cart and items ---
            cart = Cart.objects.filter(user=request.user).first()
            if not cart or not cart.items.exists():
                messages.error(request, "Your cart is empty")
                return render(request, 'checkout.html')



            cart_items = cart.items.all()
            total_price = cart.total_price()

            # Save delivery address
            deliver = DeliveryAddress.objects.create(
                user=request.user,
                contact_name=name,
                contact_phone=phone_no,
                address_line_1=address1,
                address_line_2=address2,
                city=city,
                state=state,
                postal_zip_code=postal,
                country=country,
                is_default=is_default
            )

            # ✅ Generate and store order reference once
            order_ref = f"FB-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                reference_code=order_ref  # Save to model
            )

            # ✅ Create OrderItems
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.custom_price or item.product.price,
                    package=item.package
                )

            # --- USER EMAIL (Order Confirmation) ---
            try:
                user_subject = f"🛍️ Order Confirmation #{order_ref} - Thank you for your purchase!"
                cart_items_data = []
                for item in cart.items.all():
                    cart_items_data.append({
                        'name': item.product.name,
                        'package': item.package or 'N/A',
                        'quantity': item.quantity,
                        'price': item.custom_price or item.product.price,
                        'subtotal': item.subtotal(),
                    })

                user_context = {
                    'name': name,
                    'address1': address1,
                    'address2': address2,
                    'city': city,
                    'state': state,
                    'postal': postal,
                    'country': country,
                    'year': datetime.now().year,
                    'cart_items': cart_items_data,
                    'total_price': total_price,
                    'order_ref': order_ref,
                }

                user_html = render_to_string('order_confirmation_user.html', user_context)
                user_text = strip_tags(user_html)

                user_email = EmailMultiAlternatives(
                    user_subject,
                    user_text,
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email]
                )
                user_email.attach_alternative(user_html, "text/html")
                user_email.send(fail_silently=False)
            except Exception as e:
                print(f"User email error: {e}")
                messages.warning(request, "Order placed successfully, but confirmation email failed to send.")

            # --- ADMIN EMAIL (Order Notification) ---
            try:
                admin_subject = f"📦 New Order #{order_ref} from {name}"
                cart_items_data = []
                for item in cart.items.all():
                    cart_items_data.append({
                        'name': item.product.name,
                        'package': item.package or 'N/A',
                        'quantity': item.quantity,
                        'price': item.custom_price or item.product.price,
                        'subtotal': item.subtotal(),
                    })

                admin_context = {
                    'name': name,
                    'phone_no': phone_no,
                    'address1': address1,
                    'address2': address2,
                    'city': city,
                    'state': state,
                    'postal': postal,
                    'country': country,
                    'email': request.user.email,
                    'year': datetime.now().year,
                    'cart_items': cart_items_data,
                    'total_price': total_price,
                    'order_ref': order_ref,
                }

                # Check if template exists first
                try:
                    admin_html = render_to_string('order_notify_admin.html', admin_context)
                except TemplateDoesNotExist:
                    # Fallback template
                    admin_html = f"""
                    <h2>New Order Received</h2>
                    <p><strong>Customer:</strong> {name}</p>
                    <p><strong>Email:</strong> {request.user.email}</p>
                    <p><strong>Phone:</strong> {phone_no}</p>
                    <p><strong>Address:</strong> {address1}, {city}, {state} {postal}, {country}</p>
                    <p><strong>Total:</strong> ${total_price}</p>
                    <h3>Order Items:</h3>
                    """
                    for item in cart_items:
                        admin_html += f"<p>{item.quantity} x {item.product.name} - ${item.subtotal()}</p>"
                    admin_html += f"<h3>Total: ${total_price}</h3>"

                admin_text = strip_tags(admin_html)

                admin_email = EmailMultiAlternatives(
                    admin_subject,
                    admin_text,
                    settings.DEFAULT_FROM_EMAIL,
                    ["walepython@gmail.com"]  # This is the admin email recipient
                )
                admin_email.attach_alternative(admin_html, "text/html")
                admin_email.send(fail_silently=True)  # Change to True to prevent checkout failure

            except Exception as e:
                print(f"Admin email error: {e}")

            # Clear the cart after successful checkout
            cart.items.all().delete()
            cart.delete()

            messages.success(request, "✅ Checkout successful! Confirmation email sent.")
            return redirect('cart')

        except Exception as e:
            print(f"Checkout error: {str(e)}")
            messages.error(request, f"Error during checkout: {str(e)}")
            return render(request, 'checkout.html')

    return render(request, 'cart.html')

#@login_required
def user_dashboard(request):
    user = request.user
    address = DeliveryAddress.objects.filter(user=user, is_default=True).first()
    orders = Order.objects.filter(user=user).order_by('-date_ordered')
    return render(request, 'dashboard.html', {
        'user': user,
        'address': address,
        'orders': orders,
    })

@login_required
def user_account(request):
    user = request.user
    address = DeliveryAddress.objects.filter(user=user, is_default=True).first()
    orders = Order.objects.filter(user=user).order_by('-date_ordered')
    return render(request, 'partials/my_account.html', {
        'user': user,
        'address': address,
        'orders': orders,
    })

@login_required
def dashboard_partial(request, page):
    print(f"Dashboard partial called with page: {page}")
    context = {}
    if page == 'orders':
        context['orders'] = Order.objects.filter(user=request.user).order_by('-date_ordered')
    elif page == 'account':
        context['user'] = request.user
        context['address'] = DeliveryAddress.objects.filter(user=request.user, is_default=True).first()
    # Add elif blocks for other pages like 'reviews', 'wishlist' as you build them
    elif page == 'inbox':
        # Add inbox context if needed
        pass
    elif page == 'reviews':
        # Add reviews context if needed
        pass
    elif page == 'profile_details':
        print(" this is my Profile ")
        profile = request.user.profile
        context = {
            'profile': profile,
            'user': request.user
        }

    # --- TEMPLATE MAPPING ---
    template_map = {
        "orders": "partials/ordersection.html",
        "inbox": "partials/inbox.html",
        "reviews": "partials/reviews.html",
        "voucher": "partials/voucher.html",
        "wishlist": "partials/wishlist.html",
        "recent": "partials/recent.html",
        "account": "partials/my_account.html",  # Make sure this exists
        "payment": "partials/payment.html",
        "profile_details": "partials/profile_details.html",
        # ... and so on for your other pages
    }

    # Get the correct template, or a default/error template if the page is not found
    template_name = template_map.get(page)

    if not template_name:
        # Handle the case where an invalid 'page' is requested
        return HttpResponse("Content not found.", status=404)

    return render(request, template_name, context)




@login_required
def edit_address(request):
    user = request.user
    address = DeliveryAddress.objects.filter(user=user, is_default=True).first()

    if request.method == 'POST':
        name = request.POST.get('contact_name')
        phone = request.POST.get('contact_phone')
        line1 = request.POST.get('address_line_1')
        line2 = request.POST.get('address_line_2')
        city = request.POST.get('city')
        state = request.POST.get('state')
        country = request.POST.get('country')
        postal = request.POST.get('postal_zip_code')

        if not address:
            address = DeliveryAddress(user=user)

        address.contact_name = name
        address.contact_phone = phone
        address.address_line_1 = line1
        address.address_line_2 = line2
        address.city = city
        address.state = state
        address.country = country
        address.postal_zip_code = postal
        address.is_default = True
        address.save()

        messages.success(request, "✅ Address updated successfully!")
        return redirect('dashboard')

    return redirect('dashboard')

def orders(request):
    if not request.user.is_authenticated:
        return redirect('login')

        # Get all orders for the logged-in user
    orders = Order.objects.filter(user=request.user).order_by('-date_ordered')

    return render(request, 'partials/ordersection.html', {'orders': orders})


def order_detail(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')
    print(f"Order detail called for order_id: {order_id}, user: {request.user.username}")

    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all() if hasattr(order, 'items') else []

    steps = [
        {'status': 'pending', 'label': 'Order Placed'},
        {'status': 'processing', 'label': 'Processing'},
        {'status': 'shipped', 'label': 'Shipped'},
        {'status': 'delivered', 'label': 'Delivered'},
    ]

    return render(request, 'order_detail.html', {'order': order, 'order_items': order_items,'steps': steps,})


@login_required
def profile_details(request):
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = Profile.objects.create(user=request.user)

    return render(request, 'partials/profile_details.html', {'profile': profile})

@login_required
def profile_view(request,id):
    user = request.user
    profile = get_object_or_404( Profile,user=user,pk=id)

    if request.method == 'POST':
        fullname = request.POST.get('fullName')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        dob = request.POST.get('DOB')
        gender = request.POST.get('gender')
        image = request.FILES.get('image')

        if fullname:
            user.first_name = fullname  # Or use a custom field if you have fullName on User
        user.username = username
        user.email = email
        user.save()
        profile.phone = phone
        profile.DOB = dob
        profile.gender = gender
        if image:
            profile.image = image
        profile.save()

        messages.success(request, "✅ Profile updated successfully!")
        return redirect('dashboard')

    context = {'profile': profile,'user':user}
    return render(request, 'partials/edit_profile.html', context)


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    def dispatch(self, *args, **kwargs):
        response = super().dispatch(*args, **kwargs)
        if hasattr(response, 'render'):
            # Add header to bypass ngrok warning
            response['ngrok-skip-browser-warning'] = 'anyvalue'
        return response