from django.contrib import messages
from django.shortcuts import render, get_object_or_404

# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from staticApp.models import Order, Product, Users, OrderItem, DeliveryAddress


def admin_required(view_func):
    return user_passes_test(lambda u: u.is_staff)(view_func)


@login_required
@admin_required
def admin_dashboard(request):
    # Time periods
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Key metrics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_customers = Users.objects.count()
    total_products = Product.objects.count()

    # Recent time metrics
    today_orders = Order.objects.filter(created_at__date=today).count()
    week_revenue = Order.objects.filter(
        created_at__date__gte=week_ago
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Order status breakdown
    order_status = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Recent orders
    recent_orders = Order.objects.select_related('user').prefetch_related('orderitem_set').order_by('-created_at')[:10]

    # Top products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity'),
        total_revenue=Sum('orderitem__price')
    ).order_by('-total_sold')[:10]

    # Sales chart data (last 30 days)
    sales_data = []
    for i in range(30):
        date = today - timedelta(days=29 - i)
        daily_sales = Order.objects.filter(
            created_at__date=date
        ).aggregate(total=Sum('total_price'))['total'] or 0
        sales_data.append({
            'date': date,
            'sales': float(daily_sales)
        })

    context = {
        # Metrics
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'total_products': total_products,
        'today_orders': today_orders,
        'week_revenue': week_revenue,

        # Charts and lists
        'order_status': order_status,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'sales_data': sales_data,

        # Date ranges
        'today': today,
        'week_ago': week_ago,
        'month_ago': month_ago,
    }

    return render(request, 'dashboard/index.html', context)


@login_required
@admin_required
def orders_list(request):
    orders = Order.objects.select_related('user').prefetch_related('orderitem_set').all()

    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Search
    search_query = request.GET.get('search')
    if search_query:
        orders = orders.filter(
            Q(reference_code__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES if hasattr(Order, 'STATUS_CHOICES') else []
    }
    return render(request, 'dashboard/orders.html', context)


@login_required
@admin_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.select_related('user'), id=order_id)
    order_items = order.orderitem_set.select_related('product')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES if hasattr(Order, 'STATUS_CHOICES') else []):
            order.status = new_status
            order.save()
            messages.success(request, f"Order status updated to {new_status}")

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'dashboard/order_detail.html', context)