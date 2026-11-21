import json
from django.http import Http404, HttpResponseBadRequest
import yfinance as yf
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from django.core.paginator import Paginator
from core import models
from core import services

# Create your views here.
@login_required
def dashboard(request):
    return render(request, "core/loading.html", {
        "title": "Dashboard",
        "refresh": "api/dashboard-refresh/"
    })

@login_required
def dashboard_refresh(request):
    today = timezone.localdate()
    holdings = models.Holding.objects.filter(user=request.user)
    user_cash, _ = models.UserCash.objects.get_or_create(user=request.user)
    cash = float(user_cash.cash)
    portfolio_value = cash
    symbols = [holding.symbol for holding in holdings]
    key = f"user_{request.user.id}_holdings"
    prices = cache.get_or_set(key, lambda: services.fetch_prices(symbols), 300)

    for holding in holdings:
        holding.current_price = prices[holding.symbol]
        holding.value = holding.current_price * holding.shares
        portfolio_value += holding.value

    for holding in holdings:
        holding.allocation = f"{holding.value / portfolio_value * 100:.2f}%"
        holding.current_price = f"${holding.current_price:,.2f}"
        holding.value = f"${holding.value:,.2f}"

    models.PortfolioHistory.objects.update_or_create(
        user=request.user,
        date=today,

        defaults={
            'value': portfolio_value,
        }
    )

    portfolio_value = f"${portfolio_value:,.2f}"

    history = reversed(
        list(models.PortfolioHistory.objects.filter(user=request.user) \
        .order_by('-date')[:50])
    )

    labels = []
    data = []

    for h in history:
        labels.append(h.date.strftime("%b %d, %Y"))
        data.append(float(h.value))
    
    return render(request, 'core/partial/dashboard-refresh.html', {
        "portfolio_value": portfolio_value,
        "holdings": holdings,
        "labels": json.dumps(labels),
        'data': json.dumps(data),
    })

@login_required
def stocks(request):
    stock_name = request.GET.get("stock_name")
    page = request.GET.get("page")
    url = "/api/stocks-refresh/"

    if stock_name:
        url += f"?stock_name={stock_name}"

        if page:
            url += f"&page={page}"
    elif page:
        url += f"?page={page}"
        
    return render(request, "core/loading.html", {
        "title": "Stocks",
        "refresh": url
    })

@login_required
def stocks_refresh(request):
    stock_list = models.Stock.objects.all()
    symbols = [stock.symbol for stock in stock_list]

    prices = cache.get_or_set(
        "stock_prices",
        lambda: services.fetch_prices(symbols),
        300
    )

    stock_name = request.GET.get("stock_name")

    if stock_name:
        stock_list = stock_list.filter(symbol__icontains=stock_name)

    paginator = Paginator(stock_list, 4)
    page = request.GET.get("page")
    stock_list = paginator.get_page(page)

    for stock in stock_list:
        stock.price = prices[stock.symbol]

    return render(request, 'core/partial/stocks-refresh.html', {
        "stock_list": stock_list,
        "stock_name": stock_name,
    })

@login_required
def stock_details(request, symbol):
    symbol = symbol.upper()

    if request.method == "POST":
        trade_type = request.POST.get("trade_type")

        if trade_type == "buy":
            trade_type = models.Trade.TradeType.BUY
        elif trade_type == "sell":
            trade_type = models.Trade.TradeType.SELL
        else:
            return HttpResponseBadRequest("Invalid trade type")
        
        

    return render(request, 'core/loading.html', {
        "title": symbol,
        'refresh': f"/api/stock-details-refresh/{symbol}"
    })

@login_required
def stock_details_refresh(request, symbol):
    stock = get_object_or_404(models.Stock, symbol=symbol)
    history = services.fetch_stock_history(stock.symbol)
    labels = history.index.strftime("%b %d, %Y").tolist()
    data = history.astype(float).tolist()
    cash = models.UserCash.objects.get(user=request.user).cash
    holding = models.Holding.objects \
        .filter(user=request.user, symbol=stock.symbol).first()

    shares = 0 if not holding else holding.shares

    return render(request, "core/partial/stock-details-refresh.html", {
        "current_price": data[-1],
        "buying_power": cash,
        "shares_owned": shares,
        "desc": stock.desc,
        "labels": json.dumps(labels),
        "data": json.dumps(data),
    })

@login_required
def history(request):
    return render(request, 'core/history.html')